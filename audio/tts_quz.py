"""Audios SINTÉTICOS en quechua cusqueño con Meta MMS-TTS (facebook/mms-tts-quz) → audio/quz/*.opus + *.mp3.

No hay hablante de quechua para la entrega del hackathon. Este es el respaldo de PLAN §11:
- Textos: texto_quz de contracts/mensajes.example.json. BORRADOR del equipo, sin validar por un hablante nativo.
- Voz: MMS-TTS (Meta, CC-BY-NC 4.0: solo uso no comercial). Modelo VITS de 36 M de parámetros, 16 kHz.
- En audio/mensajes.json se llena texto_quz y se deja "sintetico": true y "revisado_por" vacío.
Cuando lleguen grabaciones humanas, se reemplazan con audio/convertir.py y este script ya no se usa.

MMS no lee puntuación, así que cada frase se sintetiza por separado y se unen con pausas.

Uso (con torch + transformers; en este repo: ml/.venv):
  ml/.venv/Scripts/python audio/tts_quz.py [--velocidad 0.9]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convertir  # noqa: E402

RAIZ = convertir.RAIZ
CATALOGO = RAIZ / "audio/mensajes.json"
EJEMPLO = RAIZ / "contracts/mensajes.example.json"
MODELO = "facebook/mms-tts-quz"
PAUSA_FRASE_S, PAUSA_COMA_S = 0.4, 0.15
NOTA = ("SINTÉTICO: quechua cusqueño con Meta MMS-TTS (facebook/mms-tts-quz, CC-BY-NC 4.0, uso no comercial), "
        "generado con audio/tts_quz.py. Texto en quechua: borrador del equipo, SIN VALIDAR por un hablante nativo. "
        "Castellano: voz TTS de Windows (provisional). Reemplazar ambos por grabaciones humanas.")


def trozos(texto: str) -> list[tuple[str, float]]:
    """Parte el texto en frases y comas; devuelve (texto normalizado para MMS, pausa que va después)."""
    salida = []
    for frase in re.split(r"(?<=[.;?!])\s+", texto.strip()):
        partes = [p for p in frase.split(",") if p.strip()]
        for i, p in enumerate(partes):
            salida.append((p, PAUSA_COMA_S if i < len(partes) - 1 else PAUSA_FRASE_S))
    return salida


def normalizar(texto: str, vocab: set[str]) -> str:
    """Minúsculas, sin tildes (salvo ñ) y solo con caracteres que el tokenizador de MMS conoce."""
    t = texto.lower().replace("ñ", "\0")
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").replace("\0", "ñ")
    t = re.sub(r"[¿?¡!.,;:]", " ", t)
    fuera = {c for c in t if c not in vocab and c != " "}
    if fuera:
        print(f"  aviso: MMS no conoce {sorted(fuera)} en {texto!r}; se quitan")
    return re.sub(r"\s+", " ", "".join(c for c in t if c in vocab or c == " ")).strip()


def sintetizar(textos: dict[str, str], carpeta: Path, velocidad: float) -> None:
    import numpy as np
    import torch
    from transformers import VitsModel, VitsTokenizer

    tok = VitsTokenizer.from_pretrained(MODELO)
    modelo = VitsModel.from_pretrained(MODELO).eval()
    modelo.speaking_rate = velocidad
    sr = modelo.config.sampling_rate
    vocab = set(tok.get_vocab())
    for codigo, texto in textos.items():
        torch.manual_seed(7)  # misma voz en cada corrida
        piezas = []
        for parte, pausa in trozos(texto):
            with torch.no_grad():
                onda = modelo(**tok(normalizar(parte, vocab), return_tensors="pt")).waveform[0].numpy()
            piezas += [onda, np.zeros(int(pausa * sr), dtype=onda.dtype)]
        audio = np.concatenate(piezas[:-1])
        pcm = (np.clip(audio / max(1e-6, np.abs(audio).max()) * 0.9, -1, 1) * 32767).astype("<i2")
        with wave.open(str(carpeta / f"{codigo}.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
            w.writeframes(pcm.tobytes())


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--velocidad", type=float, default=0.9, help="speaking_rate de MMS (por defecto 0,9: más sereno)")
    a = ap.parse_args()

    ejemplo = json.loads(EJEMPLO.read_text(encoding="utf-8"))["mensajes"]
    textos = {c: m["texto_quz"] for c, m in ejemplo.items()}
    if vacios := [c for c, t in textos.items() if not t.strip()]:
        sys.exit(f"Falta texto_quz en contracts/mensajes.example.json: {', '.join(vacios)}")

    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    if humanos := [c for c, m in catalogo["mensajes"].items() if m.get("revisado_por")]:
        sys.exit(f"Ya hay quechua validado por una persona ({', '.join(humanos)}); no lo piso.")

    with tempfile.TemporaryDirectory() as tmp:
        sintetizar(textos, Path(tmp), a.velocidad)
        resultados = {r["codigo"]: r for r in convertir.convertir_carpeta(Path(tmp), "quz")}
    convertir.imprimir(list(resultados.values()))

    for codigo, m in catalogo["mensajes"].items():
        if codigo not in resultados:
            sys.exit(f"Falta el audio quz de {codigo}")
        m["texto_quz"] = textos[codigo]
        m["sintetico"] = True
        m["duracion_s"] = round(max(m.get("duracion_s", 0), resultados[codigo]["duracion_s"]), 2)
        m["nota"] = NOTA
    catalogo["version"] = catalogo["version"].split(".")[0] + ".tts-quz"
    from tts_provisional import validar
    if errores := validar(catalogo):
        print("mensajes.json NO valida:\n  " + "\n  ".join(errores) + "\nSi algo pasa de 8 s, prueba --velocidad 1.0")
        return 1
    with open(CATALOGO, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n")
    print(f"Escrito {CATALOGO.relative_to(RAIZ)} (14 mensajes con texto_quz, sintetico: true)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
