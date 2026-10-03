# data/

`fincas.geojson`: 5 fincas **de ejemplo** (`"ejemplo": true`), polígonos inventados pero plausibles en La Convención. Solo servidor y pipeline: nunca va al teléfono.
`alertas_activas.json`: alertas oficiales cargadas a mano (SENASA, SENAMHI, ENFEN) con URL y cita literal; cumple `contracts/alertas.schema.json`.
Lo usan `pipeline/ficha` (P3) y la API. Los datos descargados (CHIRPS, POWER) van a `data/raw/`, que no se sube a git.
