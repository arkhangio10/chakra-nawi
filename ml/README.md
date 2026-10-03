# ml/ · Contador de broca

Datos (fotos propias de gorgojos sobre la tarjeta + sintéticos; Yellow Sticky Traps solo para probar el pipeline), entrenamiento YOLOv8n/11n, exportación ONNX y evaluación.
Responsable: P2. Produce el `.onnx` que cumple `contracts/modelo-io.md`; los pesos y datasets no se suben a git.
**El error con el sustituto nunca se presenta como desempeño en broca.** Licencia Ultralytics AGPL-3.0.

## Estado: v0 · entrenado solo con datos sintéticos

`broca-y8n-v0-sint` es un YOLOv8n de una clase (`broca`) entrenado **solo con imágenes sintéticas** (`sintetico.py`). Sirve para que la PWA integre el modelo con la entrada y la salida definitivas. Se reemplaza por `broca-y8n-v1` cuando haya fotos reales de gorgojos sobre la tarjeta (ver "Próximos pasos").

| Archivo | Qué es |
|---|---|
| `sintetico.py` | Generador de marcos rectificados 1216×1216 sintéticos + mosaicos 640×640 + etiquetas YOLO + `conteos.json` |
| `entrenar.py` | Entrena YOLOv8n de una clase en CPU (mosaicos, `imgsz=640`) |
| `exportar.py` | Exporta ONNX (opset 17, sin NMS, 640 fijo), crea int8 dinámica, verifica E/S, escribe `modelos/metadata.json` y copia a `apps/campo/public/models/` |
| `evaluar.py` | Conteo en marcos completos con el **posprocesado exacto** de `modelo-io.md`; MAE por densidad, latencia, ejemplos |
| `contador_clasico.py` + `contador_clasico.json` | Contador de manchas sin IA (portable a JS). Solo mide, no activa reglas |
| `entrenar_colab.ipynb` | Lo mismo en Colab con GPU (plan B y para reentrenar más rápido) |
| `modelos/` | `.onnx` (gitignored) y `metadata.json` |
| `resultados/` | `eval_sintetico.json`, `eval_clasico.json` y 3 imágenes de ejemplo |

## Entorno (Windows)

Entorno propio en `ml/.venv` (no se usa el `.venv` de la raíz).

```bash
cd ml
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install numpy pillow opencv-python-headless
.venv/Scripts/python -m pip install "torch==2.5.1" "torchvision==0.20.1" --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install ultralytics onnx onnxruntime onnxslim
```

**Smart App Control bloquea torch reciente.** Con `torch 2.14.1+cpu` (la última versión, instalada por defecto), `import torch` falla con
`ImportError: DLL load failed while importing _C: Una directiva de Control de aplicaciones bloqueó este archivo.` (WinError 4551, archivo `torch/_C.cp312-win_amd64.pyd`; las DLL de `torch/lib` sí cargan).
Este equipo tiene Smart App Control en modo obligatorio (`HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy\VerifiedAndReputablePolicyState = 1`), que bloquea binarios sin firma y sin reputación. **`torch 2.5.1+cpu` sí carga** (es más antiguo y tiene reputación). onnxruntime (firmado por Microsoft), onnx y opencv cargan sin problema. No se desactivó Smart App Control.
Si vuelve a bloquear algo, el plan B es `entrenar_colab.ipynb`.

## Cómo correr todo (desde `ml/`)

```bash
# 1. Datos sintéticos: 400 marcos de entrenamiento, 60 de validación y 60 de prueba (~12 min con 8 procesos)
.venv/Scripts/python sintetico.py --train 400 --val 60 --test 60 --workers 8
#    vista rápida de 4 marcos con sus cajas en datasets/vista/
.venv/Scripts/python sintetico.py --vista 4

# 2. Entrenamiento en CPU con tope de 45 min (Ultralytics ajusta las épocas)
.venv/Scripts/python entrenar.py --horas 0.75

# 3. Exportación ONNX fp32 + int8 (+ w8 experimental), verificación y copia a apps/campo/public/models/
.venv/Scripts/python exportar.py --pesos runs/y8n_sint_v0/weights/best.pt --nombre broca-y8n-v0-sint --w8

# 4. Evaluación del conteo en los 60 marcos de prueba (fp32, int8, w8)
.venv/Scripts/python evaluar.py --nombre broca-y8n-v0-sint

# 5. Contador clásico: calibrar en VALIDACIÓN y medir en PRUEBA (después de evaluar.py)
.venv/Scripts/python contador_clasico.py --calibrar
.venv/Scripts/python contador_clasico.py
```

Datos en `datasets/sint_v0/` y corridas en `runs/` (ambos gitignored).

## Resultados v0 (DATOS SINTÉTICOS)

YOLOv8n con pesos COCO, 3 épocas en CPU (46 min; lote 8, 4 capas congeladas). Validación en mosaicos sintéticos: P 0,969 · R 0,965 · mAP50 0,990 · mAP50-95 0,791.
Prueba: 60 marcos sintéticos completos (6 sin brocas; 19 de 1–49; 18 de 50–300; 17 de >300) con el posprocesado del contrato. Detalle en `resultados/eval_sintetico.json` y `resultados/eval_clasico.json`.

**MAE del conteo (brocas por marco)**

| | <50 (n=25) | 50–300 (n=18) | >300 (n=17) | Total | Sesgo |
|---|---|---|---|---|---|
| fp32, score 0,25 (contrato) | 8,6 | 19,7 | 42,8 | 21,6 | +21,6 |
| int8, score 0,25 (contrato) | 7,8 | 19,2 | 43,1 | 21,3 | +21,3 |
| fp32, score 0,60 (propuesto) | 2,4 | 5,7 | 8,1 | 5,0 | +4,0 |
| int8, score 0,60 (propuesto) | 2,4 | 5,9 | 7,7 | 4,9 | +3,7 |
| Contador clásico (calibrado en val) | 17,1 | 40,0 | 64,6 | 37,4 | sobrecuenta |

- Con 0,25 el modelo **sobrecuenta**: precisión 0,89 y recall 0,99 (IoU 0,5). Los falsos positivos son sobre todo granitos de café alargados (ver `resultados/ejemplo_fallo_*.jpg`: 0 brocas reales, 15 contadas). En marcos sin brocas hay 3,5–4,2 falsos positivos de media.
- **Umbral propuesto: score 0,60** (NMS 0,45 igual). Se eligió en la VALIDACIÓN sintética (curva: 0,25 → MAE 22,1; 0,60 → 6,8; 0,70 → 9,0) y luego se midió en prueba. Es una propuesta para acordar antes de H8 y no cambia la E/S. Con fotos reales hay que recalibrarlo.
- Desacuerdo clásico vs YOLO (int8, 0,25), con diferencia > 30 %: 26,7 % de los marcos (60 % en <50; 5,6 % en 50–300; 0 % en >300). Solo se mide; no activa ninguna regla.

**Tamaño y latencia por mosaico** (onnxruntime 1.30 CPU, i7-1165G7, mediana)

| Variante | MB | 1 hilo | hilos por defecto | ¿< 10 MB? |
|---|---|---|---|---|
| fp32 `broca-y8n-v0-sint.onnx` | 11,7 | 94 ms | 62 ms | **No** |
| int8 `broca-y8n-v0-sint-int8.onnx` (dinámica, ConvInteger) | 3,2 | 104 ms | 81 ms | Sí |
| w8 experimental (solo pesos int8; no va a la PWA) | 3,15 | 215 ms | 214 ms | Sí |

**Recomendada para la PWA: int8.** Es la única variante del contrato que pesa menos de 10 MB. Su MAE es igual al de fp32 y en x86 es solo un 10 % más lenta. P1 debe medir las dos en el Android con `onnxruntime-web`: ConvInteger en WASM puede rendir distinto que en x86. Las dos están en `apps/campo/public/models/`.

## Lo que estos resultados NO significan

- **No son desempeño en broca real.** Las imágenes de prueba salen del mismo generador que las de entrenamiento: misma forma de "broca" (un elipsoide oscuro), mismos distractores, mismo papel. El modelo aprendió las reglas del generador, no la broca. El MAE sintético es una **cota optimista**.
- **No son desempeño con el sustituto (gorgojos).** Aún no hay fotos propias; cuando las haya, su error se reporta aparte y tampoco se presenta como desempeño en broca.
- **No validan el control de calidad ni la homografía.** Se generan directamente marcos ya rectificados; los errores de esquinas, reflejos o desenfoque fuerte del teléfono no están medidos.
- **La latencia es de onnxruntime en la CPU de una laptop (i7-1165G7)**, no de `onnxruntime-web` WASM en un Android barato. Sirve para comparar fp32 contra int8, no para prometer segundos en campo.
- **El contador clásico no está calibrado con fotos reales**: su desacuerdo con el YOLO no activa ninguna regla (PLAN §2).
- Los porcentajes de distractores (7–22 % de los insectos no son broca) y las densidades son supuestos del generador, no mediciones de trampas de La Convención.

## Próximos pasos: reentrenar con fotos reales de gorgojos (v1)

1. Fotografiar la tarjeta con gorgojos con 3–4 teléfonos distintos, a distintas horas y con distinta luz; 30–60 fotos con densidades de 0 a >300.
2. Rectificar cada foto con la misma homografía de la PWA (las 4 esquinas → 1216×1216) y guardar el marco.
3. Etiquetar las cajas (CVAT o Label Studio, formato YOLO, una clase) y contar a mano. Dos personas en una muestra para medir el acuerdo entre anotadores.
4. Separar por **sesión de fotos** (no por imagen) en entrenamiento/validación/prueba, para que la prueba no comparta luz ni teléfono con el entrenamiento.
5. Cortar en mosaicos con `cajas_en_mosaico` de `sintetico.py` y entrenar desde `runs/y8n_sint_v0/weights/best.pt`, mezclando reales y sintéticos (p. ej. 1:1). En Colab con GPU (`entrenar_colab.ipynb`), 50–100 épocas.
6. Reportar el MAE con gorgojos por densidad, el barrido del umbral y 3 fallos, siempre rotulado "sustituto".
7. Si CIRAD da permiso, evaluar (sin entrenar) con sus 3 fotos de broca real y reportarlo aparte.
8. Calibrar el contador clásico con las fotos reales antes de considerar la regla del 30 %.

## Yellow Sticky Traps

Omitido en v0. La CPU estuvo ocupada con el entrenamiento y el pipeline ya quedó probado de punta a punta con los sintéticos. El dataset tiene el contraste invertido (insectos claros u oscuros sobre fondo amarillo) y solo serviría para probar el pipeline (PLAN §6).
