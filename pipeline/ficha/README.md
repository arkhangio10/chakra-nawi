# pipeline/ficha/ · Ficha de finca

CHIRPS v3 (lluvia) + NASA POWER `T2M`/`T2M_MAX`/`T2M_MIN` corregida por altitud (−6,5 °C/km) + `data/alertas_activas.json` → una ficha por finca.
Responsable: P3 (P2 si el equipo es de 3). Consume `data/fincas.geojson` y `alertas.schema.json`; produce `ficha.schema.json`.
Comando: `python -m pipeline.ficha --fincas data/fincas.geojson --out fichas/`.
