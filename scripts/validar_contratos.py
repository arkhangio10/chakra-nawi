"""Valida los ejemplos de contracts/ y los archivos de data/ contra sus esquemas (JSON Schema 2020-12).

Uso:  python scripts/validar_contratos.py      (requiere: pip install jsonschema)
Sale con código 1 si algo falla.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "contracts"

# (archivo a validar, esquema)
PARES = [
    ("contracts/ficha.example.json", "ficha.schema.json"),
    ("contracts/caso.example.json", "caso.schema.json"),
    ("contracts/rules.example.json", "rules.schema.json"),
    ("contracts/config.example.json", "config.schema.json"),
    ("contracts/mensajes.example.json", "mensajes.schema.json"),
    ("data/alertas_activas.json", "alertas.schema.json"),
]

# Esquema mínimo para data/fincas.geojson (no es un contrato entre equipos: solo servidor y pipeline)
FINCAS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["type", "features"],
    "properties": {
        "type": {"const": "FeatureCollection"},
        "features": {
            "type": "array",
            "minItems": 5,
            "items": {
                "type": "object",
                "required": ["type", "properties", "geometry"],
                "properties": {
                    "properties": {
                        "type": "object",
                        "required": ["finca_id", "ejemplo", "altitud_m"],
                        "properties": {
                            "finca_id": {"type": "string", "pattern": "^LC-\\d{3}$"},
                            "ejemplo": {"const": True},
                            "altitud_m": {"type": "number", "minimum": 400, "maximum": 3000},
                        },
                    },
                    "geometry": {
                        "type": "object",
                        "required": ["type", "coordinates"],
                        "properties": {"type": {"const": "Polygon"}},
                    },
                },
            },
        },
    },
}


def cargar(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    esquemas = {p.name: cargar(p) for p in CONTRATOS.glob("*.schema.json")}
    registro = Registry().with_resources(
        (s["$id"], Resource.from_contents(s)) for s in esquemas.values()
    )
    errores = 0

    def validar(nombre, dato, esquema):
        nonlocal errores
        Draft202012Validator.check_schema(esquema)
        v = Draft202012Validator(esquema, registry=registro, format_checker=FormatChecker())
        fallos = sorted(v.iter_errors(dato), key=lambda e: list(e.path))
        if fallos:
            errores += len(fallos)
            print(f"FALLA  {nombre}")
            for e in fallos:
                print(f"       en /{'/'.join(map(str, e.path))}: {e.message}")
        else:
            print(f"OK     {nombre}")

    for archivo, esquema in PARES:
        validar(f"{archivo}  ->  {esquema}", cargar(RAIZ / archivo), esquemas[esquema])
    for ficha in sorted((RAIZ / "fichas").glob("*.json")):
        validar(f"fichas/{ficha.name}  ->  ficha.schema.json", cargar(ficha), esquemas["ficha.schema.json"])
    fincas = cargar(RAIZ / "data/fincas.geojson")
    validar("data/fincas.geojson  ->  (esquema mínimo en el script)", fincas, FINCAS_SCHEMA)

    # Coherencia entre contratos (lo que JSON Schema no puede ver)
    def chequeo(nombre, ok, detalle=""):
        nonlocal errores
        print(f"{'OK' if ok else 'FALLA':6} {nombre}{'' if ok else ': ' + detalle}")
        errores += 0 if ok else 1

    reglas = cargar(CONTRATOS / "rules.example.json")["reglas"]
    ids = [r["id"] for r in reglas]
    caso = cargar(CONTRATOS / "caso.example.json")
    config = cargar(CONTRATOS / "config.example.json")
    chequeo("ids de reglas únicos", len(ids) == len(set(ids)))
    faltan = set(caso["resultado"]["reglas"]) - set(ids)
    chequeo("caso.resultado.reglas existen en rules", not faltan, str(faltan))
    probs = sum(caso["resultado"]["probabilidades"].values())
    chequeo("probabilidades del caso suman 1", abs(probs - 1) < 1e-6, f"suman {probs}")
    meses = sorted(m for t in config["temporadas"].values() for m in t["meses"])
    chequeo("cada mes pertenece a una sola temporada", meses == list(range(1, 13)), str(meses))
    mes_caso = next(k for k, t in config["temporadas"].items() if caso["mes"] in t["meses"])
    chequeo("caso.temporada coincide con su mes", mes_caso == caso["temporada"], mes_caso)
    priors = sum(config["priors_base"].values())
    chequeo("priors_base suman 1", abs(priors - 1) < 1e-6, f"suman {priors}")
    ids_fincas = {f["properties"]["finca_id"] for f in fincas["features"]}
    chequeo("ficha y caso apuntan a una finca de fincas.geojson",
            {caso["finca_id"], cargar(CONTRATOS / "ficha.example.json")["finca_id"]} <= ids_fincas)
    n_sup = sum(r["tipo"] == "supuesto" for r in reglas)
    print(f"\nReglas: {len(reglas)} ({n_sup} supuesto, "
          f"{sum(r['tipo'] == 'literatura' for r in reglas)} literatura, "
          f"{sum(r['tipo'] == 'oficial' for r in reglas)} oficial)")
    print("\nTODO VÁLIDO" if errores == 0 else f"\n{errores} ERROR(ES)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
