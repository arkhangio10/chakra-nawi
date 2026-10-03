# apps/panel/ · Panel del técnico

Una sola página estática, sin build ni frameworks (`index.html` + `panel.css` + `panel.js`). La sirve la API en **`/panel/`** (ver `api/README.md`).
Responsable: P3. Sin mapas ni gráficos; tema claro y oscuro según el sistema; se lee en laptop y en celular.

- **Lista** de `GET /casos` por prioridad: técnico urgente → técnico → amarillo → verde. Cada estado tiene color **y** forma (urgente ■, técnico ◆, amarillo ▲, verde ●) y texto. Muestra finca, fecha (hora de Lima), época, "conteo dudoso", "foto de hojas" y la última llamada.
- **Detalle:** foto (`/fotos/{archivo}`); si es de trampa, dibuja `conteo.cajas` ([xc, yc, w, h] normalizadas) encima, porque la foto subida es el marco rectificado de 1216×1216 px. Casilla para ocultar las cajas y botón "Ampliar" (tamaño real). Conteo YOLO, anterior, tendencia, contador clásico, dudoso y modelo; respuestas; causa y probabilidades (aquí sí hay cifras: es para el técnico); lo que escuchó Noor (texto y audio); y las **reglas aplicadas con su fuente y tipo** (oficial / literatura / supuesto), leídas de `GET /reglas`. Si el motor usó otro mes que el de la fecha (selector del modo técnico), lo dice.
- **Llamar a Noor** → `POST /llamadas/{caso_id}`: muestra si fue **real** (con el SID de Twilio) o **simulada**, en qué idioma salió el audio (y si fue respaldo en castellano) y el TwiML. Errores visibles: finca sin teléfono (409), falta de audio (409), error de Twilio (502).
- **Actualizar** vuelve a leer los casos. El caso abierto queda en la URL (`#caso_id`).
- Otra API: abrir con `?api=https://mi-api.example.com` (la API ya permite CORS).

Para verlo con datos: `python -m api.demo_casos` carga 5 casos de demostración con fotos sintéticas rotuladas "DEMO".
