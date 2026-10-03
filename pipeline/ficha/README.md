# pipeline/ficha/ · Ficha de finca

CHIRPS v3 (lluvia mensual + diaria `sat`, desagregada con NASA IMERG) + NASA POWER `T2M`/`T2M_MAX` corregidas por altitud (−6,5 °C/km desde la cota de la celda) y `PRECTOTCORR` + `data/alertas_activas.json` vigentes → una ficha por finca en `fichas/`.
Responsable: P3 (P2 si el equipo es de 3). Consume `data/fincas.geojson` (centroide del polígono) y `contracts/config.example.json`; produce `ficha.schema.json`.
Comando: `python -m pipeline.ficha --fecha 2026-10-03` (opciones: `--fincas`, `--out`, `--floracion AAAA`). Las descargas quedan en caché en `data/raw/`.

Anomalías para la roya (`clima.py`): cada una compara una serie consigo misma frente a 1991–2020 (misma fuente, mismo punto, misma ventana de calendario).
- `dias_lluvia_nov_abr_normal/_anom/_sd`: días ≥ 1 mm de nov–abr con NASA POWER `PRECTOTCORR` (CHIRPS diario `sat` empieza en 1998; el `rnl` exige ~5 400 teselas de ~1 MB).
- `dias_temp_roya_90d_normal/_anom/_sd`: días en 17–25 °C de los últimos 90 con `T2M` corregida por altitud.

`python -m pipeline.ficha.historico --fecha 2026-10-03` imprime lo que habría dado la ficha en cada octubre desde 1991 y qué años activan R-LLUVIA-01 y R-TEMP-01 con los cortes de `contracts/rules.example.json` (usa la caché de POWER).

Diferencia con ARCHITECTURE §3.4: no usa `rasterio` (DLL bloqueada por Control de aplicaciones de Windows). Lee los COG con peticiones HTTP por rangos y un decodificador LZW en Python puro, verificado contra el `.bil` sin comprimir del mismo mes.
