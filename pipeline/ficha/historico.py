"""Anomalías que habría tenido la ficha en campañas pasadas: justifica los cortes de R-LLUVIA-01 y R-TEMP-01.

python -m pipeline.ficha.historico [--fecha 2026-10-03] [--anios 2012 2013 2016 2023]

Usa la caché de NASA POWER que deja `python -m pipeline.ficha` y las mismas funciones (clima.py).
Fila "oct A" = ficha generada a inicios de octubre del año A:
- Lluvia: días ≥ 1 mm de nov(A−1)–abr(A) con PRECTOTCORR, menos su normal 1991–2020 (igual en las 5 fincas: misma celda).
- Temperatura: días con T2M corregida por altitud en 17–25 °C de los 90 que terminan en la misma fecha que el último
  dato de la ficha actual (30 sep → jul–sep), menos su normal 1991–2020.
Un * marca que la regla se activa con el `rango` de contracts/rules.example.json.
"""
from __future__ import annotations

import argparse
import json
from datetime import date

from .__main__ import RAIZ, centroide
from .clima import CLIMA_FIN, CLIMA_INI, anomalia, dias_en_rango, dias_lluvia_temporada, misma_fecha
from .power import serie_diaria


def rango_de(reglas: list[dict], evidencia: str) -> dict:
    return next(r["rango"] for r in reglas if r["evidencia"] == evidencia and "rango" in r)


def activa(x: float | None, rango: dict) -> bool:
    return x is not None and rango.get("min", float("-inf")) <= x <= rango.get("max", float("inf"))


def fmt(x: float | None, rango: dict) -> str:
    return "—" if x is None else f"{x:+.1f}{'*' if activa(x, rango) else ''}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fecha", type=date.fromisoformat, default=date.today(), help="fecha de la caché de POWER")
    ap.add_argument("--anios", type=int, nargs="*", help="años A de las fichas (por defecto, todos)")
    ap.add_argument("--fincas", default=RAIZ / "data/fincas.geojson")
    ap.add_argument("--config", default=RAIZ / "contracts/config.example.json")
    ap.add_argument("--reglas", default=RAIZ / "contracts/rules.example.json")
    ap.add_argument("--raw", default=RAIZ / "data/raw")
    a = ap.parse_args()

    cfg = json.loads(open(a.config, encoding="utf-8").read())
    reglas = json.loads(open(a.reglas, encoding="utf-8").read())["reglas"]
    r_lluvia, r_temp = rango_de(reglas, "E_LLUVIA_DIAS"), rango_de(reglas, "E_TEMP_ROYA")
    t_min, t_max = cfg["rango_temp_roya_c"]["min"], cfg["rango_temp_roya_c"]["max"]
    fincas = json.loads(open(a.fincas, encoding="utf-8").read())["features"]
    clima = range(CLIMA_INI, CLIMA_FIN + 1)

    series = []
    for f in fincas:
        pr = f["properties"]
        lat, lon = centroide(f["geometry"])
        pw = serie_diaria(lat, lon, date(CLIMA_INI, 1, 1), a.fecha,
                          a.raw / f"power_{pr['finca_id']}_{a.fecha:%Y%m%d}.json")
        corr = cfg["correccion_altitud_c_por_km"] * (pr["altitud_m"] - pw["elevacion_celda"]) / 1000
        series.append((pr["finca_id"], pr["altitud_m"], corr, pw))

    prec = series[0][3]["PRECTOTCORR"]
    ult = max(series[0][3]["T2M"])
    fin_t = date(int(ult[:4]), int(ult[4:6]), int(ult[6:]))
    anios = a.anios or list(range(CLIMA_INI, fin_t.year + 1))

    lluvia_clima = [dias_lluvia_temporada(prec, y) for y in clima]
    base_ll = anomalia(None, lluvia_clima)

    def temp(corr, pw, anio):
        return dias_en_rango(pw["T2M"], misma_fecha(anio, fin_t), corr, t_min, t_max)

    base_t = {fid: anomalia(None, [temp(corr, pw, y) for y in clima]) for fid, _, corr, pw in series}

    print(f"Cortes: R-LLUVIA-01 {r_lluvia} · R-TEMP-01 {r_temp}. Ventana de temperatura: 90 días hasta el "
          f"{fin_t:%d-%m}. Normal {CLIMA_INI}–{CLIMA_FIN} ± desviación estándar interanual:")
    print(f"  días de lluvia (PRECTOTCORR): {base_ll['normal']} ± {base_ll['sd']}")
    for fid, alt, corr, _ in series:
        b = base_t[fid]
        print(f"  días 17–25 °C {fid} ({alt} m, {corr:+.1f} °C): {b['normal']} ± {b['sd']}")

    def anom_lluvia(temporada):  # temporada = año de noviembre
        ll = dias_lluvia_temporada(prec, temporada)
        return ll, None if ll is None else round(ll - base_ll["normal"], 1)

    def anom_temp(fid, corr, pw, anio):
        t = temp(corr, pw, anio)
        return None if t is None else round(t - base_t[fid]["normal"], 1)

    print("\n| Ficha | Lluvias | Días lluvia (anom) | " + " | ".join(f"{fid} T (anom)" for fid, *_ in series) + " |")
    print("|---|---|---|" + "---|" * len(series))
    for anio in anios:
        ll, anom_ll = anom_lluvia(anio - 1)
        celdas = [fmt(anom_temp(fid, corr, pw, anio), r_temp) for fid, _, corr, pw in series]
        dias = "—" if ll is None else f"{ll} ({fmt(anom_ll, r_lluvia)})"
        print(f"| oct {anio} | {anio - 1}-{anio % 100:02d} | {dias} | " + " | ".join(celdas) + " |")

    disparos = {"lluvia": sum(activa(anom_lluvia(y)[1], r_lluvia) for y in clima),
                **{fid: sum(activa(anom_temp(fid, corr, pw, y), r_temp) for y in clima) for fid, _, corr, pw in series}}
    print(f"\nActivaciones en {CLIMA_INI}–{CLIMA_FIN} (30 temporadas de lluvia que empiezan en esos años; "
          f"30 ventanas de temperatura): " + ", ".join(f"{k} {v}" for k, v in disparos.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
