"""
Entrena YOLOv8n de UNA clase (broca) en CPU con mosaicos 640×640 SINTÉTICOS.

- Datos: ml/datasets/sint_v0/data.yaml (generados con ml/sintetico.py).
- Corridas: ml/runs/<nombre>/ (gitignored). Pesos iniciales COCO en ml/weights/.
- El presupuesto se fija con --horas (Ultralytics ajusta las épocas para no pasarse).

Aumentos elegidos para el problema:
- scale=0.15 (no 0.5): el tamaño es una pista clave (broca ≈21 px; moscas y otros
  escarabajos son más grandes). La homografía ya fija la escala.
- flipud=0.5 y fliplr=0.5: la tarjeta se ve desde arriba, no hay "arriba".
- degrees=0: la rotación ya está en el sintético y rotar cajas alineadas las agranda.

Ajustes para CPU lenta (i7-1165G7, 4 núcleos: ≈1,2 s por mosaico de 640):
- nbs = lote: un paso del optimizador por lote (con nbs=64 por defecto, Ultralytics
  acumularía 8 lotes y en 45 min habría ~35 pasos).
- warmup_epochs=0.3: con el valor por defecto (3) todo el entrenamiento sería calentamiento.
- freeze=4: congela las 4 primeras capas COCO (las más caras, en resolución alta).

Uso:
    python entrenar.py --horas 0.7
    python entrenar.py --epocas 3 --fraccion 0.1 --nombre prueba   # prueba rápida
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ML = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=str(ML / "datasets" / "sint_v0" / "data.yaml"))
    ap.add_argument("--modelo", default=str(ML / "weights" / "yolov8n.pt"),
                    help="pesos iniciales (yolov8n.pt o yolo11n.pt; NO yolo26)")
    ap.add_argument("--epocas", type=int, default=30)
    ap.add_argument("--horas", type=float, default=None, help="tope de tiempo; reemplaza --epocas")
    ap.add_argument("--lote", type=int, default=8)
    ap.add_argument("--nbs", type=int, default=None,
                    help="lote nominal; por defecto = --lote (un paso del optimizador por lote)")
    ap.add_argument("--congelar", type=int, default=4, help="congela las N primeras capas (0 = ninguna)")
    ap.add_argument("--warmup", type=float, default=0.3, help="épocas de calentamiento")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fraccion", type=float, default=1.0)
    ap.add_argument("--nombre", default="y8n_sint_v0")
    ap.add_argument("--cache", default="ram")
    a = ap.parse_args()

    import torch
    from ultralytics import YOLO

    (ML / "weights").mkdir(exist_ok=True)
    torch.set_num_threads(max(1, torch.get_num_threads()))
    modelo = YOLO(a.modelo)
    t0 = time.time()
    args = dict(
        data=a.datos, imgsz=640, epochs=a.epocas, batch=a.lote, device="cpu", workers=a.workers,
        project=str(ML / "runs"), name=a.nombre, exist_ok=True, single_cls=True, pretrained=True,
        cache=a.cache, fraction=a.fraccion, seed=0, deterministic=False, amp=False, plots=False,
        patience=100, close_mosaic=2, mosaic=1.0, scale=0.15, translate=0.1, degrees=0.0,
        fliplr=0.5, flipud=0.5, hsv_h=0.015, hsv_s=0.5, hsv_v=0.4, mixup=0.0, max_det=1000,
        nbs=a.nbs or a.lote, warmup_epochs=a.warmup, freeze=a.congelar or None,
    )
    if a.horas:
        args["time"] = a.horas
    res = modelo.train(**args)
    dur = time.time() - t0
    run = ML / "runs" / a.nombre
    resumen = {
        "sintetico": True,
        "nota": "Entrenado SOLO con datos sintéticos (ml/sintetico.py).",
        "modelo_inicial": Path(a.modelo).name,
        "datos": a.datos,
        "epocas_pedidas": a.epocas,
        "lote": a.lote, "nbs": a.nbs or a.lote, "congelar": a.congelar, "warmup_epochs": a.warmup,
        "horas_tope": a.horas,
        "duracion_s": round(dur, 1),
        "mejor": str(run / "weights" / "best.pt"),
        "metricas_val_mosaicos": {k: float(v) for k, v in getattr(res, "results_dict", {}).items()},
    }
    # Épocas realmente completadas (results.csv tiene una fila por época)
    csv = run / "results.csv"
    if csv.exists():
        resumen["epocas_completadas"] = max(0, len(csv.read_text().strip().splitlines()) - 1)
    (run / "resumen_entrenamiento.json").write_text(json.dumps(resumen, indent=1, ensure_ascii=False),
                                                    encoding="utf-8")
    print(json.dumps(resumen, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
