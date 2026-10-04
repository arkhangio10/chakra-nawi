"""
Exporta el YOLO entrenado a ONNX según contracts/modelo-io.md y crea la variante int8.

Pasos:
1. `yolo export format=onnx imgsz=640 opset=17 simplify=True dynamic=False nms=False half=False`
2. Verifica con onnxruntime: entrada `images` [1,3,640,640] float32 y salida
   `output0` [1,5,8400] float32 (fila 4 = puntaje ya con sigmoide, en [0,1]).
3. int8 con `onnxruntime.quantization.quantize_dynamic` (pesos QUInt8; misma E/S).
4. Copia ambas variantes a apps/campo/public/models/ y escribe ml/modelos/metadata.json.

5. Opcional (--w8): variante EXPERIMENTAL con solo los pesos en int8 y cómputo fp32.

Uso:
    python exportar.py --pesos runs/y8n_sint_v0/weights/best.pt --nombre broca-y8n-v0-sint --w8
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path

import numpy as np

ML = Path(__file__).resolve().parent
RAIZ = ML.parent
PUBLICO = RAIZ / "apps" / "campo" / "public" / "models"


def verificar(ruta: Path) -> dict:
    import onnxruntime as ort
    s = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    ins, outs = s.get_inputs(), s.get_outputs()
    assert len(ins) == 1 and len(outs) == 1, (ins, outs)
    i, o = ins[0], outs[0]
    assert i.name == "images", i.name
    assert list(i.shape) == [1, 3, 640, 640], i.shape
    assert i.type == "tensor(float)", i.type
    assert o.name == "output0", o.name
    assert list(o.shape) == [1, 5, 8400], o.shape
    assert o.type == "tensor(float)", o.type
    x = np.random.default_rng(0).random((1, 3, 640, 640), dtype=np.float32)
    y = s.run(None, {"images": x})[0]
    assert y.shape == (1, 5, 8400) and y.dtype == np.float32
    assert 0.0 <= y[0, 4].min() and y[0, 4].max() <= 1.0, "la fila 4 debe estar en [0,1]"
    return {"entrada": {"nombre": i.name, "forma": list(i.shape), "tipo": "float32"},
            "salida": {"nombre": o.name, "forma": list(o.shape), "tipo": "float32"}}


def pesos_int8(fuente: Path, destino: Path):
    """Variante EXPERIMENTAL "w8": solo los pesos de las Conv se guardan en int8.

    Cuantización simétrica por canal de salida (escala = max|w|/127) y un nodo
    DequantizeLinear (opset ≥ 13, axis=0) que reconstruye el peso fp32 al vuelo.
    El cómputo sigue en fp32 (rápido en WASM) y el archivo pesa ~1/4.
    No reemplaza a la variante int8 del contrato; es una propuesta medida aparte.
    """
    import onnx
    from onnx import helper, numpy_helper

    m = onnx.load(str(fuente))
    g = m.graph
    inits = {i.name: i for i in g.initializer}
    pesos_conv = {n.input[1] for n in g.node if n.op_type == "Conv" and len(n.input) > 1 and n.input[1] in inits}
    nuevos_nodos = []
    for nombre in sorted(pesos_conv):
        w = numpy_helper.to_array(inits[nombre]).astype(np.float32)
        if w.ndim != 4:
            continue
        esc = np.abs(w).reshape(w.shape[0], -1).max(1) / 127.0
        esc[esc == 0] = 1e-8
        q = np.clip(np.round(w / esc[:, None, None, None]), -127, 127).astype(np.int8)
        g.initializer.remove(inits[nombre])
        g.initializer.extend([numpy_helper.from_array(q, nombre + "_q"),
                              numpy_helper.from_array(esc.astype(np.float32), nombre + "_esc"),
                              numpy_helper.from_array(np.zeros(w.shape[0], np.int8), nombre + "_zp")])
        nuevos_nodos.append(helper.make_node("DequantizeLinear", [nombre + "_q", nombre + "_esc", nombre + "_zp"],
                                             [nombre], name=nombre + "_dq", axis=0))
    for i, n in enumerate(nuevos_nodos):
        g.node.insert(i, n)
    onnx.checker.check_model(m)
    onnx.save(m, str(destino))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w8", action="store_true",
                    help="crea además la variante experimental -w8 (pesos int8, cómputo fp32)")
    ap.add_argument("--pesos", default=None, help="por defecto: corrida v0 de la arquitectura indicada en --nombre")
    ap.add_argument("--nombre", default="broca-y8n-v0-sint")
    ap.add_argument("--arquitectura", default=None)
    ap.add_argument("--evaluacion", default=None, help="JSON de evaluación de ESTE modelo, si ya existe")
    ap.add_argument("--no-copiar", action="store_true", help="no copiar a apps/campo/public/models/")
    a = ap.parse_args()

    from ultralytics import YOLO
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from onnxruntime.quantization.shape_inference import quant_pre_process

    destino = ML / "modelos"
    destino.mkdir(exist_ok=True)
    corrida = "y11n_sint_v0" if "y11n" in a.nombre else "y8n_sint_v0"
    pesos = Path(a.pesos) if a.pesos else ML / "runs" / corrida / "weights" / "best.pt"

    modelo = YOLO(str(pesos))
    salida = modelo.export(format="onnx", imgsz=640, opset=17, simplify=True, dynamic=False,
                           nms=False, half=False, device="cpu")
    fp32 = destino / f"{a.nombre}.onnx"
    shutil.copyfile(salida, fp32)
    io = verificar(fp32)
    print("fp32 OK", io)

    pre = destino / f"{a.nombre}-pre.onnx"
    int8 = destino / f"{a.nombre}-int8.onnx"
    try:
        quant_pre_process(str(fp32), str(pre), skip_symbolic_shape=True)
        fuente = pre
    except Exception as e:  # el preproceso es opcional
        print("quant_pre_process falló, se cuantiza directo:", e)
        fuente = fp32
    quantize_dynamic(str(fuente), str(int8), weight_type=QuantType.QUInt8)
    if pre.exists():
        pre.unlink()
    io8 = verificar(int8)
    assert io8 == io, (io8, io)
    print("int8 OK", io8)
    w8 = destino / f"{a.nombre}-w8.onnx"
    if a.w8:
        pesos_int8(fp32, w8)
        assert verificar(w8) == io
        print("w8 OK (experimental)")

    # Épocas y datos del entrenamiento
    run = pesos.parent.parent
    resumen = {}
    if (run / "resumen_entrenamiento.json").exists():
        resumen = json.loads((run / "resumen_entrenamiento.json").read_text(encoding="utf-8"))
    epocas = resumen.get("epocas_completadas")
    if epocas is None and (run / "results.csv").exists():
        epocas = len((run / "results.csv").read_text().strip().splitlines()) - 1

    mb = lambda p: round(p.stat().st_size / 2 ** 20, 2)
    meta = {
        "modelo": a.nombre,
        "leyenda": "entrenado solo con datos sintéticos",
        "arquitectura": a.arquitectura or (
            "YOLO11n" if "yolo11" in str(modelo.model.yaml.get("yaml_file", "")) else "YOLOv8n"),
        "clases": {"0": "broca"},
        "epocas": epocas,
        "pesos_iniciales": resumen.get("modelo_inicial_ruta", resumen.get("modelo_inicial", "yolov8n.pt (COCO)")),
        "datos": resumen.get("datos", "sintéticos ml/sintetico.py (marcos 1216×1216 → mosaicos 640×640)"),
        "exportacion": "format=onnx imgsz=640 opset=17 simplify=True dynamic=False nms=False half=False",
        "entrada": io["entrada"],
        "salida": io["salida"],
        "umbrales": {"candidatas": 0.25, "conteo": 0.60, "nms_iou": 0.45,
                     "dudoso": ">30% de candidatas en [0,25;0,60)",
                     "fuente": "contracts/modelo-io.md (adoptado 2026-10-03)"},
        "variantes": {
            "fp32": {"archivo": fp32.name, "mb": mb(fp32), "unidad": "MiB",
                     "bytes": fp32.stat().st_size, "cumple_10_MB_decimal": fp32.stat().st_size < 10_000_000},
            "int8": {"archivo": int8.name, "mb": mb(int8), "unidad": "MiB",
                     "bytes": int8.stat().st_size, "cumple_10_MB_decimal": int8.stat().st_size < 10_000_000,
                     "cuantizacion": "onnxruntime.quantization.quantize_dynamic, pesos QUInt8"},
            **({"w8_experimental": {"archivo": w8.name, "mb": mb(w8),
                                    "cuantizacion": "solo pesos Conv int8 por canal + DequantizeLinear; cómputo fp32",
                                    "nota": "propuesta fuera del contrato (que pide int8 dinámica); misma E/S"}}
               if w8.exists() else {}),
        },
        "nota_tamano": "El contrato pide < 10 MB; revisar tamaño y latencia por variante.",
        "fecha": dt.datetime.now().isoformat(timespec="seconds"),
        "contrato": "contracts/modelo-io.md",
    }
    ev = Path(a.evaluacion) if a.evaluacion else None
    if ev is not None and ev.exists():
        e = json.loads(ev.read_text(encoding="utf-8"))
        assert e.get("modelo") == a.nombre, "La evaluación pertenece a otro modelo"
        meta["evaluacion_sintetica"] = {"archivo": str(ev),
                                        "recomendada": e.get("recomendacion", {}).get("variante")}
    # Conservar trazabilidad de todas las exportaciones, sin reemplazar el modelo vigente.
    (destino / f"{a.nombre}.metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    if not (destino / "metadata.json").exists():
        (destino / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta, indent=1, ensure_ascii=False))

    if not a.no_copiar:
        PUBLICO.mkdir(parents=True, exist_ok=True)
        for p in (fp32, int8):          # w8 (experimental) se queda en ml/modelos/
            shutil.copyfile(p, PUBLICO / p.name)
        print("Copiados a", PUBLICO)


if __name__ == "__main__":
    main()
