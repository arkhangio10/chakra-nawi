# Chakra Ñawi

Triaje offline que prioriza las visitas del técnico de la cooperativa para pequeños productores de café de La Convención (Cusco). **No es un diagnóstico autónomo.**
Hack-Nation 7 · Challenge 04 "Small AI for Development" (World Bank) · Agricultura, Perú.

- Plan (manda): [`docs/PLAN.md`](docs/PLAN.md) · Arquitectura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Contratos (congelados en H1): [`contracts/`](contracts/) · validar con `python scripts/validar_contratos.py`
- Antes de cualquier tarea: brújula anti-desvío (PLAN §1). Lo que no pase va a [`docs/LO_QUE_SIGUE.md`](docs/LO_QUE_SIGUE.md).

## Qué hay

| Carpeta | Qué es | Estado |
|---|---|---|
| `packages/motor` | Motor de triaje en TypeScript (PLAN §5): reglas citadas, pesos por época, tope de LR, decisión del semáforo | 17 tests |
| `apps/campo` | PWA offline de 3 pantallas: foto de la trampa → pregunta con dibujos → semáforo con voz | 23 tests |
| `api` | FastAPI + SQLite: recibe casos, sirve el panel del técnico y llama a Noor por Twilio | tests en `api/` |
| `apps/panel` | Panel del técnico, una sola página | — |
| `pipeline/ficha` | Ficha de clima por finca: CHIRPS v3 + NASA POWER, como anomalías frente a 1991–2020 | — |
| `ml` | Contador de broca: datos sintéticos con recortes de escarabajos reales, YOLO nano, exportación ONNX | ver `ml/README.md` |
| `audio` | Catálogo de 14 mensajes y conversión a `.opus` (app) y `.mp3` (llamada) | sintéticos: quechua (Meta MMS-TTS, texto sin validar) y castellano (TTS de Windows) |

## Correr en local

Requisitos: Python 3.11+ y Node 20.19+ (probado con Node 24).

```bash
# 1. Python: API, pipeline y validador
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
python scripts/validar_contratos.py                                     # debe decir TODO VÁLIDO
uvicorn api.app:app --reload                                            # http://localhost:8000 · panel en /panel

# 2. JavaScript: motor y PWA
npm install
npm test                                  # tests del motor y de la PWA
npm run dev                               # PWA en http://localhost:5173 (usa /api → localhost:8000)
```

### Probar en un Android real

La cámara, el service worker y `crypto.randomUUID` exigen HTTPS:

```bash
npm run dev:lan -w apps/campo             # https://<IP-de-la-laptop>:5173 con certificado propio (aceptar el aviso)
```

O compila y sirve la versión de producción: `npm run build && npm run preview -w apps/campo`.

En el teléfono:
1. Abrir la dirección, esperar a que cargue todo e instalar la app ("Agregar a pantalla de inicio").
2. Poner el **modo avión** y comprobar que el triaje funciona completo.
3. **Mantener presionado el logo** para abrir el modo técnico: finca, idioma, mes del demo ("caso de agosto"), ms por mosaico, tamaño total guardado y cola de casos.
4. Quitar el modo avión: los casos se envían solos a la API y aparecen en el panel.

Para probar sin tarjeta impresa: `docs/demo/foto_tarjeta_sintetica.jpg` (foto sintética en perspectiva).

## Honestidad de los datos

El contador de la app (`broca-y8n-v0-semireal`) se entrena con trampas sintéticas en las que la mayoría de las "brocas" son recortes de **escarabajos reales** de la misma subfamilia (Scolytinae; [Marais et al. 2024](https://huggingface.co/datasets/ChristopherMarais/Andrew_Alpha_training_data), PLOS ONE, doi:10.1371/journal.pone.0310716, **CC-BY-SA-4.0**). Con una especie que no vio en el entrenamiento, el error de conteo es ≈ 11 insectos por marco con el umbral 0,60 (subcuenta) y 0,17 detecciones falsas por trampa vacía. **Es un sustituto: su error no es desempeño en broca real.** Más adelante se reentrena con fotos de gorgojos sobre la tarjeta. Límites completos en [`docs/LIMITES_DE_DATOS.md`](docs/LIMITES_DE_DATOS.md).
