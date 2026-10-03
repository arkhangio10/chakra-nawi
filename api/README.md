# api/ · Backend (FastAPI + SQLite + Twilio)

`POST /casos` (multipart, idempotente por `caso_id`) · `GET /casos` (por prioridad) · `POST /llamadas/{caso_id}` (`L_INTRO` + `R_*`, dos veces, ≤ 25 s).
Responsable: P3. Consume `caso.schema.json` y `mensajes.schema.json`; sirve las fichas como JSON estático.
El número de Noor y el polígono de la finca viven **solo aquí** (Ley 29733).
