"""NASA POWER: serie diaria por punto (T2M, T2M_MAX), con caché en disco."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
VACIO = -999.0


def serie_diaria(lat: float, lon: float, inicio: date, fin: date, cache: Path) -> dict:
    """Devuelve {'elevacion_celda': m, 'T2M': {fecha: °C}, 'T2M_MAX': {...}} sin días vacíos."""
    if cache.exists():
        crudo = json.loads(cache.read_text(encoding="utf-8"))
    else:
        r = requests.get(URL, timeout=120, params={
            "parameters": "T2M,T2M_MAX", "community": "AG", "format": "JSON",
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
        **{p: {d: v for d, v in params[p].items() if v != VACIO} for p in ("T2M", "T2M_MAX")},
    }
