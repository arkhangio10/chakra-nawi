"""Audios PROVISIONALES en castellano con la voz TTS de Windows → audio/es/*.opus + *.mp3 y audio/mensajes.json.

Son SINTÉTICOS: en mensajes.json van con "sintetico": true y una nota con la voz usada. Sirven para que la PWA y la
llamada funcionen antes de que lleguen las grabaciones; se reemplazan con audio/convertir.py (ver audio/README.md).
Los textos salen de contracts/mensajes.example.json (texto_es), que sigue el guion de docs/GUION_AUDIOS.md.

Uso (solo Windows):  python audio/tts_provisional.py [--velocidad -1] [--forzar]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convertir  # noqa: E402

RAIZ = convertir.RAIZ
CATALOGO = RAIZ / "audio/mensajes.json"
EJEMPLO = RAIZ / "contracts/mensajes.example.json"


def sintetizar(textos: dict[str, str], carpeta: Path, velocidad: int) -> str:
    """Escribe carpeta/CODIGO.wav con PowerShell + System.Speech. Devuelve 'Nombre de la voz|cultura'."""
    entrada = carpeta / "textos.json"
    entrada.write_text(json.dumps(textos, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RAIZ / "audio/tts_windows.ps1"),
         "-Textos", str(entrada), "-Salida", str(carpeta), "-Velocidad", str(velocidad)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"La voz TTS de Windows falló (código {r.returncode}):\n{r.stderr.strip()}")
    return next(l.split("=", 1)[1] for l in r.stdout.splitlines() if l.startswith("VOZ="))


def validar(catalogo: dict) -> list[str]:
    from jsonschema import Draft202012Validator
    esquema = json.loads((RAIZ / "contracts/mensajes.schema.json").read_text(encoding="utf-8"))
    return [f"/{'/'.join(map(str, e.path))}: {e.message}" for e in Draft202012Validator(esquema).iter_errors(catalogo)]


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--velocidad", type=int, default=-1, help="-10 a 10 (por defecto -1: un poco más lento, sereno)")
    ap.add_argument("--forzar", action="store_true", help="sobrescribir aunque mensajes.json ya tenga audios grabados")
    a = ap.parse_args()

    if CATALOGO.exists() and not a.forzar:
        grabados = [c for c, m in json.loads(CATALOGO.read_text(encoding="utf-8"))["mensajes"].items()
                    if not m.get("sintetico", True)]
        if grabados:
            print(f"audio/mensajes.json ya tiene audios grabados por personas ({', '.join(grabados)}). "
                  "No los piso: usa --forzar si de verdad quieres volver a los sintéticos.")
            return 1

    ejemplo = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    textos = {c: m["texto_es"] for c, m in ejemplo["mensajes"].items()}
    with tempfile.TemporaryDirectory() as tmp:
        voz = sintetizar(textos, Path(tmp), a.velocidad)
        nombre, cultura = voz.split("|")
        print(f"Voz TTS: {nombre} ({cultura}) · velocidad {a.velocidad}")
        resultados = {r["codigo"]: r for r in convertir.convertir_carpeta(Path(tmp), "es")}
    convertir.imprimir(list(resultados.values()))

    nota = (f"PROVISIONAL Y SINTÉTICO: castellano con la voz TTS de Windows ({nombre}, {cultura}), generado con "
            "audio/tts_provisional.py. Reemplazar por la grabación del equipo. Quechua pendiente (texto_quz vacío): "
            "la app y la llamada usan el castellano como respaldo.")
    catalogo = {"version": f"{date.today().isoformat()}.tts", "mensajes": {}}
    for codigo, m in ejemplo["mensajes"].items():
        if codigo not in resultados:
            sys.exit(f"Falta el audio de {codigo}")
        catalogo["mensajes"][codigo] = {
            "uso": m["uso"],
            "archivos": {"es": f"audio/es/{codigo}.opus", "quz": f"audio/quz/{codigo}.opus"},
            "archivos_llamada": {"es": f"audio/es/{codigo}.mp3", "quz": f"audio/quz/{codigo}.mp3"},
            "texto_es": m["texto_es"],
            "texto_quz": "",
            "revisado_por": "",
            "sintetico": True,
            "duracion_s": resultados[codigo]["duracion_s"],
            "nota": nota,
        }
    errores = validar(catalogo)
    if errores:
        print("mensajes.json NO valida contra contracts/mensajes.schema.json:\n  " + "\n  ".join(errores))
        print("Si algún audio dura más de 8 s, prueba con --velocidad 0.")
        return 1
    with open(CATALOGO, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n")
    print(f"Escrito {CATALOGO.relative_to(RAIZ)} (14 mensajes, sintetico: true)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
