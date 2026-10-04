"""
Recortes de escarabajos REALES (Scolytinae) para el generador semi-real.

Fuente: "Bark Beetle Grouped Images" (Marais et al., PLOS ONE 2024,
doi:10.1371/journal.pone.0310716), en Hugging Face
`ChristopherMarais/Andrew_Alpha_training_data`, licencia CC-BY-SA-4.0.
Fotos de 3456×5184 con ~13–40 escarabajos en etanol sobre baldosa blanca.

NO SON BROCA (Hypothenemus hampei). Son escarabajos de la misma subfamilia
(Scolytinae), pequeños y oscuros. Sirven para que el modelo vea textura, patas
y brillo de insectos reales en vez de un elipsoide dibujado. El error medido con
ellos es error con un SUSTITUTO y nunca se presenta como desempeño en broca.

Grupos (separados por especie para que la prueba no comparta insectos con el
entrenamiento):
  entrenamiento  Coccotrypes dactyliperda, Pityophthorus juglandis,
                 Xyleborinus saxesenii, Xyleborus affinis          → clase broca
  prueba         Xylosandrus compactus (especie que el modelo nunca ve) → clase broca
  distractor     Hylesinus varius, Platypus cylindrus (entrenamiento) y
                 Phloeosinus dentatus (prueba): escarabajos más grandes, NO broca

Salida: datasets/recortes_scolytinae/
  fotos/<especie>/<archivo>.jpg        originales descargados (caché)
  recortes/<grupo>/<id>.png            RGBA: color + alfa suave (incluye patas)
  recortes/<grupo>/<id>_cuerpo.png     máscara del cuerpo sin patas (define la caja)
  recortes.json                        metadatos: especie, vial, largo del cuerpo en px
  ATRIBUCION.txt                       licencia y cita
  muestra.jpg                          hoja de contacto para revisar a ojo

Uso:
  python recortes_reales.py                 # descarga (~200 MB) y recorta
  python recortes_reales.py --fotos 6       # menos fotos por especie (prueba rápida)
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

ML = Path(__file__).resolve().parent
REPO = "ChristopherMarais/Andrew_Alpha_training_data"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main/"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main/"

GRUPOS = {
    "entrenamiento": ["Coccotrypes_dactyliperda", "Pityophthorus_juglandis",
                      "Xyleborinus_saxesenii", "Xyleborus_affinis"],
    "prueba": ["Xylosandrus_compactus"],
    "distractor_entrenamiento": ["Hylesinus_varius", "Platypus_cylindrus"],
    "distractor_prueba": ["Phloeosinus_dentatus"],
}
LARGO_GUARDADO = 64      # largo del cuerpo (px) en el recorte guardado; la broca se pega a ≈21 px


def listar(ruta: str) -> list[dict]:
    with urllib.request.urlopen(API + ruta + "?recursive=true", timeout=60) as r:
        return json.load(r)


def elegir_fotos(especie: str, n: int) -> list[str]:
    """n fotos repartidas entre viales y subconjuntos (determinista)."""
    fotos = sorted(x["path"] for x in listar(f"Data/{especie}")
                   if x["type"] == "file" and x["path"].lower().endswith((".jpg", ".jpeg", ".png")))
    por_carpeta: dict[str, list[str]] = {}
    for f in fotos:
        por_carpeta.setdefault(f.rsplit("/", 1)[0], []).append(f)
    elegidas, ronda = [], 0
    carpetas = sorted(por_carpeta)
    while len(elegidas) < n and any(len(v) > ronda for v in por_carpeta.values()):
        for c in carpetas:
            if len(por_carpeta[c]) > ronda and len(elegidas) < n:
                elegidas.append(por_carpeta[c][ronda])
        ronda += 1
    return sorted(set(elegidas))


def descargar(ruta_remota: str, destino: Path) -> Path:
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    urllib.request.urlretrieve(RAW + ruta_remota, tmp)
    tmp.replace(destino)
    return destino


def segmentar(bgr: np.ndarray):
    """Devuelve una lista de (recorte_rgba, cuerpo, largo_cuerpo) por escarabajo aislado."""
    f = 0.5
    img = cv2.resize(bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Fondo: cierre morfológico grande (borra los insectos) → iluminación de la baldosa
    fondo = cv2.morphologyEx(gris, cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8))
    fondo = cv2.GaussianBlur(fondo, (0, 0), 25)
    oscuro = fondo - gris
    m = ((oscuro > 28) | ((hsv[..., 1] > 70) & (oscuro > 12))).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    # rellenar huecos (reflejos del flash dentro del cuerpo)
    cont, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lleno = np.zeros_like(m)
    cv2.drawContours(lleno, cont, -1, 255, -1)
    # cuerpo: apertura que borra patas y antenas
    cuerpo_g = cv2.morphologyEx(lleno, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))

    n, lab, st, _ = cv2.connectedComponentsWithStats(cuerpo_g, 8)
    areas = st[1:, cv2.CC_STAT_AREA]
    grandes = areas[areas > 400]
    if len(grandes) == 0:
        return []
    med = float(np.median(grandes))
    H, W = cuerpo_g.shape
    salida = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 0.4 * med or a > 1.6 * med:              # restos o insectos que se tocan
            continue
        if x <= 2 or y <= 2 or x + w >= W - 2 or y + h >= H - 2:
            continue
        cuerpo = (lab == i).astype(np.uint8) * 255
        c, _ = cv2.findContours(cuerpo, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(c, key=cv2.contourArea)
        per = cv2.arcLength(c, True)
        circ = 4 * math.pi * cv2.contourArea(c) / max(per * per, 1)
        sat = float(hsv[..., 1][lab == i].mean())
        if circ > 0.82 and sat < 60:                     # la bolita metálica de referencia
            continue
        if cv2.contourArea(c) / max(cv2.contourArea(cv2.convexHull(c)), 1) < 0.85:
            continue                                     # forma rara: probablemente dos insectos
        (_, _), (rw, rh), _ = cv2.minAreaRect(c)
        largo = max(rw, rh)
        if largo < 20 or max(rw, rh) / max(min(rw, rh), 1) > 4.0:
            continue
        # recorte con margen para las patas
        pad = int(0.35 * largo)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
        # alfa: componente de la máscara completa (con patas) que contiene al cuerpo
        nn, lab2 = cv2.connectedComponents(lleno[y0:y1, x0:x1], connectivity=8)
        ids = np.unique(lab2[cuerpo[y0:y1, x0:x1] > 0])
        ids = ids[ids > 0]
        if len(ids) == 0:
            continue
        completo = np.isin(lab2, ids).astype(np.uint8) * 255
        # no incluir trozos de otros cuerpos que toquen las patas
        otros = (cuerpo_g[y0:y1, x0:x1] > 0) & (cuerpo[y0:y1, x0:x1] == 0)
        completo[otros] = 0
        alfa = cv2.GaussianBlur(completo.astype(np.float32) / 255, (0, 0), 0.8)
        rgb = img[y0:y1, x0:x1].astype(np.float32)
        # quitar el halo blanco del fondo: el color de borde se oscurece hacia el interior
        rgba = np.dstack([rgb, alfa * 255]).clip(0, 255).astype(np.uint8)
        k = LARGO_GUARDADO / largo
        rgba = cv2.resize(rgba, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        cu = cv2.resize(cuerpo[y0:y1, x0:x1], (rgba.shape[1], rgba.shape[0]), interpolation=cv2.INTER_AREA)
        salida.append((rgba, cu, largo * k))
    return salida


def hoja_contacto(rutas: list[Path], destino: Path, n=120, lado=72):
    cols = 12
    filas = math.ceil(min(n, len(rutas)) / cols)
    hoja = np.full((filas * lado, cols * lado, 3), 245, np.uint8)
    for j, r in enumerate(rutas[:n]):
        rgba = cv2.imread(str(r), cv2.IMREAD_UNCHANGED)
        h, w = rgba.shape[:2]
        k = (lado - 4) / max(h, w)
        rgba = cv2.resize(rgba, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
        a = rgba[..., 3:4].astype(np.float32) / 255
        celda = hoja[(j // cols) * lado:(j // cols + 1) * lado, (j % cols) * lado:(j % cols + 1) * lado]
        hh, ww = rgba.shape[:2]
        oy, ox = (lado - hh) // 2, (lado - ww) // 2
        reg = celda[oy:oy + hh, ox:ox + ww].astype(np.float32)
        celda[oy:oy + hh, ox:ox + ww] = (rgba[..., :3] * a + reg * (1 - a)).astype(np.uint8)
    cv2.imwrite(str(destino), hoja)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default=str(ML / "datasets" / "recortes_scolytinae"))
    ap.add_argument("--fotos", type=int, default=12, help="fotos por especie de broca-sustituto")
    ap.add_argument("--fotos-distractor", type=int, default=6)
    a = ap.parse_args()

    out = Path(a.salida)
    (out / "fotos").mkdir(parents=True, exist_ok=True)
    tareas = []
    for grupo, especies in GRUPOS.items():
        n = a.fotos_distractor if grupo.startswith("distractor") else a.fotos
        for esp in especies:
            for remota in elegir_fotos(esp, n):
                local = out / "fotos" / esp / remota.replace(f"Data/{esp}/", "").replace("/", "__")
                tareas.append((grupo, esp, remota, local))
    print(f"{len(tareas)} fotos por descargar/usar", flush=True)
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda t: descargar(t[2], t[3]), tareas))
    print("descarga lista", flush=True)

    meta = []
    for grupo, esp, remota, local in tareas:
        bgr = cv2.imread(str(local))
        if bgr is None:
            print("no se pudo leer", local)
            continue
        vial = remota.split("/")[2] if len(remota.split("/")) > 3 else ""
        piezas = segmentar(bgr)
        d = out / "recortes" / grupo
        d.mkdir(parents=True, exist_ok=True)
        for j, (rgba, cuerpo, largo) in enumerate(piezas):
            rid = f"{esp}__{local.stem}__{j:02d}"
            cv2.imwrite(str(d / f"{rid}.png"), rgba)
            cv2.imwrite(str(d / f"{rid}_cuerpo.png"), cuerpo)
            meta.append({"id": rid, "grupo": grupo, "especie": esp.replace("_", " "), "vial": vial,
                         "foto": remota, "largo_cuerpo_px": round(float(largo), 1)})
        print(f"{grupo:26s} {esp:26s} {local.name:40s} {len(piezas):3d} recortes", flush=True)

    resumen = {}
    for m in meta:
        resumen.setdefault(m["grupo"], {}).setdefault(m["especie"], 0)
        resumen[m["grupo"]][m["especie"]] += 1
    (out / "recortes.json").write_text(json.dumps(
        {"fuente": f"https://huggingface.co/datasets/{REPO}", "licencia": "CC-BY-SA-4.0",
         "cita": "Marais et al. (2024) Progress in developing a bark beetle identification tool. "
                 "PLOS ONE. doi:10.1371/journal.pone.0310716",
         "advertencia": "Escarabajos Scolytinae reales, NO broca. Sustituto para el generador semi-real.",
         "resumen": resumen, "recortes": meta}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "ATRIBUCION.txt").write_text(
        "Recortes derivados de 'Bark Beetle Grouped Images for AI Classification'\n"
        f"https://huggingface.co/datasets/{REPO}  ·  licencia CC-BY-SA-4.0\n"
        "Marais et al. (2024) PLOS ONE, doi:10.1371/journal.pone.0310716\n"
        "Si se redistribuyen estos recortes o imágenes derivadas, deben llevar esta atribución y la misma licencia.\n"
        "NO son broca (Hypothenemus hampei): son un sustituto de la misma subfamilia.\n", encoding="utf-8")
    for g in GRUPOS:
        rutas = sorted(p for p in (out / "recortes" / g).glob("*.png") if not p.stem.endswith("_cuerpo"))
        if rutas:
            hoja_contacto(rutas[:: max(1, len(rutas) // 60)], out / f"muestra_{g}.jpg", n=60)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
