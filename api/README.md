# api/ · Backend (FastAPI + SQLite + Twilio)

`POST /casos` (multipart: campo `caso` con el JSON + `foto`; idempotente por `caso_id`, valida contra `contracts/caso.schema.json`) · `GET /casos` (por prioridad) · `POST /llamadas/{caso_id}` · `GET /fotos/{archivo}` · `/fichas/{finca_id}.json` · `/audio/...`
Responsable: P3. El número de Noor vive **solo** en `api/fincas_privadas.json` (no se sube a git; ver `.example`). Nunca sale por la API (Ley 29733).
Correr: `uvicorn api.app:app --reload --env-file api/.env` · Tests: `python -m pytest api -q`.
Sin credenciales de Twilio, `/llamadas` responde `"simulada": true` con el TwiML que habría usado. **Twilio `<Play>` no acepta Opus**: la llamada usa `audio/<idioma>/<CODIGO>.mp3`.
