"""Experimento SEMI-REAL, de punta a punta y sin intervención; ejecutar desde ml/.

1. recortes_reales.py   descarga fotos de Scolytinae reales (CC-BY-SA-4.0) y recorta cada escarabajo
2. sintetico.py         genera datasets/semireal_v1 (70 % de las brocas son recortes reales;
                        la PRUEBA usa una especie que el entrenamiento nunca ve)
3. entrenar.py          afina YOLOv8n desde el modelo "difíciles" (CPU, --horas)
4. exportar.py          ONNX fp32 + int8 como broca-y8n-v0-semireal (NO se copia a la PWA)
5. evaluar.py           el modelo vigente de la PWA, el de difíciles y el semi-real, en los mismos
                        marcos semi-reales de prueba; y el semi-real en el test difícil anterior
                        (para ver que no empeora en lo que ya hacía bien)
6. resultados/semireal/comparacion.json y RESUMEN.md

Los recortes NO son broca. Todo error medido aquí es con un SUSTITUTO y no se presenta como
desempeño en broca real. El contrato (umbral 0,60) no se toca; cambiar el modelo de la PWA
es decisión del equipo.

Uso:
    python semireal.py                 # todo (~1,5–2 h en CPU)
    python semireal.py --horas 0.3     # entrenamiento más corto
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ML = Path(__file__).resolve().parent
OUT = ML / "resultados" / "semireal"
RECORTES = "datasets/recortes_scolytinae"
DATOS = "datasets/semireal_v1"
CORRIDA = "y8n_semireal_v1"
NOMBRE = "broca-y8n-v0-semireal"
VIGENTE = "broca-y8n-v0-sint"                 # el que usa hoy apps/campo
DIFICILES = "broca-y8n-v0-sint-dificiles"


def leer(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def escribir(p, contenido):
    Path(p).write_text(json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")


def ejecutar(etapa, *args):
    escribir(OUT / "estado.json", {"etapa": etapa, "estado": "en curso",
                                   "inicio": dt.datetime.now().isoformat(timespec="seconds")})
    print(f"[{dt.datetime.now():%H:%M}] {etapa}", flush=True)
    with (OUT / f"{etapa}.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, *args], cwd=ML, stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--horas", type=float, default=1.0, help="tope del entrenamiento en CPU")
    ap.add_argument("--train", type=int, default=400)
    ap.add_argument("--p-real", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if not (ML / RECORTES / "recortes.json").exists():
        ejecutar("1_recortes", "recortes_reales.py", "--salida", RECORTES)
    if not (ML / DATOS / "marcos" / "test" / "conteos.json").exists():
        ejecutar("2_generacion", "sintetico.py", "--salida", DATOS, "--recortes", RECORTES,
                 "--p-real", str(a.p_real), "--train", str(a.train), "--val", "60", "--test", "60",
                 "--workers", str(a.workers), "--semilla", "20261005")
    inicial = ML / "runs" / "y8n_sint_dificiles_v1" / "weights" / "best.pt"
    if not inicial.exists():
        inicial = ML / "runs" / "y8n_sint_v0" / "weights" / "best.pt"
    if not (ML / "runs" / CORRIDA / "resumen_entrenamiento.json").exists():
        ejecutar("3_entrenamiento", "entrenar.py", "--datos", f"{DATOS}/data.yaml", "--modelo", str(inicial),
                 "--nombre", CORRIDA, "--horas", str(a.horas),
                 "--nota", "Sintéticos + recortes de Scolytinae reales (CC-BY-SA-4.0), NO broca. Sustituto.")
    ejecutar("4_exportacion", "exportar.py", "--pesos", f"runs/{CORRIDA}/weights/best.pt", "--nombre", NOMBRE,
             "--no-copiar", "--leyenda", "sintéticos + recortes de Scolytinae reales (sustituto, no broca)")

    evals = {
        "vigente_semireal": (VIGENTE, DATOS),
        "dificiles_semireal": (DIFICILES, DATOS),
        "semireal_semireal": (NOMBRE, DATOS),
        "semireal_dificiles": (NOMBRE, "datasets/sint_dificiles_v1"),
        "dificiles_dificiles": (DIFICILES, "datasets/sint_dificiles_v1"),
    }
    for carpeta, (modelo, datos) in evals.items():
        if not (ML / "modelos" / f"{modelo}.onnx").exists() or not (ML / datos / "marcos" / "test").exists():
            print("se omite", carpeta, flush=True)
            continue
        ejecutar(f"5_eval_{carpeta}", "evaluar.py", "--nombre", modelo, "--marcos", f"{datos}/marcos/test",
                 "--val", f"{datos}/marcos/val", "--salida", str(OUT / carpeta))

    filas = []
    for carpeta, (modelo, datos) in evals.items():
        f = OUT / carpeta / "eval_sintetico.json"
        if not f.exists():
            continue
        ev = leer(f)
        for var in ("fp32", "int8"):
            d = ev["variantes"].get(var)
            if not d:
                continue
            cal = ev.get("umbral_propuesto", {}).get("variantes", {}).get(var, {})
            filas.append({
                "modelo": modelo, "prueba": Path(datos).name, "variante": var, "mb": d["mb"],
                "mae_060": d["conteo_total"]["mae"], "sesgo_060": d["conteo_total"].get("sesgo"),
                "mae_por_densidad_060": {b: x.get("mae") for b, x in d["por_densidad"].items()},
                "fp_marcos_vacios": d["marcos_con_0_brocas"]["falsos_positivos_medios"],
                "precision": d["deteccion_iou50"]["precision"], "recall": d["deteccion_iou50"]["recall"],
                "score_val": cal.get("score_elegido_en_val"),
                "mae_prueba_score_val": cal.get("prueba_con_ese_score", {}).get("conteo_total", {}).get("mae"),
            })
    comp = {"advertencia": "Sintéticos + recortes de escarabajos Scolytinae reales (no broca). "
                           "La prueba semi-real usa una especie (Xylosandrus compactus) que el entrenamiento no vio. "
                           "NO es desempeño en broca real.",
            "contrato_modificado": False, "pwa_modificada": False, "filas": filas}
    escribir(OUT / "comparacion.json", comp)

    lineas = ["# Experimento semi-real (sustituto, NO broca)", "",
              f"Generado {dt.datetime.now():%Y-%m-%d %H:%M} por `ml/semireal.py`.", "",
              "Prueba `semireal_v1`: 70 % de las brocas son recortes de *Xylosandrus compactus* (especie no vista "
              "en entrenamiento) y los escarabajos grandes son *Phloeosinus dentatus* (no vistos). "
              "Prueba `sint_dificiles_v1`: el test anterior, 100 % dibujado.", "",
              "| Modelo | Prueba | Var. | MiB | MAE a 0,60 | Sesgo | FP en vacíos | P | R | Score val | MAE con score val |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for f in filas:
        lineas.append(f"| {f['modelo']} | {f['prueba']} | {f['variante']} | {f['mb']} | {f['mae_060']} | "
                      f"{f['sesgo_060']} | {f['fp_marcos_vacios']} | {f['precision']} | {f['recall']} | "
                      f"{f['score_val']} | {f['mae_prueba_score_val']} |")
    lineas += ["", "Fuente de los recortes: Marais et al. (2024) PLOS ONE, doi:10.1371/journal.pone.0310716 "
               "(Hugging Face `ChristopherMarais/Andrew_Alpha_training_data`, CC-BY-SA-4.0).",
               "El modelo NO se copió a `apps/campo`; el contrato (0,60) no cambió.", ""]
    (OUT / "RESUMEN.md").write_text("\n".join(lineas), encoding="utf-8")
    escribir(OUT / "estado.json", {"etapa": "completo", "estado": "completo",
                                   "fin": dt.datetime.now().isoformat(timespec="seconds")})
    print("\n".join(lineas), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        escribir(OUT / "error.json", {"error": str(exc), "tipo": type(exc).__name__})
        raise
