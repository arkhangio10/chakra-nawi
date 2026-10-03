# api/ · Backend (FastAPI + SQLite + Twilio) y panel del técnico

| Ruta | Uso |
|---|---|
| `POST /casos` | Multipart: campo `caso` con el JSON + `foto`. Idempotente por `caso_id`; valida contra `contracts/caso.schema.json` |
| `GET /casos` | Lista por prioridad (urgente → técnico → amarillo → verde) con `foto_url` y el historial `llamadas` (fecha y si fue simulada). **Nunca** incluye teléfonos |
| `POST /llamadas/{caso_id}` | Llama a Noor: `L_INTRO` + `R_*` dos veces. Responde `simulada`, `sid`, `twiml`, `idioma_audio` y `respaldo` |
| `GET /reglas` | `rules.json` con fuente y tipo de cada regla, más `origen` (qué archivo se sirvió). Usa `packages/motor/rules.json` si existe; si no, `contracts/rules.example.json`. Se puede forzar con `CHAKRA_REGLAS` |
| `GET /panel/` | Panel del técnico (`apps/panel/`, estático). `/` y `/panel` redirigen aquí |
| `GET /fotos/{archivo}` · `/fichas/{finca_id}.json` · `/audio/...` | Estáticos (`/audio/mensajes.json` es el catálogo de audios) |
| `GET /salud` | `ok` |

Responsable: P3. El número de Noor vive **solo** en el servidor: `api/fincas_privadas.json` (no se sube a git; ver `.example`) o el secreto `CHAKRA_FINCAS_PRIVADAS_JSON`. Nunca sale por la API (Ley 29733; hay un test).

## Correr en local

```bash
pip install -r requirements.txt python-dotenv      # o: pip install -r api/requirements.txt
cp api/.env.example api/.env                       # sin credenciales de Twilio: llamadas simuladas
uvicorn api.app:app --reload --env-file api/.env
python -m api.demo_casos                           # opcional: 5 casos de DEMO con fotos sintéticas
```

Abrir **http://localhost:8000/panel/**. Tests: `python -m pytest api -q`.

**La llamada:** Twilio `<Play>` no acepta Opus, así que el TwiML apunta a `audio/<idioma>/<CODIGO>.mp3`. El idioma sale de `fincas_privadas` (`quz` por defecto); si falta ese `.mp3` (el quechua aún no está grabado), se usa el castellano y la respuesta trae `"respaldo": true` (el panel lo muestra). Si tampoco hay castellano, responde 409 y no llama. Sin `TWILIO_*`, la llamada es simulada: devuelve el TwiML que habría usado y queda en el historial como simulada.

## Desplegar

**Elegimos Render.** Se despliega desde el repositorio de GitHub con un Blueprint (`render.yaml`, sin instalar CLI), los secretos se cargan en la web y el disco persistente se declara en el mismo archivo; además Render define `RENDER_EXTERNAL_URL`, que la API usa como URL pública para Twilio. Fly.io obliga a instalar `flyctl` y crear el volumen a mano, y su ventaja (regiones en Sudamérica) no pesa en un demo.

La imagen (`Dockerfile` en la raíz) lleva la API, el panel, los contratos, las fichas, los audios y las reglas (≈ 1 MB más Python). Lo que cambia vive en el disco `/data`: `chakra.sqlite`, `uploads/` (fotos) y, si se usa, `fincas_privadas.json`.

### Opción A · Render (enlace público estable)

1. Subir el repositorio a GitHub (debe ser público por la licencia AGPL de Ultralytics).
2. En <https://dashboard.render.com>: **New → Blueprint** → elegir el repositorio. Render lee `render.yaml` y crea el servicio `chakra-nawi-api` (Docker, región Virginia, plan *starter* con disco de 1 GB en `/data`).
3. Llenar los valores que pide (`sync: false`):
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` (el número de Twilio, con Perú habilitado en *Voice → Geo permissions*). Si se dejan vacíos, las llamadas quedan simuladas.
   - `CHAKRA_FINCAS_PRIVADAS_JSON`: `{"LC-001": {"telefono": "+519XXXXXXXX", "idioma": "quz"}}` (una línea).
4. **Apply**. Al terminar el build, comprobar:
   ```bash
   curl https://chakra-nawi-api.onrender.com/salud            # ok
   curl https://chakra-nawi-api.onrender.com/audio/es/L_INTRO.mp3 -o /dev/null -w "%{http_code} %{content_type}\n"   # 200 audio/mpeg
   ```
   y abrir `https://chakra-nawi-api.onrender.com/panel/` (la URL exacta aparece en el panel de Render).
5. Poner esa URL como API en la PWA de campo (P1) y cargar un caso: `python -m api.demo_casos --api https://chakra-nawi-api.onrender.com` (solo si se quiere ver datos de demo; no usar en el video como datos reales).
6. Probar la llamada desde el panel con el botón **Llamar a Noor**: debe decir "Llamada REAL enviada a Twilio" y sonar el teléfono.

Costo: el plan *starter* cobra unos 7 USD al mes, prorrateado por segundo; borrar el servicio al terminar el hackathon. **Plan B gratis:** en `render.yaml` cambiar `plan: free` y borrar el bloque `disk`; funciona igual, pero la base y las fotos se pierden en cada despliegue o reinicio, y el servicio se duerme tras 15 min sin uso (el primer pedido tarda ~1 min).

### Opción B · Túnel desde la laptop (si no hay tiempo de desplegar)

Twilio necesita una URL pública con HTTPS para descargar los `.mp3`; un túnel la da en un minuto, sin cuenta:

```bash
winget install --id Cloudflare.cloudflared          # una vez (macOS: brew install cloudflared)
cloudflared tunnel --url http://localhost:8000      # imprime https://<algo>.trycloudflare.com
```

1. Copiar esa URL en `PUBLIC_BASE_URL` de `api/.env` y **reiniciar** uvicorn (la API la lee al arrancar):
   `uvicorn api.app:app --port 8000 --env-file api/.env`
2. Panel: `https://<algo>.trycloudflare.com/panel/`. La PWA de campo apunta a esa misma URL.
3. Limitaciones: la URL cambia cada vez que se reinicia `cloudflared`, la laptop debe quedar encendida y con internet, y no hay garantía de servicio. Alternativa equivalente: `ngrok http 8000` (requiere cuenta).

### Docker en local (para probar la imagen)

```bash
docker build -t chakra-nawi-api .
docker run --rm -p 8000:8000 -v chakra-datos:/data -e TWILIO_ACCOUNT_SID=... -e TWILIO_AUTH_TOKEN=... -e TWILIO_FROM=... \
  -e PUBLIC_BASE_URL=https://<algo>.trycloudflare.com -e CHAKRA_FINCAS_PRIVADAS_JSON='{"LC-001":{"telefono":"+519XXXXXXXX","idioma":"quz"}}' \
  chakra-nawi-api
```

No pasar `--env-file api/.env` si ese archivo define `CHAKRA_DB`/`CHAKRA_FOTOS` con rutas locales: sacarían los datos del volumen `/data`.
