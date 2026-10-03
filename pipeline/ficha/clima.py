"""Conteos de días sobre series diarias {AAAAMMDD: valor} y su anomalía frente a 1991–2020.

La Convención es húmeda y templada todos los años: el valor absoluto casi no cambia entre años ni entre fincas.
Lo que informa es si **este año** se sale de lo normal. Por eso la anomalía compara una serie consigo misma
(temporada actual menos la climatología de la misma fuente, en el mismo punto y la misma ventana de calendario).
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, stdev

CLIMA_INI, CLIMA_FIN = 1991, 2020
MIN_ANIOS_CLIMA = 24  # 80% de los 30 años; con menos, la normal queda en null


def _clave(d: date) -> str:
    return d.strftime("%Y%m%d")


def misma_fecha(anio: int, ref: date) -> date:
    """La fecha ref en otro año (el 29 de febrero pasa al 28)."""
    return date(anio, ref.month, 28 if (ref.month, ref.day) == (2, 29) else ref.day)


def dias_lluvia_temporada(pr: dict[str, float], anio: int, umbral_mm: float = 1.0) -> int | None:
    """Días con lluvia ≥ umbral de nov(anio)–abr(anio+1). Sin el 29 de febrero: 181 días todos los años.
    None si falta algún día."""
    d, fin, n = date(anio, 11, 1), date(anio + 1, 4, 30), 0
    while d <= fin:
        if (d.month, d.day) != (2, 29):
            v = pr.get(_clave(d))
            if v is None:
                return None
            n += v >= umbral_mm
        d += timedelta(1)
    return n


def dias_en_rango(t: dict[str, float], fin: date, corr: float, t_min: float, t_max: float, n: int = 90) -> int | None:
    """Días de los n que terminan en fin (incluido) con t + corr en [t_min, t_max]. None si falta algún día."""
    cuenta = 0
    for k in range(n):
        v = t.get(_clave(fin - timedelta(k)))
        if v is None:
            return None
        cuenta += t_min <= v + corr <= t_max
    return cuenta


def anomalia(actual: float | None, climatologia: list[float | None]) -> dict:
    """{'normal', 'sd', 'anom'} con 1 decimal. sd = desviación estándar interanual (muestral).
    anom = actual − normal (ya redondeada), así normal + anom reproduce el valor actual de la misma fuente."""
    vals = [v for v in climatologia if v is not None]
    if len(vals) < MIN_ANIOS_CLIMA:
        return {"normal": None, "sd": None, "anom": None}
    normal = round(mean(vals), 1)
    return {
        "normal": normal,
        "sd": round(stdev(vals), 1),
        "anom": None if actual is None else round(actual - normal, 1),
    }
