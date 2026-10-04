"""Comparación y reentrenamiento SOLO SINTÉTICOS; ejecutar desde ml/.

Conserva sint_v0, las corridas originales y las métricas históricas.
No entrena con fotos reales ni publica resultados de broca real.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ML = Path(__file__).resolve().parent
OUT = ML / "resultados" / "p2"


def leer(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def escribir(p, contenido):
    Path(p).write_text(json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")


def ejecutar(etapa, *args):
    escribir(OUT / "estado.json", {"etapa": etapa, "estado": "en curso",
                                    "sintetico": True, "inicio_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    print(etapa, flush=True)
    with (OUT / f"{etapa}.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, *args], cwd=ML, stdout=log, stderr=subprocess.STDOUT,
                       check=True, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--esperar-y11", action="store_true", help="espera el entrenamiento ya iniciado")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    resumen11 = ML / "runs/y11n_sint_v0/resumen_entrenamiento.json"
    if a.esperar_y11:
        escribir(OUT / "estado.json", {"etapa": "entrenamiento_y11", "estado": "esperando", "sintetico": True})
        while not resumen11.exists():
            time.sleep(10)
    else:
        ejecutar("entrenamiento_y11", "entrenar.py", "--modelo", "weights/yolo11n.pt",
                 "--nombre", "y11n_sint_v0", "--horas", "0.75")

    ejecutar("exportacion_y11", "exportar.py", "--pesos", "runs/y11n_sint_v0/weights/best.pt",
             "--nombre", "broca-y11n-v0-sint")
    for nombre, carpeta in (("broca-y8n-v0-sint", "y8_original"),
                             ("broca-y11n-v0-sint", "y11_original")):
        ejecutar(f"evaluacion_{carpeta}", "evaluar.py", "--nombre", nombre,
                 "--salida", str(OUT / carpeta))

    ejecutar("generacion_dificiles", "sintetico.py", "--salida", "datasets/sint_dificiles_v1",
             "--train", "400", "--val", "60", "--test", "60", "--workers", "4", "--semilla", "20261004")
    ejecutar("entrenamiento_dificiles", "entrenar.py", "--datos", "datasets/sint_dificiles_v1/data.yaml",
             "--modelo", "runs/y8n_sint_v0/weights/best.pt", "--nombre", "y8n_sint_dificiles_v1", "--horas", "0.75")
    mejorado = "broca-y8n-v0-sint-dificiles"
    ejecutar("exportacion_dificiles", "exportar.py", "--pesos", "runs/y8n_sint_dificiles_v1/weights/best.pt",
             "--nombre", mejorado)
    # Todos los modelos ven los mismos marcos difíciles; no mezclar MAE entre datasets.
    for nombre, carpeta in (("broca-y8n-v0-sint", "y8_dificiles"),
                             ("broca-y11n-v0-sint", "y11_dificiles"), (mejorado, "y8_reentrenado")):
        ejecutar(f"evaluacion_{carpeta}", "evaluar.py", "--nombre", nombre,
                 "--marcos", "datasets/sint_dificiles_v1/marcos/test",
                 "--val", "datasets/sint_dificiles_v1/marcos/val", "--salida", str(OUT / carpeta))
    params = "contador_clasico_dificiles.json"
    ejecutar("calibracion_clasico", "contador_clasico.py", "--calibrar",
             "--val", "datasets/sint_dificiles_v1/marcos/val", "--params", params)
    ejecutar("evaluacion_clasico", "contador_clasico.py", "--test", "datasets/sint_dificiles_v1/marcos/test",
             "--params", params, "--evaluacion", str(OUT / "y8_reentrenado/eval_sintetico.json"),
             "--salida", str(OUT / "y8_reentrenado"))

    filas = []
    for carpeta in ("y8_original", "y11_original", "y8_dificiles", "y11_dificiles", "y8_reentrenado"):
        ev = leer(OUT / carpeta / "eval_sintetico.json")
        for var, d in ev["variantes"].items():
            cal = ev["umbral_propuesto"]["variantes"][var]
            filas.append({"modelo": ev["modelo"], "dataset": ev["carpeta"], "variante": var,
                          "mb": d["mb"], "mae_contrato_060": d["conteo_total"]["mae"],
                          "latencia_ms": d["latencia_ms_mosaico"],
                          "score_elegido_val": cal["score_elegido_en_val"],
                          "mae_val_min": min(x["mae"] for x in cal["curva_val"]),
                          "mae_prueba_score_calibrado": cal["prueba_con_ese_score"]["conteo_total"]["mae"]})
    comparacion = {"sintetico": True,
                  "advertencia": "SOLO datos sintéticos; NO es desempeño en broca real ni en el sustituto.",
                  "score_contrato": 0.60, "filas": filas,
                  "sin_fotos_reales": "broca-y8n-v1 pendiente de fotos etiquetadas y división por sesión"}
    escribir(OUT / "comparacion_sintetica.json", comparacion)
    meta_path = ML / "modelos/metadata.json"
    meta = leer(meta_path)
    meta["evaluacion_historica"] = {"archivo": "ml/resultados/eval_sintetico.json", "score_conteo": 0.25,
                                  "nota": "Resultados históricos conservados; no corresponden al conteo vigente a 0,60"}
    meta["evaluacion_sintetica"]["archivo"] = "ml/resultados/p2/y8_original/eval_sintetico.json"
    meta["evaluacion_sintetica"].pop("umbral_score_propuesto", None)
    meta["evaluacion_sintetica"]["umbral_score_contrato"] = 0.60
    meta["evaluacion_sintetica"]["nota"] = "0,60 adoptado en contrato; recalibraciones experimentales por modelo en resultados/p2."
    meta["experimentos_p2"] = {"sintetico": True, "comparacion": "ml/resultados/p2/comparacion_sintetica.json",
                              "resultados": filas, "contrato_modificado": False,
                              "sustituto": {"estado": "pendiente", "motivo": "no hay fotos reales etiquetadas por sesión"},
                              "contador_clasico": {"parametros": f"ml/{params}",
                                                   "evaluacion": "ml/resultados/p2/y8_reentrenado/eval_clasico.json",
                                                   "solo_sintetico": True, "activa_reglas": False}}
    escribir(meta_path, meta)
    for nombre, carpeta in (("broca-y11n-v0-sint", "y11_original"), (mejorado, "y8_reentrenado")):
        p = ML / "modelos" / f"{nombre}.metadata.json"
        m = leer(p)
        ev = leer(OUT / carpeta / "eval_sintetico.json")
        m["evaluacion_sintetica"] = {"archivo": f"ml/resultados/p2/{carpeta}/eval_sintetico.json",
                                     "recomendada": ev["recomendacion"]["variante"],
                                     "recalibracion_val": ev["umbral_propuesto"]}
        escribir(p, m)
    tabla = ["", "## Experimento P2 · SOLO SINTÉTICOS (2026-10-03)", "",
             "Comparación medida con el contrato vigente (conteo ≥0,60). Latencia de laptop CPU; no es Android.", "",
             "| Modelo / dataset | Variante | MiB | MAE a 0,60 | ms/mosaico 1 hilo | Score val | MAE prueba calibrado |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for f in filas:
        tabla.append(f"| {f['modelo']} / {Path(f['dataset']).parts[1]} | {f['variante']} | {f['mb']} | "
                     f"{f['mae_contrato_060']} | {f['latencia_ms']['1_hilo_mediana']} | {f['score_elegido_val']} | "
                     f"{f['mae_prueba_score_calibrado']} |")
    clas = leer(OUT / "y8_reentrenado/eval_clasico.json")
    tabla += ["", f"Contador clásico recalibrado en validación difícil sintética: MAE prueba **{clas['mae_total']}**. "
              "No está calibrado con fotos reales y no activa reglas.", "",
              "El barrido elige score solo en validación. Un score distinto de 0,60 es una propuesta; "
              "el contrato congelado permanece intacto. Se conserva el modelo vigente en metadata y las variantes nuevas "
              "tienen metadata individual. Las épocas y tiempos efectivos están en cada resumen de entrenamiento.", "",
              "Los datasets son diferentes: comparar modelos solo dentro del mismo dataset. "
              "Detalle: `resultados/p2/comparacion_sintetica.json`. "
              "**Ninguno de estos errores mide desempeño en broca real o en gorgojos.**", ""]
    readme = ML / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n".join(tabla), encoding="utf-8")
    escribir(OUT / "estado.json", {"etapa": "completo", "estado": "completo", "sintetico": True})
    print(json.dumps(comparacion, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if OUT.exists():
            escribir(OUT / "error.json", {"error": str(exc), "tipo": type(exc).__name__})
        raise
