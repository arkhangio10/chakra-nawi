"""Convierte grabaciones a los dos formatos de la app (PLAN §7, docs/GUION_AUDIOS.md).

Entrada: una carpeta con un archivo por mensaje, llamado CODIGO.ext (p. ej. R_VERDE.ogg), en cualquier formato que
lea ffmpeg: notas de voz de WhatsApp (.opus/.ogg), .m4a, .wav, .mp3, .aac, .amr, .webm, .flac.
Salida:  audio/<idioma>/<CODIGO>.opus   para la PWA (Opus 24 kb/s, mono)
         audio/<idioma>/<CODIGO>.mp3    para la llamada (Twilio <Play> no reproduce Opus; 22,05 kHz, mono, 48 kb/s)

Pasos: (opcional) quitar el código dicho al inicio → filtro paso alto (80 Hz) → recortar los silencios del inicio y del
final → normalizar el volumen (EBU R128 en dos pasadas, -16 LUFS, pico -1,5 dBTP) → 0,15 s de margen a cada lado.

Uso:
  python audio/convertir.py --entrada grabaciones/quz --idioma quz
  python audio/convertir.py --entrada grabaciones              (con subcarpetas es/ y quz/)
  python audio/convertir.py --entrada grabaciones/quz --idioma quz --quitar-codigo --actualizar-catalogo

--quitar-codigo: el guion pide decir el código antes del mensaje ("R_VERDE", pausa, mensaje). Corta todo lo anterior
a la primera pausa de ≥ 0,6 s. Escucha el resultado: si el hablante no hizo la pausa, recorta a mano.
Requiere: pip install -r audio/requirements.txt  (imageio-ffmpeg trae el binario de ffmpeg; no hace falta instalarlo).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AUDIO = RAIZ / "audio"
IDIOMAS = ("es", "quz")
EXTENSIONES = {".opus", ".ogg", ".oga", ".m4a", ".mp4", ".aac", ".wav", ".mp3", ".amr", ".webm", ".flac"}
LUFS, PICO, LRA = -16, -1.5, 11
MAX_S = 8.0  # PLAN §7 y mensajes.schema.json (duracion_s ≤ 8)
MARGEN_S = 0.15


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.exit("Falta imageio-ffmpeg: pip install -r audio/requirements.txt")
    return imageio_ffmpeg.get_ffmpeg_exe()


def _correr(*args: str) -> str:
    """Corre ffmpeg y devuelve su stderr (ahí escribe las mediciones)."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falló:\n{r.stderr[-1500:]}")
    return r.stderr


def codigos() -> list[str]:
    """Los 14 códigos de PLAN §7, leídos del contrato."""
    esquema = json.loads((RAIZ / "contracts/mensajes.schema.json").read_text(encoding="utf-8"))
    return esquema["properties"]["mensajes"]["required"]


def duracion(ruta: Path) -> float | None:
    """Duración de cualquier archivo de audio, leída de la cabecera con ffmpeg."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(ruta)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else None


def inicio_tras_codigo(entrada: Path, umbral_db: float, pausa_s: float = 0.6) -> float | None:
    """Fin de la primera pausa que viene después de haber hablado (el código dicho al inicio)."""
    err = _correr("-i", str(entrada), "-af", f"silencedetect=noise={umbral_db}dB:d={pausa_s}", "-f", "null", "-")
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    fines = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    for ini, fin in zip(inicios, fines):
        if ini > 0.05:  # la pausa que empieza en 0 es el silencio inicial, no la que sigue al código
            return fin
    return None


def _filtros(inicio: float | None, umbral_db: float) -> list[str]:
    corte = f"silenceremove=start_periods=1:start_threshold={umbral_db}dB:start_silence=0.05"
    f = [f"atrim=start={inicio:.3f}", "asetpts=PTS-STARTPTS"] if inicio else []
    # recorte del final: invertir, recortar el "inicio" y volver a invertir
    return f + ["aformat=channel_layouts=mono", "highpass=f=80", corte, "areverse", corte, "areverse"]


def procesar(entrada: Path, codigo: str, idioma: str, salida: Path = AUDIO,
             quitar_codigo: bool = False, umbral_db: float = -40) -> dict:
    """Una grabación → <salida>/<idioma>/<codigo>.opus y .mp3. Devuelve duración y tamaños."""
    inicio = inicio_tras_codigo(entrada, umbral_db) if quitar_codigo else None
    avisos = []
    if quitar_codigo and inicio is None:
        avisos.append("no encontré la pausa tras el código: no se cortó nada")
    previos = _filtros(inicio, umbral_db)

    # Pasada 1: medir la sonoridad del audio ya recortado
    err = _correr("-i", str(entrada), "-af",
                  ",".join(previos + [f"loudnorm=I={LUFS}:TP={PICO}:LRA={LRA}:print_format=json"]), "-f", "null", "-")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err)
    if not m:
        raise RuntimeError(f"{entrada.name}: no pude medir la sonoridad")
    med = json.loads(m[0])
    if "inf" in med["input_i"]:
        raise RuntimeError(f"{entrada.name}: el audio quedó vacío tras recortar silencios (¿umbral muy alto? usa --umbral)")

    # Pasada 2: normalizar con lo medido (lineal) + margen, a un WAV intermedio
    norma = (f"loudnorm=I={LUFS}:TP={PICO}:LRA={LRA}:measured_I={med['input_i']}:measured_TP={med['input_tp']}"
             f":measured_LRA={med['input_lra']}:measured_thresh={med['input_thresh']}"
             f":offset={med['target_offset']}:linear=true")
    destino = salida / idioma
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / f"{codigo}.wav"
        margen_ms = int(MARGEN_S * 1000)
        _correr("-i", str(entrada), "-af",
                ",".join(previos + [norma, "aresample=48000", f"adelay={margen_ms}:all=1", f"apad=pad_dur={MARGEN_S}"]),
                "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav))
        with wave.open(str(wav)) as w:
            dur = w.getnframes() / w.getframerate()
        opus, mp3 = destino / f"{codigo}.opus", destino / f"{codigo}.mp3"
        _correr("-i", str(wav), "-map_metadata", "-1", "-ac", "1",
                "-c:a", "libopus", "-b:a", "24k", "-application", "voip", str(opus))
        _correr("-i", str(wav), "-map_metadata", "-1", "-ac", "1", "-ar", "22050",
                "-c:a", "libmp3lame", "-b:a", "48k", "-id3v2_version", "0", str(mp3))
    if dur > MAX_S:
        avisos.append(f"dura {dur:.1f} s (> {MAX_S:.0f} s): pedir una versión más corta")
    return {"codigo": codigo, "idioma": idioma, "duracion_s": round(dur, 2), "lufs_entrada": med["input_i"],
            "opus_bytes": opus.stat().st_size, "mp3_bytes": mp3.stat().st_size, "avisos": avisos}


def buscar_grabaciones(carpeta: Path) -> tuple[dict[str, Path], list[str]]:
    """CODIGO → archivo. Acepta mayúsculas o minúsculas y guiones; ignora lo que no es uno de los 14 códigos."""
    validos, encontrados, avisos = set(codigos()), {}, []
    for p in sorted(carpeta.iterdir(), key=lambda p: p.stat().st_mtime):
        if not p.is_file() or p.suffix.lower() not in EXTENSIONES:
            continue
        codigo = re.sub(r"[\s-]+", "_", p.stem.strip()).upper()
        if codigo not in validos:
            avisos.append(f"se omite {p.name}: el nombre no es uno de los 14 códigos")
            continue
        if codigo in encontrados:
            avisos.append(f"{codigo}: hay varias grabaciones; uso la más reciente ({p.name})")
        encontrados[codigo] = p  # orden por fecha: gana la más reciente
    return encontrados, avisos


def convertir_carpeta(carpeta: Path, idioma: str, salida: Path = AUDIO,
                      quitar_codigo: bool = False, umbral_db: float = -40) -> list[dict]:
    grabaciones, avisos = buscar_grabaciones(carpeta)
    for a in avisos:
        print(f"  aviso: {a}")
    resultados = []
    for codigo, ruta in sorted(grabaciones.items()):
        try:
            resultados.append(procesar(ruta, codigo, idioma, salida, quitar_codigo, umbral_db))
        except RuntimeError as e:
            print(f"  ERROR {codigo}: {e}")
    faltan = sorted(set(codigos()) - set(grabaciones))
    if faltan:
        print(f"  faltan en {idioma} ({len(faltan)}): {', '.join(faltan)}")
    return resultados


def actualizar_catalogo(ruta: Path, salida: Path = AUDIO) -> None:
    """Pone en mensajes.json la duración (la mayor entre idiomas) de cada audio existente. El resto se llena a mano."""
    cat = json.loads(ruta.read_text(encoding="utf-8"))
    for codigo, m in cat["mensajes"].items():
        durs = [d for idi in IDIOMAS if (salida / idi / f"{codigo}.opus").exists()
                and (d := duracion(salida / idi / f"{codigo}.opus"))]
        if durs:
            m["duracion_s"] = round(max(durs), 2)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(cat, ensure_ascii=False, indent=2) + "\n")
    print(f"Catálogo actualizado: {ruta}. Llena a mano texto_quz, revisado_por y sintetico; "
          "luego corre python scripts/validar_contratos.py y python -m pytest api -q")


def imprimir(resultados: list[dict]) -> None:
    print(f"{'código':20} {'idioma':6} {'dur. s':>6} {'opus KB':>8} {'mp3 KB':>7}  avisos")
    for r in resultados:
        print(f"{r['codigo']:20} {r['idioma']:6} {r['duracion_s']:6.2f} {r['opus_bytes'] / 1024:8.1f} "
              f"{r['mp3_bytes'] / 1024:7.1f}  {'; '.join(r['avisos'])}")
    if resultados:
        print(f"{'TOTAL':20} {'':6} {'':6} {sum(r['opus_bytes'] for r in resultados) / 1024:8.1f} "
              f"{sum(r['mp3_bytes'] for r in resultados) / 1024:7.1f}")


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", type=Path, required=True, help="carpeta con CODIGO.ext (o con subcarpetas es/ y quz/)")
    ap.add_argument("--idioma", choices=IDIOMAS, help="si se omite, se leen las subcarpetas es/ y quz/ de --entrada")
    ap.add_argument("--salida", type=Path, default=AUDIO, help="raíz de salida (por defecto audio/)")
    ap.add_argument("--quitar-codigo", action="store_true", help="cortar el código dicho antes de la primera pausa")
    ap.add_argument("--umbral", type=float, default=-40, help="umbral de silencio en dB (por defecto -40; "
                    "súbelo a -35 si la grabación tiene ruido de fondo)")
    ap.add_argument("--actualizar-catalogo", nargs="?", const=AUDIO / "mensajes.json", type=Path, metavar="RUTA",
                    help="poner duracion_s en mensajes.json (por defecto audio/mensajes.json)")
    a = ap.parse_args()

    tareas = [(a.entrada, a.idioma)] if a.idioma else [(a.entrada / i, i) for i in IDIOMAS if (a.entrada / i).is_dir()]
    if not tareas:
        print(f"No hay subcarpetas es/ ni quz/ en {a.entrada}; usa --idioma")
        return 1
    resultados = []
    for carpeta, idioma in tareas:
        print(f"[{idioma}] {carpeta}")
        resultados += convertir_carpeta(carpeta, idioma, a.salida, a.quitar_codigo, a.umbral)
    imprimir(resultados)
    if a.actualizar_catalogo and a.actualizar_catalogo.exists():
        actualizar_catalogo(a.actualizar_catalogo, a.salida)
    return 1 if any(r["avisos"] for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
