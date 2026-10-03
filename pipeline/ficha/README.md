# pipeline/ficha/ · Ficha de finca

CHIRPS v3 (lluvia mensual + diaria `sat`, desagregada con NASA IMERG) + NASA POWER `T2M`/`T2M_MAX` corregidas por altitud (−6,5 °C/km desde la cota de la celda) + `data/alertas_activas.json` vigentes → una ficha por finca en `fichas/`.
Responsable: P3 (P2 si el equipo es de 3). Consume `data/fincas.geojson` (centroide del polígono) y `contracts/config.example.json`; produce `ficha.schema.json`.
Comando: `python -m pipeline.ficha --fecha 2026-10-03` (opciones: `--fincas`, `--out`, `--floracion AAAA`). Las descargas quedan en caché en `data/raw/`.
Diferencia con ARCHITECTURE §3.4: no usa `rasterio` (DLL bloqueada por Control de aplicaciones de Windows). Lee los COG con peticiones HTTP por rangos y un decodificador LZW en Python puro, verificado contra el `.bil` sin comprimir del mismo mes.
