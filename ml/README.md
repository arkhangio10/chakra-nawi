# ml/ · Contador de broca

Datos (fotos propias de gorgojos sobre la tarjeta + sintéticos; Yellow Sticky Traps solo para probar el pipeline), entrenamiento YOLOv8n/11n, exportación ONNX y evaluación.
Responsable: P2. Produce el `.onnx` que cumple `contracts/modelo-io.md`; los pesos y datasets no se suben a git.
**El error con el sustituto nunca se presenta como desempeño en broca.** Licencia Ultralytics AGPL-3.0.

## Estado: v0 · entrenado solo con datos sintéticos

`broca-y8n-v0-sint` es un YOLOv8n de una clase (`broca`) entrenado **solo con imágenes sintéticas** (`sintetico.py`). Sirve para que la PWA integre el modelo con la entrada y la salida definitivas. Se reemplaza por `broca-y8n-v1` cuando haya fotos reales de gorgojos sobre la tarjeta (ver "Próximos pasos").

| Archivo | Qué es |
|---|---|
| `sintetico.py` | Generador de marcos rectificados 1216×1216 sintéticos + mosaicos 640×640 + etiquetas YOLO + `conteos.json` |
| `entrenar.py` | Entrena YOLOv8n/YOLO11n de una clase en CPU (mosaicos, `imgsz=640`) |
| `exportar.py` | Exporta ONNX (opset 17, sin NMS, 640 fijo), crea int8 dinámica, verifica E/S, conserva metadata por modelo y copia a `apps/campo/public/models/` |
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
| fp32, score 0,25 (diagnóstico anterior) | 8,6 | 19,7 | 42,8 | 21,6 | +21,6 |
| int8, score 0,25 (diagnóstico anterior) | 7,8 | 19,2 | 43,1 | 21,3 | +21,3 |
| fp32, score 0,60 (contrato vigente) | 2,4 | 5,7 | 8,1 | 5,0 | +4,0 |
| int8, score 0,60 (contrato vigente) | 2,4 | 5,9 | 7,7 | 4,9 | +3,7 |
| Contador clásico (calibrado en val) | 17,1 | 40,0 | 64,6 | 37,4 | sobrecuenta |

- Con 0,25 el modelo **sobrecuenta**: precisión 0,89 y recall 0,99 (IoU 0,5). Los falsos positivos son sobre todo granitos de café alargados (ver `resultados/ejemplo_fallo_*.jpg`: 0 brocas sintéticas de referencia, 15 contadas). En marcos sin brocas hay 3,5–4,2 falsos positivos de media.
- **Umbral de conteo adoptado: score 0,60** (NMS 0,45 igual; candidatas desde 0,25). Se eligió en la VALIDACIÓN sintética (curva: 0,25 → MAE 22,1; 0,60 → 6,8; 0,70 → 9,0) y luego se midió en prueba. El contrato lo adoptó el 3 de octubre de 2026. Con fotos reales hay que recalibrarlo; cualquier cambio posterior se anota como propuesta, sin modificar el contrato congelado.
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

## Reproducción del experimento P2 (solo sintéticos)

Desde `ml/`, ` .venv/Scripts/python experimento_p2.py` ejecuta en orden:
YOLO11n con `weights/yolo11n.pt`, nombre `y11n_sint_v0` y presupuesto de 0,75 horas;
exportación `broca-y11n-v0-sint`; evaluación de ambos modelos sobre `sint_v0`;
generación de `datasets/sint_dificiles_v1` (400/60/60, semilla 20261004);
afinamiento de YOLOv8n desde `runs/y8n_sint_v0/weights/best.pt` por 0,75 horas;
exportación `broca-y8n-v0-sint-dificiles`; evaluación de los tres modelos en los mismos
marcos difíciles; calibración del contador clásico exclusivamente en validación y evaluación en prueba.
`--esperar-y11` continúa cuando termina un entrenamiento YOLO11n ya iniciado en esta sesión.
Ultralytics puede cortar una época por el límite de tiempo; las «épocas completadas»
del resumen cuentan filas de `results.csv` y pueden incluir esa época parcial.
Los registros conservan el progreso por lote; comparar también el tiempo efectivo.

El generador difícil agrega 15–80 granitos alargados de 1–1,5 mm en el 85 % de los
marcos y aumenta las mosquitas oscuras. Son supuestos sintéticos, no frecuencias
observadas en trampas. Los negativos no reciben etiqueta YOLO. `conteos.json`
registra `cafe_alargado_dificil` y la versión del generador. La semilla y carpeta nuevas
conservan el dataset original; no comparar MAE de datasets diferentes como si fueran iguales.

Los resultados nuevos y registros se guardan en `resultados/p2/`; `eval_sintetico.json`
y `eval_clasico.json` originales se conservan como resultados históricos (a 0,25).
El evaluador actual mide por defecto el contrato adoptado: candidatas ≥0,25,
NMS global a 0,45 y conteo ≥0,60. Los scores experimentales se eligen en validación,
de 0,25 a 0,90. No cambian el umbral usado en la PWA.
El campo heredado `real` de los JSON significa **conteo de referencia sintético**,
no presencia de fotos reales ni desempeño en broca real.
`exportar.py --evaluacion <JSON>` solo adjunta una evaluación si su nombre de modelo coincide.
La rejilla del contador clásico incluye área mínima de 40 a 140 px para los
granitos mayores; la elección usa exclusivamente validación sintética. Los
parámetros nuevos se guardan en `contador_clasico_dificiles.json`, sin reemplazar
la calibración histórica ni activar reglas.

El equipo tiene NVIDIA GeForce MX450 (2 GiB), verificada con `nvidia-smi`.
El entorno autorizado usa `torch==2.5.1+cpu` y `torchvision==0.20.1+cpu`, por lo que
no puede usar CUDA (`torch.cuda.is_available() == False` no prueba ausencia física de GPU).
Se conserva ese entorno. No hay navegador conectado para acceder a una sesión de Colab;
este experimento se ejecuta en CPU. `entrenar_colab.ipynb` queda preparado para repetirlo
con una GPU T4 accesible en Colab.
No hay fotos propias de gorgojos etiquetadas en `ml/datasets/`: los pasos de
`broca-y8n-v1` siguen pendientes y no se crea un modelo sintético con ese nombre.
Antes de entrenar con fotos reales, verificar las sesiones, las esquinas para
rectificación y las etiquetas; el reporte debe decir **sustituto**, nunca broca real.

Problema anotado del contrato: el límite dice «MB» pero los scripts reportan MiB
(bytes/2²⁰); se verificará también contra 10 000 000 bytes para evitar ambigüedad.
El contrato permanece sin cambios.

## Experimento P2 · SOLO SINTÉTICOS (2026-10-03)

Comparación medida con el contrato vigente (conteo ≥0,60). Latencia de laptop CPU; no es Android.

| Modelo / dataset | Variante | MiB | MAE a 0,60 | ms/mosaico 1 hilo | Score val | MAE prueba calibrado |
|---|---|---:|---:|---:|---:|---:|
| broca-y8n-v0-sint / sint_v0 | fp32 | 11.7 | 5.02 | 270.5 | 0.6 | 5.02 |
| broca-y8n-v0-sint / sint_v0 | int8 | 3.2 | 4.92 | 305.7 | 0.6 | 4.92 |
| broca-y8n-v0-sint / sint_v0 | w8 | 3.15 | 5.12 | 353.4 | 0.6 | 5.12 |
| broca-y11n-v0-sint / sint_v0 | fp32 | 10.11 | 4.22 | 234.9 | 0.6 | 4.22 |
| broca-y11n-v0-sint / sint_v0 | int8 | 2.87 | 4.12 | 290.3 | 0.6 | 4.12 |
| broca-y8n-v0-sint / sint_dificiles_v1 | fp32 | 11.7 | 26.93 | 327.3 | 0.75 | 13.75 |
| broca-y8n-v0-sint / sint_dificiles_v1 | int8 | 3.2 | 25.65 | 371.6 | 0.75 | 14.05 |
| broca-y8n-v0-sint / sint_dificiles_v1 | w8 | 3.15 | 26.42 | 433.8 | 0.75 | 13.43 |
| broca-y11n-v0-sint / sint_dificiles_v1 | fp32 | 10.11 | 18.5 | 278.5 | 0.75 | 10.62 |
| broca-y11n-v0-sint / sint_dificiles_v1 | int8 | 2.87 | 17.63 | 351.3 | 0.75 | 10.25 |
| broca-y8n-v0-sint-dificiles / sint_dificiles_v1 | fp32 | 11.7 | 9.13 | 323.6 | 0.45 | 5.13 |
| broca-y8n-v0-sint-dificiles / sint_dificiles_v1 | int8 | 3.2 | 12.27 | 360.8 | 0.4 | 4.77 |

Contador clásico recalibrado en validación difícil sintética: MAE prueba **27.8**. No está calibrado con fotos reales y no activa reglas.

El barrido elige score solo en validación. Un score distinto de 0,60 es una propuesta; el contrato congelado permanece intacto. Se conserva el modelo vigente en metadata y las variantes nuevas tienen metadata individual. Las épocas y tiempos efectivos están en cada resumen de entrenamiento.

Los datasets son diferentes: comparar modelos solo dentro del mismo dataset. Detalle: `resultados/p2/comparacion_sintetica.json`. **Ninguno de estos errores mide desempeño en broca real o en gorgojos.**

Cierre P2: YOLO11n fp32 ocupa **10 604 660 bytes (10,60 MB; 10,11 MiB)**: no alcanza el limite de 10 MB. Su int8 ocupa 3 013 941 bytes.

En el mismo test dificil, el reentrenamiento int8 reduce los falsos positivos en los seis marcos vacios de **21,00 a 0,33 por marco**, y el MAE a score 0,60 de **25,65 a 12,27**. Sigue existiendo subconteo (sesgo -12,03). A 0,60 ninguna variante nueva satisface simultaneamente tamano y tolerancia de error: fp32 supera 10 MB; int8 supera el MAE tolerado de 10,54. La recomendacion fp32 del evaluador es solo una alternativa experimental fuera de los criterios completos, no una aprobacion para despliegue.

La propuesta int8 **score 0,40** se eligio en validacion (MAE 4,92) y obtuvo MAE **4,77** en test separado. No esta activada y requiere revisar el contrato con el equipo. El contador clasico obtuvo MAE 27,28 en validacion y 27,80 en test. **Todo es sintetico: no demuestra desempeno en broca real ni en el sustituto.**

## Modo semi-real: recortes de escarabajos reales (sustituto, no broca)

`python semireal.py` corre todo sin intervención (~1,5–2 h en CPU):

1. `recortes_reales.py` descarga ~80 fotos de **escarabajos Scolytinae reales** (la subfamilia de la broca) de
   [Marais et al. 2024](https://huggingface.co/datasets/ChristopherMarais/Andrew_Alpha_training_data)
   (PLOS ONE, doi:10.1371/journal.pone.0310716, **CC-BY-SA-4.0**). Son fotos de insectos en etanol sobre una baldosa blanca;
   cada escarabajo aislado se recorta con su alfa (patas incluidas) y con la máscara del cuerpo (define la caja).
   Se descartan la bolita de referencia, los restos y los insectos que se tocan.
2. `sintetico.py --recortes` pega esos recortes como "brocas" (70 %): los reescala a 1,7 mm, los rota y los oscurece hacia el color de la broca.
   Los "otros escarabajos" (distractores) salen de especies más grandes.
3. Separación por **especie**. Entrenamiento y validación: *Coccotrypes dactyliperda*, *Pityophthorus juglandis*,
   *Xyleborinus saxesenii* y *Xyleborus affinis* (distractores *Hylesinus varius* y *Platypus cylindrus*).
   **Prueba**: *Xylosandrus compactus* (distractor *Phloeosinus dentatus*), especies que el modelo nunca vio.
4. Afinamiento desde `y8n_sint_dificiles_v1`, exportación `broca-y8n-v0-semireal` (**no se copia a la PWA**) y evaluación
   del modelo vigente, del de difíciles y del semi-real en los mismos marcos. Resultado en `resultados/semireal/RESUMEN.md`.

Qué mide y qué no: mide si el modelo generaliza a **insectos reales de una especie no vista**, parecida a la broca.
No mide broca real, ni la luz del celular, ni la homografía (las fotos de origen tienen flash de anillo y están en etanol).
Si se redistribuyen los recortes o las imágenes derivadas, llevan la atribución de `datasets/recortes_scolytinae/ATRIBUCION.txt`
y la misma licencia.

Otras fuentes revisadas (2026-10-03):
- **CATIE / SVMendoza** ([GitHub](https://github.com/SVMendoza/Detection-and-count-CBB)): broca real en trampas BROCAP.
  En el repositorio solo hay 3 fotos completas y 13 recortes, y **no tiene licencia**. El dataset completo (Broca2000) no es público:
  se pide por correo y, sin permiso, no se usa.
- **iNaturalist**: 45 fotos de *H. hampei* con licencia CC. Son fotos sueltas (no de trampa) con otra escala; no sirven para medir el conteo.
- Descartadas: Chaullay/Cusco (fotos de frutos, fuera de alcance), figshare Tribolium/Sitophilus (recortes de 224 px para clasificar),
  Hawái/Dryad (solo conteos, sin imágenes).
