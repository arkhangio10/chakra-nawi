# Lo que sigue (fuera del MVP)

Todo lo que **no pasa la brújula anti-desvío** (PLAN §1) se anota aquí y **no se construye** durante el hackathon. Sirve para el pitch ("lo que sigue") y para no perder ideas.

Formato para agregar: `- [fecha · quién] idea — por qué quedó fuera (qué pregunta de la brújula falló)`.

## Fuera desde el plan (PLAN §3)

- NDVI de Sentinel-2 en el motor — bajo sombra no es defendible y hay 79–90% de nubes de nov a mar (PLAN §12).
- Extractor de noticias con LLM — se reemplaza por `data/alertas_activas.json` hecho a mano. Sin LLM en el sistema.
- Backtest con datos de MIDAGRI — evita la validación circular; no cabe en 24 h.
- Leaflet y mapas — el panel es una lista por prioridad, sin mapas ni gráficos.
- Scheduler y horarios de llamada — en el demo la llamada se dispara con un botón.
- Background Sync — la cola se reintenta con el evento `online` y con un botón.
- ETag — las fichas se sirven como JSON estático.
- Modo de registro de fincas en la app — las 5 fincas vienen precargadas.
- Precio de referencia del café.
- Clasificador de hojas (roya por imagen) — en lluvias la foto de hojas es solo evidencia para el técnico.
- Foto de frutos (dataset de Chaullay, TESLA-UNSAAC) — contacto para el futuro.
- Suelo y altitud como evidencias del motor.
- Varias regiones o cultivos.

## Fuera desde la arquitectura

- Número de teléfono local para la llamada (agregador peruano o línea de la cooperativa) — en el demo se usa Twilio (ARCHITECTURE §7).

## Ideas nuevas durante el hackathon

- [3 oct · equipo] Audios en quechua cusqueño grabados por una persona y validados por un segundo hablante — no se consiguió hablante a tiempo; la entrega va con quechua **sintético** (Meta MMS-TTS) sobre textos traducidos por el equipo y sin validar. Mínimo útil antes: que un hablante solo *escuche* los 14 audios y marque cuáles se entienden (`revisado_por`). El guion (`docs/GUION_AUDIOS.md`) y el soporte de `audio/quz/` en la app y la API ya están listos. Contactos posibles: UNSAAC (EIB, Lingüística), Academia Mayor de la Lengua Quechua, Centro Bartolomé de las Casas, Registro de Intérpretes de Lenguas Indígenas (Ministerio de Cultura).
