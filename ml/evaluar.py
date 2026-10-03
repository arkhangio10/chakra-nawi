"""
Evalúa el conteo de broca con marcos completos SINTÉTICOS de prueba, usando el
posprocesado EXACTO de contracts/modelo-io.md:

  1. Marco rectificado 1216×1216 → 4 mosaicos 640×640, orígenes x, y ∈ {0, 576}.
  2. Entrada por mosaico: RGB, píxel/255, float32 NCHW [1,3,640,640] (`images`).
  3. Salida `output0` [1,5,8400]: cx, cy, w, h (px del mosaico) y puntaje.
  4. Descartar puntaje < 0,25.
  5. Cajas a coordenadas del marco (+ origen del mosaico).
  6. NMS global con IoU 0,45 (se suprime si IoU > 0,45).
  7. Conteo = número de cajas que quedan.

Reporta, para fp32 e int8: error absoluto medio (MAE) del conteo, sesgo,
desglose por densidad (<50, 50–300, >300; y los marcos con 0), precisión/recall
de detección (IoU ≥ 0,5), latencia media por mosaico en onnxruntime CPU, y un
barrido del umbral de puntaje (curva para proponer umbrales antes de H8).

ESTOS RESULTADOS SON CON DATOS SINTÉTICOS: NO son desempeño en broca real.

Uso:
    python evaluar.py
    python evaluar.py --marcos datasets/sint_v0/marcos/test --nombre broca-y8n-v0-sint
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

ML = Path(__file__).resolve().parent
S, TILE, ORIGENES = 1216, 640, (0, 576)
SCORE, IOU = 0.25, 0.45


# ----------------------------- posprocesado del contrato -----------------------------

def mosaicos(marco_rgb: np.ndarray):
    """Corta el marco en 4 mosaicos; rellena con gris 114 si faltara algo."""
    for oy in ORIGENES:
        for ox in ORIGENES:
            t = np.full((TILE, TILE, 3), 114, np.uint8)
            m = marco_rgb[oy:oy + TILE, ox:ox + TILE]
            t[:m.shape[0], :m.shape[1]] = m
            yield ox, oy, t


def preparar(tile_rgb: np.ndarray) -> np.ndarray:
    return (tile_rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None].copy()


def decodificar(salida: np.ndarray, ox: int, oy: int, umbral: float):
    o = salida[0]                      # (5, 8400)
    sc = o[4]
    k = sc >= umbral
    cx, cy, w, h = o[0, k], o[1, k], o[2, k], o[3, k]
    cajas = np.stack([cx - w / 2 + ox, cy - h / 2 + oy, cx + w / 2 + ox, cy + h / 2 + oy], 1)
    return cajas.astype(np.float32), sc[k].astype(np.float32)


def iou_uno_vs_muchos(b, bs):
    xx1 = np.maximum(b[0], bs[:, 0]); yy1 = np.maximum(b[1], bs[:, 1])
    xx2 = np.minimum(b[2], bs[:, 2]); yy2 = np.minimum(b[3], bs[:, 3])
    inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
    a = (b[2] - b[0]) * (b[3] - b[1])
    a2 = (bs[:, 2] - bs[:, 0]) * (bs[:, 3] - bs[:, 1])
    return inter / np.maximum(a + a2 - inter, 1e-9)


def nms(cajas: np.ndarray, puntajes: np.ndarray, iou: float = IOU) -> np.ndarray:
    """NMS voraz (una clase), igual al que debe hacerse en JS."""
    orden = np.argsort(-puntajes, kind="stable")
    quedan = []
    while orden.size:
        i = orden[0]
        quedan.append(i)
        if orden.size == 1:
            break
        ious = iou_uno_vs_muchos(cajas[i], cajas[orden[1:]])
        orden = orden[1:][ious <= iou]
    return np.array(quedan, dtype=np.int64)


def inferir_marco(sesion, marco_rgb, umbral=SCORE):
    """Devuelve candidatos (cajas en px del marco, puntajes) antes del NMS y tiempos por mosaico."""
    cajas, punt, tiempos = [], [], []
    for ox, oy, t in mosaicos(marco_rgb):
        x = preparar(t)
        t0 = time.perf_counter()
        y = sesion.run(["output0"], {"images": x})[0]
        tiempos.append((time.perf_counter() - t0) * 1000)
        c, s = decodificar(y, ox, oy, umbral)
        cajas.append(c); punt.append(s)
    return np.concatenate(cajas), np.concatenate(punt), tiempos


def contar(cajas, punt, umbral=SCORE, iou=IOU):
    k = punt >= umbral
    c, s = cajas[k], punt[k]
    if len(c) == 0:
        return c, s
    q = nms(c, s, iou)
    return c[q], s[q]


# ----------------------------------- métricas ----------------------------------------

def leer_cajas(txt: Path) -> np.ndarray:
    if not txt.exists() or not txt.read_text().strip():
        return np.zeros((0, 4), np.float32)
    a = np.loadtxt(txt, ndmin=2)[:, 1:] * S
    return np.stack([a[:, 0] - a[:, 2] / 2, a[:, 1] - a[:, 3] / 2,
                     a[:, 0] + a[:, 2] / 2, a[:, 1] + a[:, 3] / 2], 1).astype(np.float32)


def emparejar(pred, punt, gt, umbral_iou=0.5):
    """Emparejamiento voraz por puntaje. Devuelve (tp_pred bool, gt_encontrado bool)."""
    tp = np.zeros(len(pred), bool)
    usado = np.zeros(len(gt), bool)
    if len(gt) == 0 or len(pred) == 0:
        return tp, usado
    for i in np.argsort(-punt):
        ious = iou_uno_vs_muchos(pred[i], gt)
        ious[usado] = -1
        j = int(np.argmax(ious))
        if ious[j] >= umbral_iou:
            tp[i] = True
            usado[j] = True
    return tp, usado


def banda(n: int) -> str:
    return "<50" if n < 50 else ("50-300" if n <= 300 else ">300")


def resumen_conteo(reales, preds):
    r, p = np.asarray(reales, float), np.asarray(preds, float)
    out = {"n": int(len(r))}
    if len(r) == 0:
        return out
    err = p - r
    out["mae"] = round(float(np.abs(err).mean()), 2)
    out["sesgo"] = round(float(err.mean()), 2)
    nz = r > 0
    if nz.any():
        out["error_relativo_medio_%"] = round(float((np.abs(err[nz]) / r[nz]).mean() * 100), 1)
    return out


def latencia(ruta: Path, hilos: int | None, n: int = 30) -> float:
    import onnxruntime as ort
    so = ort.SessionOptions()
    if hilos:
        so.intra_op_num_threads = hilos
    s = ort.InferenceSession(str(ruta), so, providers=["CPUExecutionProvider"])
    x = np.random.default_rng(1).random((1, 3, 640, 640), dtype=np.float32)
    for _ in range(3):
        s.run(None, {"images": x})
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        s.run(None, {"images": x})
        t.append((time.perf_counter() - t0) * 1000)
    return round(float(np.median(t)), 1)


def dibujar(marco_rgb, pred, punt, gt, titulo, ruta):
    tp, usado = emparejar(pred, punt, gt)
    v = cv2.cvtColor(marco_rgb, cv2.COLOR_RGB2BGR).copy()
    for b, ok in zip(pred.astype(int), tp):
        cv2.rectangle(v, tuple(b[:2]), tuple(b[2:]), (0, 200, 0) if ok else (0, 140, 255), 2)
    for b, ok in zip(gt.astype(int), usado):
        if not ok:
            cv2.rectangle(v, tuple(b[:2]), tuple(b[2:]), (0, 0, 255), 2)
    cv2.rectangle(v, (0, 0), (S, 64), (255, 255, 255), -1)
    cv2.putText(v, titulo, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(v, "verde=acierto  naranja=falso positivo  rojo=broca no detectada  | DATOS SINTETICOS",
                (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.imwrite(str(ruta), v, [cv2.IMWRITE_JPEG_QUALITY, 90])


# ------------------------------------- main ------------------------------------------

def main():
    import onnxruntime as ort

    ap = argparse.ArgumentParser()
    ap.add_argument("--marcos", default=str(ML / "datasets" / "sint_v0" / "marcos" / "test"))
    ap.add_argument("--nombre", default="broca-y8n-v0-sint")
    ap.add_argument("--salida", default=str(ML / "resultados"))
    ap.add_argument("--val", default=str(ML / "datasets" / "sint_v0" / "marcos" / "val"),
                    help="marcos de validación para elegir el umbral propuesto")
    a = ap.parse_args()

    marcos = Path(a.marcos)
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    conteos = json.loads((marcos / "conteos.json").read_text(encoding="utf-8"))["marcos"]
    nombres = sorted(conteos)
    variantes = {"fp32": ML / "modelos" / f"{a.nombre}.onnx", "int8": ML / "modelos" / f"{a.nombre}-int8.onnx",
                 "w8": ML / "modelos" / f"{a.nombre}-w8.onnx"}
    variantes = {k: v for k, v in variantes.items() if v.exists() or k != "w8"}

    imgs = {n: cv2.cvtColor(cv2.imread(str(marcos / "images" / f"{n}.jpg")), cv2.COLOR_BGR2RGB) for n in nombres}
    gts = {n: leer_cajas(marcos / "labels" / f"{n}.txt") for n in nombres}

    res = {"sintetico": True,
           "advertencia": "Evaluación con datos SINTÉTICOS. NO es desempeño en broca real.",
           "marcos_prueba": len(nombres), "carpeta": str(marcos.relative_to(ML)) if marcos.is_relative_to(ML) else str(marcos),
           "posprocesado": {"score_min": SCORE, "nms_iou": IOU, "mosaicos": "4 de 640, orígenes {0,576}",
                            "fuente": "contracts/modelo-io.md"},
           "variantes": {}, "por_marco": {n: {"real": len(gts[n])} for n in nombres}}
    candidatos = {}
    for var, ruta in variantes.items():
        if not ruta.exists():
            print("falta", ruta)
            continue
        ses = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
        reales, preds, tps, nps, ngt, tiempos = [], [], 0, 0, 0, []
        cand_var = {}
        for n in nombres:
            c, s, t = inferir_marco(ses, imgs[n], umbral=0.05)
            cand_var[n] = (c, s)
            tiempos += t
            pc, ps = contar(c, s)
            tp, _ = emparejar(pc, ps, gts[n])
            tps += int(tp.sum()); nps += len(pc); ngt += len(gts[n])
            reales.append(len(gts[n])); preds.append(len(pc))
            res["por_marco"][n][var] = len(pc)
        candidatos[var] = cand_var
        porb = {}
        for b in ("<50", "50-300", ">300"):
            idx = [i for i, r in enumerate(reales) if banda(r) == b]
            porb[b] = resumen_conteo([reales[i] for i in idx], [preds[i] for i in idx])
        ceros = [preds[i] for i, r in enumerate(reales) if r == 0]
        prec = tps / max(nps, 1); rec = tps / max(ngt, 1)
        res["variantes"][var] = {
            "archivo": ruta.name, "mb": round(ruta.stat().st_size / 2 ** 20, 2),
            "conteo_total": resumen_conteo(reales, preds),
            "por_densidad": porb,
            "marcos_con_0_brocas": {"n": len(ceros), "falsos_positivos_medios": round(float(np.mean(ceros)), 2) if ceros else None},
            "deteccion_iou50": {"precision": round(prec, 3), "recall": round(rec, 3),
                                "f1": round(2 * prec * rec / max(prec + rec, 1e-9), 3)},
            "latencia_ms_mosaico": {
                "durante_eval_media": round(float(np.mean(tiempos)), 1),
                "hilos_por_defecto_mediana": latencia(ruta, None),
                "1_hilo_mediana": latencia(ruta, 1),
            },
        }
        print(var, json.dumps(res["variantes"][var], ensure_ascii=False))

    # Barrido del umbral de puntaje (fp32): curva para proponer umbrales antes de H8
    if "fp32" in candidatos:
        barrido = []
        for u in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
            r_, p_ = [], []
            for n in nombres:
                c, s = candidatos["fp32"][n]
                r_.append(len(gts[n])); p_.append(len(contar(c, s, umbral=u)[0]))
            barrido.append({"score": u, **resumen_conteo(r_, p_)})
        res["barrido_score_fp32"] = barrido

    # Recomendación: tolerancia de MAE, tamaño del contrato (< 10 MB) y latencia a 1 hilo
    v = res["variantes"]
    if "fp32" in v:
        m32 = v["fp32"]["conteo_total"]["mae"]
        tol = round(m32 * 1.1 + 0.5, 2)
        filas = {k: {"mae": d["conteo_total"]["mae"], "mb": d["mb"],
                     "latencia_1_hilo_ms": d["latencia_ms_mosaico"]["1_hilo_mediana"],
                     "latencia_hilos_def_ms": d["latencia_ms_mosaico"]["hilos_por_defecto_mediana"],
                     "precision_ok": d["conteo_total"]["mae"] <= tol, "cumple_10mb": d["mb"] < 10}
                 for k, d in v.items()}
        contrato = [k for k in ("fp32", "int8") if k in filas]
        ok = [k for k in contrato if filas[k]["precision_ok"] and filas[k]["cumple_10mb"]]
        eleg = min(ok, key=lambda k: filas[k]["latencia_1_hilo_ms"]) if ok else             min([k for k in contrato if filas[k]["precision_ok"]], key=lambda k: filas[k]["latencia_1_hilo_ms"])
        res["recomendacion"] = {
            "variante": eleg,
            "criterio": ("entre las variantes del contrato (fp32, int8): MAE ≤ 1,1×MAE fp32 + 0,5 "
                         f"(= {tol}), tamaño < 10 MB y, de esas, la más rápida a 1 hilo (como WASM sin "
                         "aislamiento). Si ninguna cumple el tamaño, la más rápida con precisión aceptable."),
            "tabla": filas,
        }

    # Umbral propuesto: se elige en VALIDACIÓN (no en prueba) y se reporta su MAE en prueba.
    val = Path(a.val)
    if (val / "conteos.json").exists() and candidatos:
        cv = json.loads((val / "conteos.json").read_text(encoding="utf-8"))["marcos"]
        umbrales = [round(0.25 + 0.05 * i, 2) for i in range(10)]
        prop = {}
        for var in candidatos:
            ses = ort.InferenceSession(str(variantes[var]), providers=["CPUExecutionProvider"])
            cand_val = {}
            for n in sorted(cv):
                im = cv2.cvtColor(cv2.imread(str(val / "images" / f"{n}.jpg")), cv2.COLOR_BGR2RGB)
                cand_val[n] = inferir_marco(ses, im, umbral=0.05)[:2]
            curva = []
            for u in umbrales:
                r_ = [cv[n]["conteo"] for n in sorted(cv)]
                p_ = [len(contar(*cand_val[n], umbral=u)[0]) for n in sorted(cv)]
                curva.append({"score": u, **resumen_conteo(r_, p_)})
            mejor = min(curva, key=lambda d: d["mae"])["score"]
            reales = [len(gts[n]) for n in nombres]
            preds = [len(contar(*candidatos[var][n], umbral=mejor)[0]) for n in nombres]
            porb = {}
            for b in ("<50", "50-300", ">300"):
                idx = [i for i, r in enumerate(reales) if banda(r) == b]
                porb[b] = resumen_conteo([reales[i] for i in idx], [preds[i] for i in idx])
            for n, pr in zip(nombres, preds):
                res["por_marco"][n][f"{var}_score_{mejor}"] = pr
            prop[var] = {"score_elegido_en_val": mejor, "curva_val": curva,
                         "prueba_con_ese_score": {"conteo_total": resumen_conteo(reales, preds), "por_densidad": porb}}
        res["umbral_propuesto"] = {
            "nota": ("PROPUESTA de P2 para discutir antes de H8 (contracts/modelo-io.md lo permite sin cambiar la E/S). "
                     "El contrato sigue en score 0,25 / NMS 0,45 hasta que los cuatro lo acuerden. "
                     "Elegido en validación sintética; con fotos reales hay que recalibrarlo."),
            "nms_iou": IOU, "variantes": prop}
        print("umbral propuesto", {k: v["score_elegido_en_val"] for k, v in prop.items()},
              {k: v["prueba_con_ese_score"]["conteo_total"] for k, v in prop.items()})

    # Ejemplos: un acierto típico, el peor fallo y un marco denso
    if "fp32" in candidatos:
        errs = {n: res["por_marco"][n]["fp32"] - res["por_marco"][n]["real"] for n in nombres}
        rel = {n: abs(e) / max(res["por_marco"][n]["real"], 5) for n, e in errs.items()}
        peor = max(rel, key=rel.get)
        medios = [n for n in nombres if 50 <= res["por_marco"][n]["real"] <= 300 and n != peor]
        bueno = min(medios, key=lambda n: abs(errs[n])) if medios else nombres[0]
        densos = [n for n in nombres if res["por_marco"][n]["real"] > 300 and n not in (peor, bueno)]
        denso = max(densos, key=lambda n: res["por_marco"][n]["real"]) if densos else nombres[-1]
        ejemplos = []
        for etiqueta, n in (("acierto", bueno), ("fallo", peor), ("denso", denso)):
            c, s = candidatos["fp32"][n]
            pc, ps = contar(c, s)
            r = res["por_marco"][n]["real"]
            titulo = f"{etiqueta.upper()} {n}: real {r}, YOLO fp32 {len(pc)} (error {len(pc) - r:+d})"
            ruta = out / f"ejemplo_{etiqueta}_{n}.jpg"
            dibujar(imgs[n], pc, ps, gts[n], titulo, ruta)
            ejemplos.append({"tipo": etiqueta, "marco": n, "real": r, "yolo_fp32": len(pc), "imagen": ruta.name})
        res["ejemplos"] = ejemplos
    for p in out.glob("ejemplo_*.jpg"):
        if p.name not in {e["imagen"] for e in res.get("ejemplos", [])}:
            p.unlink()

    (out / "eval_sintetico.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("recomendacion", "barrido_score_fp32") if k in res}, indent=1,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
