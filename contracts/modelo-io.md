# Contrato del modelo ONNX (congelado en H1)

Lo produce P2 (`ml/`) y lo consume P1 (`apps/campo`, `onnxruntime-web` WASM). Si cambia algo de esta página después de H1, hace falta el acuerdo de los cuatro (PLAN §3).

## Modelo

| Campo | Valor |
|---|---|
| Arquitectura | YOLOv8n o YOLO11n, **una sola clase**. No YOLO26 (su salida es distinta) |
| Clase 0 | `broca` (entrenada con el sustituto: gorgojos sobre la tarjeta; ver `docs/LIMITES_DE_DATOS.md`) |
| Exportación | `yolo export format=onnx imgsz=640 opset=17 simplify=True dynamic=False nms=False half=False` |
| Variantes | fp32 e int8 (cuantización dinámica). Misma entrada y salida; se elige la más rápida con precisión aceptable |
| Archivo | `broca-<arq>-v<N>.onnx` (p. ej. `broca-y11n-v1.onnx`); ese nombre sin extensión va en `caso.conteo.modelo` |
| Tamaño | < 10 MB |

## Entrada

| Campo | Valor |
|---|---|
| Nombre | `images` |
| Forma | `[1, 3, 640, 640]`, `float32`, NCHW |
| Color | RGB (no BGR), valores en `[0, 1]` (píxel / 255). Sin normalización por media ni desviación |
| Contenido | Un mosaico de 640×640 px del **marco rectificado** (ver abajo). Los mosaicos incompletos se rellenan con gris `(114, 114, 114)` |

## Salida

| Campo | Valor |
|---|---|
| Nombre | `output0` |
| Forma | `[1, 5, 8400]`, `float32` |
| Fila 0–3 | `cx, cy, w, h` en **píxeles del mosaico** (0–640) |
| Fila 4 | Puntaje de la clase `broca` (0–1, ya pasado por sigmoide) |
| NMS | **No viene en el modelo**. Se hace en JS (ver posprocesado) |

## Marco rectificado y mosaicos

1. El control de calidad detecta las 4 esquinas negras de la tarjeta y aplica una homografía al **marco de 10×10 cm → 1216×1216 px** (≈ 0,082 mm/px; una broca de 1,7 mm ocupa ≈ 21 px de largo).
2. Se corta en **4 mosaicos de 640×640 con 64 px de solape**: orígenes `x, y ∈ {0, 576}`.
3. Cada mosaico se infiere por separado; las cajas se dibujan en cuanto termina su mosaico (con `G_ESPERA` sonando).

## Posprocesado (en `apps/campo`)

1. Descartar puntaje < `0,25`.
2. Pasar las cajas a coordenadas del marco (`+ origen del mosaico`).
3. NMS global con IoU `0,45` (las cajas repetidas en el solape se funden aquí).
4. Normalizar dividiendo por 1216 → `[xc, yc, w, h]` en `[0, 1]`. Ese es el formato de `caso.conteo.cajas`.
5. `caso.conteo.yolo` = número de cajas que quedan.

Los umbrales `0,25` y `0,45` son los de Ultralytics por defecto; P2 puede proponer otros con su curva de error antes de H8, sin cambiar la forma de la entrada ni de la salida.
