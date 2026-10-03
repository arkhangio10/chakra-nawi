# Chakra Ñawi · Arquitectura

Versión 0.2 · 3 oct 2026 · Alineada con `PLAN.md` v1.0, que manda si hay contradicción.

> Triaje offline que prioriza las visitas del técnico. Un smartphone, sin internet, convierte la foto de la trampa de broca y una pregunta con dibujos en un semáforo con voz grabada en quechua. Los casos que necesitan una persona pasan al técnico, que llama a Noor a su teléfono básico.

---

## 1. Principios

| # | Principio | Consecuencia técnica |
|---|---|---|
| P1 | El triaje funciona sin internet | Modelo, motor, audios y ficha viven en el teléfono. La red solo se usa para sincronizar y llamar. |
| P2 | Noor no lee; Noor escucha | Semáforo + dibujo + voz humana. **Cero cifras** en sus pantallas (hay un test automático). |
| P3 | La IA no inventa | Lista cerrada de causas y de mensajes. Ningún LLM en el sistema. |
| P4 | Si no está segura, lo dice | Estado "técnico" explícito, con dos variantes: duda y urgente. |
| P5 | Small AI | Modelo < 10 MB. Ficha ~5 KB. La nube prepara datos; no razona. |
| P6 | Contratos primero | `contracts/` se congela en H1. |

---

## 2. Vista general

```
NUBE (preparación)                        TELÉFONO DE CAMPO (offline)                 PERSONAS
┌───────────────────────────────┐ ficha  ┌──────────────────────────────────┐
│ pipeline/ficha                │ 5 KB   │ 1. Foto (cámara nativa)          │
│  CHIRPS v3 (lluvia)           │ ─────► │    tarjeta A5 · 4 esquinas       │
│  NASA POWER (temperatura)     │        │    → calidad → YOLO por mosaicos │
│  alertas_activas.json (manual)│        │ 2. Pregunta con dibujos          │
└───────────────────────────────┘        │ 3. Motor por temporada → semáforo│──► 🔊 Noor en la chacra
                                         │    + audio grabado               │
                                         └────────────────┬─────────────────┘
                                                          │ caso (cuando hay señal)
                     ┌──────── api/ (FastAPI + SQLite) ◄──┘
                     │ POST /casos · GET /casos · POST /llamadas
                     ▼                                   │
             apps/panel (1 página)  ── botón "llamar" ───┴──► Twilio <Play> ──► 📞 teléfono básico de Noor
```

---

## 3. Componentes

### 3.1 `apps/campo` · PWA de campo

| Aspecto | Decisión |
|---|---|
| Stack | Vite + React + TypeScript · `vite-plugin-pwa` (Workbox) · Dexie (IndexedDB) |
| Pantallas | Tres, sin menú: foto → pregunta → resultado. Un selector de fecha **oculto**, en modo técnico, para el demo de las dos épocas. |
| Cámara | `<input type="file" accept="image/*" capture="environment">`: foto nativa a resolución completa. Antes de abrirla suena `G_FOTO_TRAMPA` o `G_FOTO_HOJAS`. |
| Tarjeta | A5 plastificada con 4 esquinas negras. Lado A: marco de 10×10 cm para lo capturado en la trampa. Lado B: 20 círculos para los granos. |
| Control de calidad | Detección de las 4 esquinas (escala y recorte) + brillo + nitidez (varianza del Laplaciano). Máximo 2 reintentos con `G_OTRA_VEZ`; si sigue fallando, el caso queda como `conteo_dudoso`. |
| Inferencia | `onnxruntime-web` WASM, con el `.wasm` servido desde el propio dominio y los headers COOP/COEP para tener hilos. La zona recortada se divide en mosaicos de 640 px. Las cajas aparecen sobre cada broca a medida que se procesa cada mosaico, mientras suena `G_ESPERA`. Meta ≤ 10 s; aceptable ≤ 15 s. |
| Precache | Subir `maximumFileSizeToCacheInBytes`: el límite por defecto de 2 MiB excluye el modelo y el WASM. Llamar a `navigator.storage.persist()`. |
| Offline | Cola en IndexedDB con `caso_id` UUID (envío idempotente). Se reintenta con el evento `online` y con un botón. Sin Background Sync. |
| Fincas | Precargadas (5 de ejemplo). No hay modo de registro en la app. |

### 3.2 `ml/` · Contador de broca

| Aspecto | Decisión |
|---|---|
| Modelo | YOLOv8n o YOLO11n (no YOLO26: su salida es distinta), una sola clase |
| Datos | Fotos propias de escarabajos oscuros pequeños (gorgojos) sobre la tarjeta, contados a mano, + montajes sintéticos. Yellow Sticky Traps (CC0) solo para probar el pipeline. |
| Prueba con broca real | 3 fotos completas de CATIE (con CIRAD), solo si dan permiso |
| Exportación | ONNX (comparar int8 y fp32; quedarse con el más rápido de los que tengan precisión aceptable). Meta < 10 MB. |
| Métrica | Error absoluto medio del conteo por densidad (< 50, 50–300, > 300). **El sustituto y la broca se reportan por separado.** |
| Verificación cruzada | Contador clásico (umbral + componentes conexas). Primero se mide cuánto difiere del YOLO; la regla de derivar al técnico solo se activa si se calibra. |
| Licencia | Ultralytics AGPL-3.0 → repositorio público |

### 3.3 `packages/motor` · Motor de triaje

TypeScript. Los mismos archivos los usan la PWA y los tests.

- **Clases:** `sin_problema`, `broca`, `roya`, `clima_floracion`, `plantas_viejas`, `otra`.
- **Evidencias y pesos por época:** ver `PLAN.md` §5.1. Los pesos viven en `config.json → temporadas[mes]`, que multiplica el log-LR de cada evidencia. Nunca se pone una causa en cero.
- **Cálculo:** `score(c) = log prior(c | alertas) + Σ w_mes(e)·log LR(e|c)`, con **tope de LR combinado ≤ 10 por causa**, y luego softmax.
- **Reglas:** `rules.json`. Cada regla lleva `fuente` y `tipo` (`oficial` / `literatura` / `supuesto`).
- **Pregunta adaptativa:** la segunda pregunta aparece solo si alguna de sus respuestas puede cambiar el estado.
- **Decisión:** ver `PLAN.md` §5.2. Granos 3+ en etapa de fruto atacable → `tecnico_urgente`. Un 0 nunca da verde por sí solo.
- **Salida:** `{estado, causa, probabilidades, reglas[], mensaje}`. Las probabilidades se guardan para el técnico y **nunca se muestran a Noor**.

### 3.4 `pipeline/ficha` · Ficha de finca (Python)

| Paso | Fuente | Cálculo |
|---|---|---|
| Lluvia | CHIRPS v3, COG mensuales (`rasterio` + `/vsicurl/`, leyendo solo el recorte) | Anomalía de lluvia de sep–nov de la campaña anterior frente a la climatología 1991–2020, por falta o por exceso. Días con lluvia ≥ 1 mm de nov–abr (con datos diarios si están disponibles; si no, una aproximación mensual declarada). Para el motor: anomalía de esos días frente a 1991–2020 con NASA POWER `PRECTOTCORR` (temporada y normal de la misma serie). |
| Temperatura | NASA POWER, API diaria por punto (`T2M`, `T2M_MAX`, `T2M_MIN`) | Corrección por altitud (−6,5 °C/km desde la cota de la celda). Días en el rango de germinación de la roya (17–25 °C) y su anomalía frente a la misma ventana en 1991–2020. Calor en floración. |
| Alertas | `data/alertas_activas.json` (manual) | Se copian las alertas vigentes de la provincia |

Comando: `python -m pipeline.ficha --fincas data/fincas.geojson --out fichas/`, para 5 fincas de ejemplo.

### 3.5 `api/` · Backend (FastAPI + SQLite)

| Endpoint | Uso |
|---|---|
| `POST /casos` | Caso + foto (multipart). Idempotente por `caso_id`. |
| `GET /casos` | Lista ordenada por prioridad para el panel |
| `POST /llamadas/{caso_id}` | Llama a Noor con Twilio: `L_INTRO` + el audio `R_*`, repetido dos veces, sin pedir teclas |
| Estáticos | Las fichas se sirven como archivos JSON |

Privacidad: el número de Noor y el polígono de la finca existen **solo en el servidor** (Ley 29733). La foto se recorta a la tarjeta. La llamada no dice nada sensible.

### 3.6 `apps/panel` · Panel del técnico (1 página)

Lista por prioridad (urgente → técnico → amarillo → verde). Para cada caso: foto con cajas, respuestas, causa y probabilidades, y **las reglas que se aplicaron con su fuente y tipo**. Botón "llamar a Noor". Sin mapas ni gráficos.

### 3.7 `audio/`

14 mensajes (ver `PLAN.md` §7), grabados por personas, en Opus. `contracts/mensajes.json` guarda para cada uno: código, archivo, texto en castellano, texto en quechua y `revisado_por`. El respaldo `mms-tts-quz` se rotula como sintético (licencia CC-BY-NC).

---

## 4. Contratos (se congelan en H1)

**`ficha.json`**

```json
{
  "version": "2026-27.1",
  "finca_id": "LC-017",
  "ejemplo": true,
  "altitud_m": 1450,
  "generado": "2026-10-03",
  "clima": {
    "lluvia_floracion_anom_pct": -38,
    "dias_lluvia_nov_abr": 112,
    "dias_lluvia_nov_abr_normal": 106.2,
    "dias_lluvia_nov_abr_anom": 6.8,
    "dias_temp_roya_90d": 54,
    "dias_temp_roya_90d_normal": 47.6,
    "dias_temp_roya_90d_anom": 6.4,
    "tmax_floracion_anom_c": 1.4,
    "fuentes": ["CHIRPS v3.0", "NASA POWER"]
  },
  "registro": { "edad_mas_20_sin_recepa": false, "cosecha_alta_ano_pasado": true },
  "alertas": [
    { "codigo": "BROCA_ALTA_REGION", "fuente": "SENASA", "url": "https://…",
      "cita": "…texto literal…", "fecha": "2026-08-22", "vence": "2026-09-21" }
  ]
}
```

**`caso.json`**

```json
{
  "caso_id": "0f8c…-uuid",
  "finca_id": "LC-017",
  "ficha_version": "2026-27.1",
  "creado": "2026-08-15T09:12:00-05:00",
  "temporada": "fin_seca",
  "foto": { "tipo": "trampa", "archivo": "caso_0f8c.jpg", "calidad_ok": true, "reintentos": 0 },
  "conteo": { "yolo": 143, "clasico": 151, "dudoso": false, "modelo": "broca-y11n-v1",
              "cajas": [[0.12, 0.40, 0.01, 0.01]] },
  "respuestas": { "granos": "1-2" },
  "resultado": {
    "estado": "amarillo",
    "causa": "broca",
    "probabilidades": { "sin_problema": 0.08, "broca": 0.71, "roya": 0.07, "clima_floracion": 0.06, "plantas_viejas": 0.04, "otra": 0.04 },
    "reglas": ["R-GRANOS-02", "R-TRAMPA-01"],
    "mensaje": "R_BROCA"
  },
  "app_version": "0.1.0"
}
```

**`rules.json`** (una regla)

```json
{
  "id": "R-GRANOS-02",
  "evidencia": "E_GRANOS",
  "valor": "1-2",
  "lr": { "broca": 4.0, "sin_problema": 0.4 },
  "fuente": "INIA: umbral de daño económico de 5% de frutos brocados; muestreo SENASA",
  "tipo": "literatura"
}
```

**`config.json`**: umbrales de decisión (0,6 / 0,5 / 0,15), tope de LR (10), meses de cada época y pesos por evidencia y época.

---

## 5. Estructura del repositorio

```
chakra-nawi/
├─ contracts/            esquemas JSON + ejemplos
├─ apps/
│  ├─ campo/             PWA offline
│  └─ panel/             panel del técnico (1 página)
├─ packages/motor/       motor TS + rules.json + config.json + tests
├─ api/                  FastAPI + SQLite + Twilio
├─ pipeline/ficha/       CHIRPS v3 + NASA POWER → fichas
├─ ml/                   datos, entrenamiento, exportación, evaluación
├─ audio/                grabaciones + mensajes.json
├─ validacion/           sensibilidad, curva cobertura–precisión, figuras
├─ data/                 fincas.geojson, alertas_activas.json
└─ docs/                 PLAN.md, ARCHITECTURE.md, FUENTES.md, LIMITES_DE_DATOS.md, LO_QUE_SIGUE.md
```

---

## 6. Presupuesto de tamaño

| Elemento | Objetivo | Nota |
|---|---|---|
| Modelo ONNX | < 10 MB | Medir int8 y fp32 |
| Runtime `onnxruntime-web` (WASM) | 10–14 MB sin comprimir, ~6 MB con gzip | Se instala una vez, en el wifi de la cooperativa |
| Audios (14 × idioma) | < 0,5 MB | Opus |
| App | < 1 MB | |
| Ficha | ~5 KB | Una vez por campaña |
| Caso con foto | ~250 KB | Se sube cuando hay señal |

El tamaño total medido se muestra en el demo.

---

## 7. Despliegue

- **PWA y panel:** hosting estático con HTTPS y headers COOP/COEP configurables (Cloudflare Pages o Netlify con archivo `_headers`).
- **API:** Railway, Render o Fly con un volumen para SQLite.
- **Twilio:** cuenta **pagada** desde H0 (quita el aviso de prueba y el límite de números verificados), con Perú habilitado en los permisos geográficos. En el teléfono de Noor se guarda el número como "COOPERATIVA".
- En producción haría falta un número local, mediante un agregador peruano o la línea de la cooperativa. Va en `LO_QUE_SIGUE.md`.
