# Límites de los datos

Lo que **no** sabemos o no podemos afirmar. Va tal cual a la lámina de datos del video (PLAN §9, punto 7). Responsable de mantenerlo: P4.

## Contador de broca

- **El modelo no ha visto broca peruana.** Se entrena con fotos propias de gorgojos (escarabajos oscuros pequeños de granos almacenados) sobre la tarjeta blanca, más montajes sintéticos.
- **El error de conteo con el sustituto no se presenta como desempeño en broca.** Se reportan por separado.
- Yellow Sticky Traps (CC0) solo prueba el pipeline: tiene el contraste invertido. Wadhwani queda fuera (polillas ~10 veces más grandes).
- La prueba con broca real depende de que CATIE (con CIRAD) dé permiso para usar 3 fotos completas. Si no, solo hay resultados con el sustituto, declarados como tales.
- El dataset de broca de *Sensors* 2026 (PMC13075308) son **frutos**, no trampas, y **no es público**.
- La regla "si el contador clásico difiere más de 30% → técnico" solo se activa si se calibra.

## Trampa y granos

- **No existe un umbral de SENASA por trampa.** SENASA mide el % de frutos brocados; la trampa solo indica la tendencia del vuelo y funciona en época seca. El indicador de daño económico es 5% de frutos brocados (INIA).
- Con 20 granos hay mucho ruido de muestreo. Con 0 de 20, la infestación real puede llegar a 16,8% (límite superior de Clopper-Pearson, **bilateral** al 95%; el unilateral al 95% da 13,9%): por eso un 0 nunca da verde por sí solo. La tabla se regenera con `python validacion/binomial.py`.

| Infestación real | P(0 con huequito) | P(1–2) | P(3+) |
|---|---|---|---|
| 2% | 67% | 33% | < 1% |
| 5% (umbral INIA) | 36% | 57% | 8% |
| 15% | 4% | 37% | 60% |

## Clima y satélite

- **Humedad de NASA POWER:** celdas de ~55 km, no sirven para el microclima. Solo se usan la temperatura (`T2M`, `T2M_MAX`), corregida por altitud (−6,5 °C/km), que es una aproximación, y la precipitación `PRECTOTCORR` para la anomalía de días de lluvia de la región.
- **NDVI:** no es defendible bajo sombra, y hay 79–90% de nubes de noviembre a marzo (medición propia en Planetary Computer). Queda fuera del motor.
- **La capa de clima es una señal regional del año, no de la finca.** Las 5 fincas caen en la misma celda de NASA POWER (cota de la celda: 2766 m): la lluvia de POWER es idéntica en las 5, y dentro de la zona solo cambia la altitud, que desplaza la temperatura. La anomalía de Tmax en floración es la misma (+0,3 °C). La corrección extrapola entre 1,1 y 1,7 km con un gradiente fijo de −6,5 °C/km. Como control: LC-004 (1050 m) da 25,0 °C de media en jul–sep, coherente con Quillabamba.
- **La roya usa anomalías, no valores absolutos.** La Convención es húmeda todos los años: con valores absolutos, R-LLUVIA-01 (≥ 100 días) y R-TEMP-01 (≥ 45 de 90 días) se activaban en las 5 fincas todos los años. Cada anomalía compara una serie consigo misma (temporada actual menos su propia normal 1991–2020, en el mismo punto y la misma ventana de calendario):

| Campo de la ficha | Evidencia | Fuente de la temporada **y** de la normal | Normal 1991–2020 (± DE interanual) |
|---|---|---|---|
| `dias_lluvia_nov_abr_anom` | `E_LLUVIA_DIAS` | NASA POWER `PRECTOTCORR` (MERRA-2 con corrección de sesgo), días ≥ 1 mm de nov–abr, sin el 29 de febrero | 106,2 ± 10,9 días, igual en las 5 fincas |
| `dias_temp_roya_90d_anom` | `E_TEMP_ROYA` | NASA POWER `T2M` corregida por altitud, días en 17–25 °C de los 90 que terminan en el último dato | De 89,7 ± 0,7 (LC-002, 1700 m) a 55,9 ± 14,0 (LC-004, 1050 m) |

- **Por qué POWER y no CHIRPS para los días de lluvia:** CHIRPS v3 diario `sat` empieza en 1998 (no cubre 1991–2020), y el diario `rnl` (desagregado con ERA5) exige leer ~5 400 teselas de ~1 MB para 30 temporadas, demasiado para el hackathon. `dias_lluvia_nov_abr` sigue siendo de CHIRPS `sat` y solo es informativo: el diario `sat` reparte la lluvia de cada péntada en muchos días de 1–2 mm y **sobreestima los días ≥ 1 mm** (140–156 de 181). Por eso `dias_lluvia_nov_abr` ≠ `_normal` + `_anom`, que son de POWER.
- **Lo que dicen las anomalías** (`python -m pipeline.ficha.historico`): la temporada 2025-26 da +6,8 días de lluvia (no activa R-LLUVIA-01, corte +11 ≈ +1 DE); 2024-25 daba +17,8 y 2022-23, −37,2 (sequía). La epidemia de roya de 2012-13 da +10,8: justo en el borde, no se activa. Desde 1300 m casi todos los días ya caen en 17–25 °C (desviación estándar < 4 días): en esas fincas R-TEMP-01 no puede activarse y el año no aporta. En 1991–2020, R-TEMP-01 se activa 5 de 30 años en LC-003 y 9 de 30 en LC-004.
- **Tendencia de calentamiento:** frente a la normal 1991–2020, las fincas bajas tienen anomalías de temperatura negativas casi todos los años desde 2015 (más días por encima de 25 °C). La normal de 30 años no corrige esa tendencia.
- **Fuentes mezcladas en los meses recientes:** POWER sirve MERRA-2 hasta unos meses antes del presente y completa lo más reciente con GEOS-IT (el encabezado de la respuesta declara MERRA2 y GEOSIT). La ventana de temperatura de jul–sep de 2026 puede venir de un modelo distinto al de su normal. No lo pudimos verificar día por día.
- **La ventana de 90 días se fija al generar la ficha** (jul–sep si se genera a inicios de octubre), pero `E_TEMP_ROYA` pesa "plena" en lluvias (nov–abr). Hasta que la ficha se regenere en la temporada, la evidencia de temperatura habla de la seca anterior.
- Los meses de floración y cosecha vienen de literatura regional (±1 mes por altitud) y **no están confirmados con COCLA**.

## Reglas del motor

- De las 15 reglas de `contracts/rules.example.json`: 9 son supuestos, 4 vienen de literatura y 2 de fuentes oficiales. Incluso en las de literatura u oficiales, **la magnitud del LR es un supuesto** a revisar con la prueba de sensibilidad ±50%.
- "Plantas > 15 años" no discrimina (70–75% del área ya supera esa edad, Junta Nacional del Café); se usa "> 20 años y sin recepa".

## Fincas y población

- Las 5 fincas de `data/fincas.geojson` son **de ejemplo** (`"ejemplo": true`): polígonos y altitudes plausibles en La Convención, pero inventados.
- Alfabetización: el dato correcto es **33% de analfabetismo en mujeres rurales de lengua nativa frente a 9,3% en hombres** (INEI, Censo 2017). La alfabetización general con lengua materna originaria es de ≈84%. Casi nadie lee quechua escrito. (El "48,7% no lee" que se dijo antes era falso.)

## Voz

- Idioma: **el quechua de la entrega es sintético y sin validar.** No conseguimos un hablante de quechua cusqueño a tiempo. Los 14 textos (`texto_quz` en `contracts/mensajes.example.json`) los tradujo el equipo y pueden tener errores de vocabulario o de variante; la voz es Meta MMS-TTS (`facebook/mms-tts-quz`, CC-BY-NC 4.0), entrenada sobre todo con lecturas religiosas, así que suena plana y puede pronunciar mal los préstamos ("técnico", "broca", "repase"). Por eso cada mensaje es corto, va con dibujo, y lo químico o biológico siempre pasa por el técnico. Para el piloto, el quechua debe grabarlo una persona de la cooperativa y validarlo un segundo hablante (`docs/GUION_AUDIOS.md`); `audio/convertir.py` lo reemplaza sin tocar la app.
- Dependemos del teléfono de la hija para la app; la llamada al teléfono básico es el único canal que llega directo a Noor.
