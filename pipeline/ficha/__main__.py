"""Genera una ficha por finca (contracts/ficha.schema.json).

python -m pipeline.ficha --fincas data/fincas.geojson --out fichas/

- Lluvia (CHIRPS v3): anomalía sep–nov del año de floración frente a 1991–2020, y días ≥ 1 mm de nov–abr
  siguientes (diario 'sat', desagregado con NASA IMERG).
- Temperatura (NASA POWER): T2M y T2M_MAX corregidas por altitud desde la cota de la celda.
- Alertas: las vigentes de data/alertas_activas.json.
Las descargas se guardan en data/raw/ (no se sube a git); volver a correrlo no descarga nada.
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

from .chirps import CacheChirps, url_diaria, url_mensual
from .power import serie_diaria

RAIZ = Path(__file__).resolve().parents[2]
CLIMA_INI, CLIMA_FIN = 1991, 2020
MESES_FLORACION = (9, 10, 11)


def centroide(geom: dict) -> tuple[float, float]:
    anillo = geom["coordinates"][0][:-1]
    return mean(p[1] for p in anillo), mean(p[0] for p in anillo)  # (lat, lon)


def vigentes(alertas: list[dict], hoy: date) -> list[dict]:
    return [a for a in alertas
            if date.fromisoformat(a["fecha"]) <= hoy <= date.fromisoformat(a["vence"])
            and a.get("provincia", "La Convención") == "La Convención"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fincas", type=Path, default=RAIZ / "data/fincas.geojson")
    ap.add_argument("--out", type=Path, default=RAIZ / "fichas")
    ap.add_argument("--alertas", type=Path, default=RAIZ / "data/alertas_activas.json")
    ap.add_argument("--config", type=Path, default=RAIZ / "contracts/config.example.json")
    ap.add_argument("--fecha", type=date.fromisoformat, default=date.today(), help="fecha de generación (AAAA-MM-DD)")
    ap.add_argument("--floracion", type=int, default=None,
                    help="año de la floración de la campaña anterior (por defecto, el año anterior a --fecha)")
    ap.add_argument("--raw", type=Path, default=RAIZ / "data/raw")
    a = ap.parse_args()

    hoy = a.fecha
    anio_flor = a.floracion or hoy.year - 1
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    gradiente = cfg["correccion_altitud_c_por_km"]
    t_min, t_max = cfg["rango_temp_roya_c"]["min"], cfg["rango_temp_roya_c"]["max"]
    fincas = json.loads(a.fincas.read_text(encoding="utf-8"))["features"]
    alertas = vigentes(json.loads(a.alertas.read_text(encoding="utf-8"))["alertas"], hoy)
    puntos = [centroide(f["geometry"]) for f in fincas]

    # ---- CHIRPS v3 ----
    chirps = CacheChirps(a.raw / "chirps_puntos.json", puntos)
    print(f"CHIRPS mensual: floración {anio_flor} y climatología {CLIMA_INI}–{CLIMA_FIN}")
    u_flor = [url_mensual(anio_flor, m) for m in MESES_FLORACION]
    u_clima = [url_mensual(y, m) for y in range(CLIMA_INI, CLIMA_FIN + 1) for m in MESES_FLORACION]
    mensual = chirps.obtener(u_flor + u_clima)

    ini_ll, fin_ll = date(anio_flor, 11, 1), date(anio_flor + 1, 4, 30)
    dias = [ini_ll + timedelta(d) for d in range((fin_ll - ini_ll).days + 1)]
    print(f"CHIRPS diario (sat/IMERG): {ini_ll} a {fin_ll}")
    try:
        diario = chirps.obtener([url_diaria(d.year, d.month, d.day) for d in dias])
    except Exception as e:  # sin diario no se inventa nada: queda null y se declara
        print(f"  AVISO: sin CHIRPS diario ({e}); dias_lluvia_nov_abr = null")
        diario = None

    # ---- NASA POWER ----
    print("NASA POWER: T2M y T2M_MAX diarias")
    a.out.mkdir(parents=True, exist_ok=True)
    resumen = []
    for i, f in enumerate(fincas):
        pr = f["properties"]
        fid, alt = pr["finca_id"], pr["altitud_m"]
        lat, lon = puntos[i]
        pw = serie_diaria(lat, lon, date(CLIMA_INI, 1, 1), hoy, a.raw / f"power_{fid}_{hoy:%Y%m%d}.json")
        corr = gradiente * (alt - pw["elevacion_celda"]) / 1000

        t2m = sorted(pw["T2M"].items())[-90:]
        dias_roya = sum(t_min <= v + corr <= t_max for _, v in t2m)

        def tmax_flor(y):
            vals = [v for d, v in pw["T2M_MAX"].items() if d[:4] == str(y) and int(d[4:6]) in MESES_FLORACION]
            return mean(vals) + corr

        anom_tmax = tmax_flor(anio_flor) - mean(tmax_flor(y) for y in range(CLIMA_INI, CLIMA_FIN + 1))

        lluvia_flor = sum(mensual[u][i] for u in u_flor)
        clima_anual = [sum(mensual[url_mensual(y, m)][i] for m in MESES_FLORACION) for y in range(CLIMA_INI, CLIMA_FIN + 1)]
        anom_lluvia = 100 * (lluvia_flor / mean(clima_anual) - 1)
        dias_lluvia = None if diario is None else sum(1 for v in diario.values() if v[i] is not None and v[i] >= 1.0)

        ficha = {
            "version": f"{hoy.year}-{(hoy.year + 1) % 100:02d}.1",
            "finca_id": fid,
            "ejemplo": pr.get("ejemplo", False),
            "altitud_m": alt,
            "idioma": pr.get("idioma", "quz"),
            "generado": hoy.isoformat(),
            "clima": {
                "lluvia_floracion_anom_pct": round(anom_lluvia),
                "dias_lluvia_nov_abr": dias_lluvia,
                "dias_lluvia_aprox_mensual": False,
                "dias_temp_roya_90d": dias_roya,
                "tmax_floracion_anom_c": round(anom_tmax, 1),
                "fuentes": ["CHIRPS v3.0 (mensual y diario sat/IMERG)", "NASA POWER (T2M, T2M_MAX)"],
            },
            "registro": {
                "edad_mas_20_sin_recepa": pr.get("edad_mas_20_sin_recepa", False),
                "cosecha_alta_ano_pasado": pr.get("cosecha_alta_ano_pasado", False),
            },
            "alertas": alertas,
        }
        (a.out / f"{fid}.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        resumen.append((fid, alt, pw["elevacion_celda"], corr, t2m[-1][0], ficha["clima"]))

    print(f"\n{'finca':7} {'alt':>5} {'celda':>6} {'corr°C':>6} {'últ.T':>9} {'anomLl%':>8} {'díasLl':>6} {'díasRoya':>8} {'anomTmax':>8}")
    for fid, alt, el, corr, ult, c in resumen:
        print(f"{fid:7} {alt:5} {el:6.0f} {corr:+6.1f} {ult:>9} {c['lluvia_floracion_anom_pct']:8} "
              f"{str(c['dias_lluvia_nov_abr']):>6} {c['dias_temp_roya_90d']:8} {c['tmax_floracion_anom_c']:+8.1f}")
    print(f"\n{len(resumen)} fichas en {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
