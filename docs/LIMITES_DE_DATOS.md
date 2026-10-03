# Límites de los datos

Lo que **no** sabemos o no podemos afirmar. Va tal cual a la lámina de datos del video (PLAN §9, punto 7). Responsable de mantenerlo: P4.

## Contador de broca

- **El modelo no ha visto broca peruana.** Se entrena con fotos propias de gorgojos (escarabajos oscuros pequeños de granos almacenados) sobre la tarjeta blanca, más montajes sintéticos.
- **El error de conteo con el sustituto no se presenta como desempeño en broca.** Se reportan por separado.
- Yellow Sticky Traps (CC0) solo prueba el pipeline: tiene el contraste invertido. Wadhwani queda fuera (polillas ~10 veces más grandes).
- La prueba con broca real depende de que CIRAD dé permiso para usar 3 fotos completas. Si no, solo hay resultados con el sustituto, declarados como tales.
- El dataset de broca de *Sensors* 2026 (PMC13075308) son **frutos**, no trampas, y **no es público**.
- La regla "si el contador clásico difiere más de 30% → técnico" solo se activa si se calibra.

## Trampa y granos

- **No existe un umbral de SENASA por trampa.** SENASA mide el % de frutos brocados; la trampa solo indica la tendencia del vuelo y funciona en época seca. El indicador de daño económico es 5% de frutos brocados (INIA).
- Con 20 granos hay mucho ruido de muestreo. Con 0 de 20, la infestación real puede llegar a 14% (límite superior al 95%): por eso un 0 nunca da verde por sí solo.

| Infestación real | P(0 con huequito) | P(1–2) | P(3+) |
|---|---|---|---|
| 2% | 67% | 33% | < 1% |
| 5% (umbral INIA) | 36% | 57% | 8% |
| 15% | 4% | 37% | 60% |

## Clima y satélite

- **Humedad de NASA POWER:** celdas de ~55 km, no sirven para el microclima. Solo se usa la temperatura (`T2M`, `T2M_MAX`, `T2M_MIN`), corregida por altitud (−6,5 °C/km), que es una aproximación.
- **NDVI:** no es defendible bajo sombra, y hay 79–90% de nubes de noviembre a marzo (medición propia en Planetary Computer). Queda fuera del motor.
- Los días de lluvia de nov–abr se calculan con CHIRPS v3 diario si está disponible; si no, con una aproximación mensual declarada en la ficha (`dias_lluvia_aprox_mensual`).
- Los meses de floración y cosecha vienen de literatura regional (±1 mes por altitud) y **no están confirmados con COCLA**.

## Reglas del motor

- De las 15 reglas de `contracts/rules.example.json`: 8 son supuestos, 5 vienen de literatura y 2 de fuentes oficiales. Incluso en las de literatura u oficiales, **la magnitud del LR es un supuesto** a revisar con la prueba de sensibilidad ±50%.
- "Plantas > 15 años" no discrimina (70–75% del área ya supera esa edad, Junta Nacional del Café); se usa "> 20 años y sin recepa".

## Fincas y población

- Las 5 fincas de `data/fincas.geojson` son **de ejemplo** (`"ejemplo": true`): polígonos y altitudes plausibles en La Convención, pero inventados.
- Alfabetización: el dato correcto es **33% de analfabetismo en mujeres rurales de lengua nativa frente a 9,3% en hombres** (INEI, Censo 2017). La alfabetización general con lengua materna originaria es de ≈84%. Casi nadie lee quechua escrito. (El "48,7% no lee" que se dijo antes era falso.)

## Voz

- Variantes del quechua: los audios son de quechua cusqueño, validados por un segundo hablante. Si no llegan, el respaldo `mms-tts-quz` se rotula "sintético" (licencia CC-BY-NC, uso no comercial).
- Dependemos del teléfono de la hija para la app; la llamada al teléfono básico es el único canal que llega directo a Noor.
