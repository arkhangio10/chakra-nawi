"""NASA POWER: serie diaria por punto (T2M, T2M_MAX, PRECTOTCORR), con caché en disco."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
VACIO = -999.0
PARAMETROS = ("T2M", "T2M_MAX", "PRECTOTCORR")


def serie_diaria(lat: float, lon: float, inicio: date, fin: date, cache: Path,
                 parametros: tuple[str, ...] = PARAMETROS) -> dict:
    """Devuelve {'elevacion_celda': m, 'fuentes': [...], 'T2M': {AAAAMMDD: valor}, ...} sin días vacíos.

    Si la caché no tiene alguno de los parámetros pedidos, se vuelve a descargar (una sola llamada por punto).
    """
    crudo = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
    if crudo is None or not set(parametros) <= set(crudo["properties"]["parameter"]):
        r = requests.get(URL, timeout=300, params={
            "parameters": ",".join(parametros), "community": "AG", "format": "JSON",
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "start": inicio.strftime("%Y%m%d"), "end": fin.strftime("%Y%m%d"),
        })
        r.raise_for_status()
        crudo = r.json()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(crudo), encoding="utf-8")
    params = crudo["properties"]["parameter"]
    return {
        "elevacion_celda": crudo["geometry"]["coordinates"][2],
        "fuentes": crudo.get("header", {}).get("sources", []),
        **{p: {d: v for d, v in params[p].items() if v != VACIO} for p in parametros},
    }
