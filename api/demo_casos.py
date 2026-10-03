"""Carga 5 casos de DEMOSTRACIÓN en una API en marcha, uno por estado (y uno de lluvias), para ver el panel.

Las fotos son imágenes SINTÉTICAS rotuladas "DEMO" (puntos oscuros dibujados donde van las cajas): no son broca
ni resultados del modelo. Los caso_id son fijos, así que correrlo dos veces no duplica nada (POST idempotente).

Uso:  python -m api.demo_casos [--api http://localhost:8000]
Requiere httpx (de api/requirements.txt). Si Pillow está instalado, sube fotos; si no, los casos van sin foto.
"""
from __future__ import annotations

import argparse
import io
import json
import random
import sys
import uuid

import httpx

LADO = 1216  # marco rectificado de 10×10 cm (contracts/modelo-io.md)
ESPACIO = uuid.UUID("6f1d2c1e-9b8a-4c4e-8a4f-0c6a3d2b1e00")


def cajas(n: int, semilla: int) -> list[list[float]]:
    rnd = random.Random(semilla)
    return [[round(rnd.uniform(.06, .94), 4), round(rnd.uniform(.06, .94), 4),
             round(rnd.uniform(.014, .02), 4), round(rnd.uniform(.007, .011), 4)] for _ in range(n)]


def foto_trampa(cs: list[list[float]], borrosa: bool = False) -> bytes | None:
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        return None
    rnd = random.Random(len(cs))
    img = Image.new("RGB", (LADO, LADO), (244, 243, 238))
    d = ImageDraw.Draw(img)
    for _ in range(400):  # polvo y restos
        x, y, r = rnd.uniform(0, LADO), rnd.uniform(0, LADO), rnd.uniform(.6, 2.2)
        g = rnd.randint(170, 215)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(g, g - 8, g - 20))
    for xc, yc, w, h in cs:
        x, y, w, h = xc * LADO, yc * LADO, w * LADO, h * LADO
        d.ellipse([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=(rnd.randint(30, 60), 24, 16))
    d.text((18, 14), "DEMO - imagen sintetica, no es broca real", fill=(150, 150, 150))
    if borrosa:
        img = img.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * .55))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=82)
    return out.getvalue()


def foto_hojas() -> bytes | None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    rnd = random.Random(7)
    img = Image.new("RGB", (LADO, LADO), (240, 240, 236))
    d = ImageDraw.Draw(img)
    for cx in (260, 608, 956):
        d.ellipse([cx - 170, 220, cx + 170, 1000], fill=(96, 138, 70), outline=(60, 96, 44), width=4)
        d.line([cx, 230, cx, 990], fill=(150, 180, 110), width=5)
        for _ in range(14):
            x, y, r = cx + rnd.uniform(-110, 110), rnd.uniform(330, 900), rnd.uniform(6, 16)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(232, 140, 30))
    d.text((18, 14), "DEMO - imagen sintetica", fill=(150, 150, 150))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=82)
    return out.getvalue()


def probs(**p: float) -> dict:
    base = {"sin_problema": 0, "broca": 0, "roya": 0, "clima_floracion": 0, "plantas_viejas": 0, "otra": 0}
    return base | p


def casos() -> list[tuple[dict, bytes | None]]:
    def caso(nombre, finca, creado, mes, temporada, foto_tipo, conteo, respuestas, resultado, calidad=(True, 0)):
        cid = str(uuid.uuid5(ESPACIO, nombre))
        return {
            "caso_id": cid, "finca_id": finca, "ficha_version": "2026-27.1", "creado": creado, "mes": mes,
            "temporada": temporada,
            "foto": {"tipo": foto_tipo, "archivo": f"demo_{cid[:8]}.jpg", "calidad_ok": calidad[0], "reintentos": calidad[1]},
            "conteo": conteo, "respuestas": respuestas, "resultado": resultado, "app_version": "demo",
        }

    def conteo(n, clasico, anterior, tendencia, semilla, dudoso=False):
        return {"yolo": n, "clasico": clasico, "anterior": anterior, "tendencia": tendencia, "dudoso": dudoso,
                "modelo": "broca-y11n-v1", "cajas": cajas(n, semilla)}

    urgente = conteo(212, 230, 97, "sube", 1)
    dudoso = conteo(37, 61, 40, "igual", 2, dudoso=True)
    amarillo = conteo(143, 151, 88, "sube", 3)
    verde = conteo(9, 10, 21, "baja", 4)
    return [
        (caso("urgente", "LC-002", "2026-08-14T08:40:00-05:00", 8, "fin_seca", "trampa", urgente, {"granos": "3+"},
              {"estado": "tecnico_urgente", "causa": "broca", "mensaje": "R_TECNICO_URGENTE",
               "probabilidades": probs(sin_problema=.02, broca=.9, roya=.03, clima_floracion=.02, plantas_viejas=.01, otra=.02),
               "reglas": ["R-GRANOS-03", "R-TRAMPA-01", "R-ALERTA-01"]}),
         foto_trampa(urgente["cajas"])),
        (caso("tecnico", "LC-003", "2026-08-15T10:05:00-05:00", 8, "fin_seca", "trampa", dudoso, {"granos": "no_se"},
              {"estado": "tecnico", "causa": None, "mensaje": "R_TECNICO",
               "probabilidades": probs(sin_problema=.3, broca=.3, roya=.12, clima_floracion=.12, plantas_viejas=.08, otra=.08),
               "reglas": []}, calidad=(False, 2)),
         foto_trampa(dudoso["cajas"], borrosa=True)),
        (caso("amarillo-broca", "LC-001", "2026-08-15T09:12:00-05:00", 8, "fin_seca", "trampa", amarillo, {"granos": "1-2"},
              {"estado": "amarillo", "causa": "broca", "mensaje": "R_BROCA",
               "probabilidades": probs(sin_problema=.08, broca=.71, roya=.07, clima_floracion=.06, plantas_viejas=.04, otra=.04),
               "reglas": ["R-GRANOS-02", "R-TRAMPA-01", "R-ALERTA-01"]}),
         foto_trampa(amarillo["cajas"])),
        (caso("amarillo-roya", "LC-005", "2026-10-02T16:20:00-05:00", 1, "lluvias", "hojas", None, {"polvo_naranja": "si"},
              {"estado": "amarillo", "causa": "roya", "mensaje": "R_ROYA",
               "probabilidades": probs(sin_problema=.1, broca=.05, roya=.72, clima_floracion=.05, plantas_viejas=.04, otra=.04),
               "reglas": ["R-ROYA-01", "R-LLUVIA-01", "R-TEMP-01"]}),
         foto_hojas()),
        (caso("verde", "LC-004", "2026-08-16T07:55:00-05:00", 8, "fin_seca", "trampa", verde, {"granos": "0"},
              {"estado": "verde", "causa": "sin_problema", "mensaje": "R_VERDE",
               "probabilidades": probs(sin_problema=.66, broca=.12, roya=.07, clima_floracion=.06, plantas_viejas=.05, otra=.04),
               "reglas": ["R-GRANOS-01", "R-TRAMPA-02"]}),
         foto_trampa(verde["cajas"])),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    a = ap.parse_args()
    for c, foto in casos():
        files = {"foto": (c["foto"]["archivo"], foto, "image/jpeg")} if foto else None
        r = httpx.post(f"{a.api.rstrip('/')}/casos", data={"caso": json.dumps(c)}, files=files, timeout=30)
        estado = "duplicado" if r.status_code == 200 else "creado" if r.status_code == 201 else f"ERROR {r.status_code} {r.text[:300]}"
        print(f"{c['resultado']['estado']:16} {c['finca_id']}  {'con foto' if foto else 'sin foto':9} {estado}")
        if r.status_code >= 400:
            return 1
    print(f"Abre {a.api.rstrip('/')}/panel/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
