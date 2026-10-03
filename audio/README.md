# audio/ · Mensajes grabados

Los 14 audios de PLAN §7 (≤ 8 s), en quechua cusqueño y castellano, grabados por personas y validados por un segundo hablante.
Responsable: P4. Produce `mensajes.json` según `contracts/mensajes.schema.json` (con `revisado_por`). El respaldo `mms-tts-quz` va con `sintetico: true`.
Cada audio va en **dos formatos**: `audio/<es|quz>/<CODIGO>.opus` para la PWA y `audio/<es|quz>/<CODIGO>.mp3` para la llamada (Twilio `<Play>` no reproduce Opus). Ver `docs/GUION_AUDIOS.md`.
