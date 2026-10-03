"""
Contador clásico de manchas oscuras (sin IA) para comparar con el YOLO.

SOLO MIDE. No activa ninguna regla: la regla "si difiere >30 % → técnico"
solo se activa si se calibra con fotos reales (PLAN §2, LIMITES_DE_DATOS.md).

Pensado para portarse a JavaScript tal cual: solo usa aritmética sobre arreglos,
una imagen integral y un etiquetado de componentes conexas. Los parámetros
viven en ml/contador_clasico.json.

Algoritmo, paso a paso (entrada: marco rectificado RGB de 1216×1216, uint8)
--------------------------------------------------------------------------
1. Gris: g = 0,299·R + 0,587·G + 0,114·B  (float).
2. Fondo local con imagen integral: para cada píxel, media de g en la ventana
   cuadrada de radio `radio` (lado 2·radio+1), RECORTADA al borde del marco
   (se divide por el número real de píxeles de la ventana).
     II[y+1][x+1] = g[y][x] + II[y][x+1] + II[y+1][x] − II[y][x]
     suma = II[y1][x1] − II[y0][x1] − II[y1][x0] + II[y0][x0]
3. Umbral adaptativo (tipo Bradley–Roth): oscuro = g ≤ media·(1 − t).
4. Apertura opcional (`apertura` = 1): erosión 3×3 y luego dilatación 3×3
   (vecindad de 8; fuera del marco cuenta como "no oscuro"). Quita puntitos.
5. Componentes conexas con vecindad de 8 (en JS: dos pasadas + union-find).
6. Por componente: área A (px), centroide, momentos centrales de 2.º orden
   μ20, μ02, μ11 (divididos por A) → autovalores λ1 ≥ λ2 de la matriz
   [[μ20, μ11], [μ11, μ02]]; elongación e = √(λ1/λ2) (λ2 mínimo 0,25), y
   contraste medio c = media sobre la componente de (media_local − g)/media_local.
7. Clasificación de cada componente:
     A < area_min                       → se descarta (polvo, granito de café)
     c < contraste_min                  → se descarta (mancha poco oscura)
     area_min ≤ A ≤ area_max_1:
         e_min ≤ e ≤ e_max              → 1 broca
         si no                          → se descarta
     area_max_1 < A ≤ area_max_grupo    → grupo: round(A / area_tipica) brocas
     A > area_max_grupo                 → se descarta (mosca, sombra, mancha grande)
8. Conteo = suma de lo anterior.

Uso
---
    python contador_clasico.py --calibrar     # búsqueda en rejilla sobre VALIDACIÓN (no prueba)
    python contador_clasico.py                # mide en PRUEBA y compara con el YOLO
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import cv2
import numpy as np

ML = Path(__file__).resolve().parent
PARAMS = ML / "contador_clasico.json"
POR_DEFECTO = {
    "radio": 40, "t": 0.25, "apertura": 1,
    "area_min": 60, "area_max_1": 320, "area_max_grupo": 4000, "area_tipica": 170,
    "e_min": 1.2, "e_max": 4.0, "contraste_min": 0.3,
}


# ----------------------------------- pasos 1–6 ----------------------------------------

def gris(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.float64) for i in range(3))
    return 0.299 * r + 0.587 * g + 0.114 * b


def media_local(g: np.ndarray, radio: int) -> np.ndarray:
    H, W = g.shape
    ii = np.zeros((H + 1, W + 1), np.float64)
    ii[1:, 1:] = g.cumsum(0).cumsum(1)
    ys, xs = np.arange(H), np.arange(W)
    y0, y1 = np.clip(ys - radio, 0, H), np.clip(ys + radio + 1, 0, H)
    x0, x1 = np.clip(xs - radio, 0, W), np.clip(xs + radio + 1, 0, W)
    s = ii[y1][:, x1] - ii[y0][:, x1] - ii[y1][:, x0] + ii[y0][:, x0]
    n = (y1 - y0)[:, None] * (x1 - x0)[None, :]
    return s / n


def componentes(rgb: np.ndarray, radio: int, t: float, apertura: int):
    """Pasos 1–6. Devuelve un arreglo (k, 4): área, elongación, contraste, etiqueta."""
    g = gris(rgb)
    m = media_local(g, radio)
    osc = (g <= m * (1 - t)).astype(np.uint8)
    if apertura:
        k = np.ones((3, 3), np.uint8)
        osc = cv2.dilate(cv2.erode(osc, k, borderType=cv2.BORDER_CONSTANT, borderValue=0), k,
                         borderType=cv2.BORDER_CONSTANT, borderValue=0)
    n, lab = cv2.connectedComponents(osc, connectivity=8)
    if n <= 1:
        return np.zeros((0, 4)), lab
    yy, xx = np.nonzero(lab)
    l = lab[yy, xx]
    A = np.bincount(l, minlength=n).astype(np.float64)
    sx = np.bincount(l, xx, n); sy = np.bincount(l, yy, n)
    sxx = np.bincount(l, xx * xx.astype(np.float64), n)
    syy = np.bincount(l, yy * yy.astype(np.float64), n)
    sxy = np.bincount(l, xx * yy.astype(np.float64), n)
    con = np.bincount(l, (m[yy, xx] - g[yy, xx]) / np.maximum(m[yy, xx], 1), n)
    A1 = np.maximum(A, 1)
    mx, my = sx / A1, sy / A1
    mu20 = sxx / A1 - mx ** 2 + 1 / 12
    mu02 = syy / A1 - my ** 2 + 1 / 12
    mu11 = sxy / A1 - mx * my
    tr, det = mu20 + mu02, mu20 * mu02 - mu11 ** 2
    disc = np.sqrt(np.maximum(tr ** 2 / 4 - det, 0))
    l1, l2 = tr / 2 + disc, np.maximum(tr / 2 - disc, 0.25)
    e = np.sqrt(l1 / l2)
    st = np.stack([A, e, con / A1, np.arange(n)], 1)[1:]
    return st, lab


# ----------------------------------- pasos 7–8 ----------------------------------------

def clasificar(st: np.ndarray, p: dict) -> np.ndarray:
    """Número de brocas que aporta cada componente."""
    if len(st) == 0:
        return np.zeros(0, int)
    A, e, c = st[:, 0], st[:, 1], st[:, 2]
    n = np.zeros(len(st), int)
    ok = (A >= p["area_min"]) & (c >= p["contraste_min"])
    uno = ok & (A <= p["area_max_1"]) & (e >= p["e_min"]) & (e <= p["e_max"])
    grupo = ok & (A > p["area_max_1"]) & (A <= p["area_max_grupo"])
    n[uno] = 1
    n[grupo] = np.maximum(1, np.round(A[grupo] / p["area_tipica"])).astype(int)
    return n


def contar(rgb: np.ndarray, p: dict) -> int:
    st, _ = componentes(rgb, p["radio"], p["t"], p["apertura"])
    return int(clasificar(st, p).sum())


# ------------------------------------- utilidades -------------------------------------

def cargar(carpeta: Path):
    c = json.loads((carpeta / "conteos.json").read_text(encoding="utf-8"))["marcos"]
    nombres = sorted(c)
    imgs = {n: cv2.cvtColor(cv2.imread(str(carpeta / "images" / f"{n}.jpg")), cv2.COLOR_BGR2RGB) for n in nombres}
    reales = {n: c[n]["conteo"] for n in nombres}
    return nombres, imgs, reales


def banda(n):
    return "<50" if n < 50 else ("50-300" if n <= 300 else ">300")


def mae(r, p):
    r, p = np.asarray(r, float), np.asarray(p, float)
    return round(float(np.abs(p - r).mean()), 2) if len(r) else None


def calibrar(carpeta: Path):
    nombres, imgs, reales = cargar(carpeta)
    r = np.array([reales[n] for n in nombres])
    mejor = None
    rejilla_area = list(itertools.product([40, 60, 80], [260, 320, 400], [130, 160, 190, 220],
                                          [0.2, 0.3, 0.4], [1.0, 1.2]))
    for radio, t, ap in itertools.product([25, 40, 60], [0.15, 0.2, 0.25, 0.3, 0.35], [0, 1]):
        sts = [componentes(imgs[n], radio, t, ap)[0] for n in nombres]
        for amin, amax1, atip, cmin, emin in rejilla_area:
            p = dict(POR_DEFECTO, radio=radio, t=t, apertura=ap, area_min=amin, area_max_1=amax1,
                     area_tipica=atip, contraste_min=cmin, e_min=emin)
            pred = np.array([clasificar(s, p).sum() for s in sts])
            m = float(np.abs(pred - r).mean())
            if mejor is None or m < mejor[0]:
                mejor = (m, p)
        print(f"radio={radio} t={t} apertura={ap} → mejor MAE val hasta ahora {mejor[0]:.2f}", flush=True)
    m, p = mejor
    p = dict(p)
    p["_nota"] = ("Parámetros calibrados por búsqueda en rejilla sobre la VALIDACIÓN SINTÉTICA "
                  f"(MAE val = {m:.2f}). No calibrados con fotos reales: no activan ninguna regla.")
    PARAMS.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(p, indent=1, ensure_ascii=False))


def evaluar(carpeta: Path):
    p = json.loads(PARAMS.read_text(encoding="utf-8")) if PARAMS.exists() else POR_DEFECTO
    nombres, imgs, reales = cargar(carpeta)
    clas = {n: contar(imgs[n], p) for n in nombres}
    ev_path = ML / "resultados" / "eval_sintetico.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else {}
    var = ev.get("recomendacion", {}).get("variante", "fp32")
    yolo = {n: ev.get("por_marco", {}).get(n, {}).get(var) for n in nombres}

    porb = {}
    for b in ("<50", "50-300", ">300"):
        idx = [n for n in nombres if banda(reales[n]) == b]
        porb[b] = {"n": len(idx), "mae": mae([reales[n] for n in idx], [clas[n] for n in idx]),
                   "sesgo": round(float(np.mean([clas[n] - reales[n] for n in idx])), 2) if idx else None}
    out = {
        "sintetico": True,
        "advertencia": "Datos SINTÉTICOS. Solo medición; no activa ninguna regla.",
        "parametros": {k: v for k, v in p.items() if not k.startswith("_")},
        "mae_total": mae([reales[n] for n in nombres], [clas[n] for n in nombres]),
        "por_densidad": porb,
    }
    if all(v is not None for v in yolo.values()):
        dif = [abs(clas[n] - yolo[n]) > 0.3 * max(yolo[n], 1) for n in nombres]
        dif5 = [abs(clas[n] - yolo[n]) > 0.3 * max(yolo[n], 1) and abs(clas[n] - yolo[n]) >= 5 for n in nombres]
        out["desacuerdo_con_yolo"] = {
            "variante_yolo": var,
            "definicion": "|clasico − yolo| > 0,30 × max(yolo, 1)",
            "%_marcos": round(100 * float(np.mean(dif)), 1),
            "%_marcos_con_dif_abs_>=5": round(100 * float(np.mean(dif5)), 1),
            "por_densidad_%": {b: round(100 * float(np.mean([d for n, d in zip(nombres, dif) if banda(reales[n]) == b])), 1)
                               for b in ("<50", "50-300", ">300")
                               if any(banda(reales[n]) == b for n in nombres)},
            "nota": "Con datos sintéticos; la regla de derivar al técnico NO se activa.",
        }
    out["por_marco"] = {n: {"real": reales[n], "clasico": clas[n], "yolo": yolo[n]} for n in nombres}
    (ML / "resultados").mkdir(exist_ok=True)
    (ML / "resultados" / "eval_clasico.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    if ev:
        ev["contador_clasico"] = {k: v for k, v in out.items() if k != "por_marco"}
        for n in nombres:
            ev["por_marco"].setdefault(n, {})["clasico"] = clas[n]
        ev_path.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "por_marco"}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrar", action="store_true", help="calibra con la validación sintética")
    ap.add_argument("--val", default=str(ML / "datasets" / "sint_v0" / "marcos" / "val"))
    ap.add_argument("--test", default=str(ML / "datasets" / "sint_v0" / "marcos" / "test"))
    a = ap.parse_args()
    if a.calibrar:
        calibrar(Path(a.val))
    else:
        evaluar(Path(a.test))


if __name__ == "__main__":
    main()
