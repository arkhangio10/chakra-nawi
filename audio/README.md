# audio/ · Mensajes grabados

Los 14 audios de PLAN §7 (≤ 8 s), en quechua cusqueño y castellano, grabados por personas y validados por un segundo hablante.
Responsable: P4. Guion: `docs/GUION_AUDIOS.md`. Catálogo: **`audio/mensajes.json`** (cumple `contracts/mensajes.schema.json`).

Cada audio va en **dos formatos**: `audio/<es|quz>/<CODIGO>.opus` para la PWA y `audio/<es|quz>/<CODIGO>.mp3` para la llamada (Twilio `<Play>` no reproduce Opus). En el catálogo, `archivos` son los Opus y `archivos_llamada` los MP3.

## Estado actual (3 oct)

| Idioma | Estado | `sintetico` |
|---|---|---|
| Castellano (`es/`) | **PROVISIONAL Y SINTÉTICO**: voz TTS de Windows *Microsoft Sabina Desktop* (es-MX), generada con `tts_provisional.py`. 14 audios de 2,4 a 7,8 s; 188 KB en Opus y 416 KB en MP3 | `true` (la `nota` de cada mensaje dice la voz) |
| Quechua (`quz/`) | **Pendiente**: no hay texto ni grabación. `texto_quz` vacío | — |

**Respaldo:** mientras `texto_quz` esté vacío (o falte el archivo `quz`), la PWA y la llamada usan el castellano. La API lo hace sola, archivo por archivo, y el panel avisa "respaldo". En el demo y el video, todo audio con `sintetico: true` se rotula "sintético".

## Convertir grabaciones (notas de voz de WhatsApp)

```bash
pip install -r audio/requirements.txt            # imageio-ffmpeg trae ffmpeg (con libopus y libmp3lame)
# 1. Guardar cada nota como audio/grabaciones/<idioma>/<CODIGO>.<ext>  (p. ej. quz/R_VERDE.opus; .ogg, .m4a, .wav también)
#    audio/grabaciones/ no se sube a git: lleva la voz y el código dicho del hablante.
# 2. Convertir (recorta silencios, filtra graves, normaliza a -16 LUFS, deja 0,15 s de margen):
python audio/convertir.py --entrada audio/grabaciones --quitar-codigo --actualizar-catalogo
```

- `--quitar-codigo` corta lo dicho antes de la primera pausa de ≥ 0,6 s (el guion pide decir el código, esperar un segundo y luego el mensaje). Escuchar el resultado.
- `--umbral -35` si la grabación tiene ruido de fondo y no recorta los silencios.
- Avisa si un audio dura más de 8 s y lista los códigos que faltan.
- `--actualizar-catalogo` solo pone `duracion_s` (la mayor entre idiomas). **A mano** en `mensajes.json`: `texto_quz`, `revisado_por` (el segundo hablante) y `sintetico: false` cuando ya no quede ningún audio sintético en ese mensaje; actualizar la `nota`.
- Después: `python scripts/validar_contratos.py` y `python -m pytest api -q` (el test revisa que el catálogo valide y que existan los `.opus` y `.mp3` en castellano).

## Regenerar los provisionales en castellano (solo Windows)

```bash
python audio/tts_provisional.py            # usa la primera voz TTS "es-*" instalada; --velocidad 0 si algo pasa de 8 s
```

Sobrescribe `audio/es/*` y `audio/mensajes.json`; se niega si el catálogo ya tiene mensajes con `sintetico: false` (usar `--forzar` solo a propósito). El respaldo `mms-tts-quz` para el quechua (PLAN §11) también va con `sintetico: true` y su licencia CC-BY-NC en la `nota`.
