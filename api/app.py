"""API de Chakra Ñawi (ARCHITECTURE §3.5).

POST /casos               caso (JSON en el campo 'caso') + foto opcional, idempotente por caso_id
GET  /casos               lista para el panel, por prioridad
POST /llamadas/{caso_id}  llama a Noor con Twilio: L_INTRO + R_* dos veces (simulada si no hay credenciales)
GET  /fotos/{archivo}     foto del caso · GET /fichas/{finca_id}.json · GET /audio/...

Correr:  uvicorn api.app:app --reload      Variables: ver api/.env.example
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

RAIZ = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("CHAKRA_DB", RAIZ / "api/data/chakra.sqlite"))
FOTOS = Path(os.environ.get("CHAKRA_FOTOS", RAIZ / "api/uploads"))
PRIVADO = Path(os.environ.get("CHAKRA_FINCAS_PRIVADAS", RAIZ / "api/fincas_privadas.json"))
BASE_PUBLICA = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
PRIORIDAD = {"tecnico_urgente": 0, "tecnico": 1, "amarillo": 2, "verde": 3}


def _validador_caso() -> Draft202012Validator:
    esquemas = [json.loads(p.read_text(encoding="utf-8")) for p in (RAIZ / "contracts").glob("*.schema.json")]
    registro = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in esquemas)
    caso = next(s for s in esquemas if s["$id"].endswith("/caso.schema.json"))
    return Draft202012Validator(caso, registry=registro, format_checker=FormatChecker())


VALIDAR_CASO = _validador_caso()


def conectar() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS casos (
            caso_id TEXT PRIMARY KEY, finca_id TEXT NOT NULL, estado TEXT NOT NULL,
            prioridad INTEGER NOT NULL, creado TEXT NOT NULL, recibido TEXT NOT NULL,
            foto TEXT, json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS llamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, caso_id TEXT NOT NULL, sid TEXT,
            simulada INTEGER NOT NULL, mensaje TEXT NOT NULL, fecha TEXT NOT NULL);
    """)
    return con


def fincas_privadas() -> dict:
    """finca_id → {telefono, idioma}. Solo existe en el servidor (Ley 29733); nunca sale por la API."""
    return json.loads(PRIVADO.read_text(encoding="utf-8")) if PRIVADO.exists() else {}


app = FastAPI(title="Chakra Ñawi API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for ruta, carpeta in (("/fichas", RAIZ / "fichas"), ("/audio", RAIZ / "audio")):
    carpeta.mkdir(parents=True, exist_ok=True)
    app.mount(ruta, StaticFiles(directory=carpeta), name=ruta.strip("/"))


@app.post("/casos")
async def crear_caso(caso: str = Form(...), foto: UploadFile | None = File(None)):
    try:
        dato = json.loads(caso)
    except json.JSONDecodeError as e:
        raise HTTPException(422, f"caso no es JSON: {e}")
    errores = [f"/{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDAR_CASO.iter_errors(dato)]
    if errores:
        raise HTTPException(422, {"errores": errores})

    with closing(conectar()) as con:
        if con.execute("SELECT 1 FROM casos WHERE caso_id = ?", (dato["caso_id"],)).fetchone():
            return JSONResponse({"caso_id": dato["caso_id"], "duplicado": True}, status_code=200)
        nombre = None
        if foto is not None:
            FOTOS.mkdir(parents=True, exist_ok=True)
            nombre = Path(dato["foto"]["archivo"]).name
            (FOTOS / nombre).write_bytes(await foto.read())
        estado = dato["resultado"]["estado"]
        con.execute(
            "INSERT INTO casos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (dato["caso_id"], dato["finca_id"], estado, PRIORIDAD[estado], dato["creado"],
             datetime.now(timezone.utc).isoformat(), nombre, json.dumps(dato, ensure_ascii=False)),
        )
        con.commit()
    return JSONResponse({"caso_id": dato["caso_id"], "duplicado": False}, status_code=201)


@app.get("/casos")
def listar_casos():
    with closing(conectar()) as con:
        filas = con.execute("SELECT * FROM casos ORDER BY prioridad, creado DESC").fetchall()
        llamadas = {r["caso_id"]: r["fecha"] for r in con.execute(
            "SELECT caso_id, MAX(fecha) AS fecha FROM llamadas GROUP BY caso_id")}
    return [{
        **json.loads(f["json"]),
        "foto_url": f"/fotos/{f['foto']}" if f["foto"] else None,
        "recibido": f["recibido"],
        "ultima_llamada": llamadas.get(f["caso_id"]),
    } for f in filas]


@app.get("/fotos/{archivo}")
def ver_foto(archivo: str):
    ruta = FOTOS / Path(archivo).name
    if not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta)


def twiml(mensaje: str, idioma: str) -> str:
    """L_INTRO + el mensaje dos veces. Twilio <Play> no acepta Opus: se usan las copias .mp3."""
    url = lambda codigo: f"{BASE_PUBLICA}/audio/{idioma}/{codigo}.mp3"  # noqa: E731
    return (f'<Response><Play>{url("L_INTRO")}</Play><Play>{url(mensaje)}</Play>'
            f'<Pause length="1"/><Play>{url(mensaje)}</Play></Response>')


@app.post("/llamadas/{caso_id}")
def llamar(caso_id: str):
    with closing(conectar()) as con:
        fila = con.execute("SELECT json FROM casos WHERE caso_id = ?", (caso_id,)).fetchone()
        if not fila:
            raise HTTPException(404, "caso no encontrado")
        caso = json.loads(fila["json"])
        privado = fincas_privadas().get(caso["finca_id"])
        if not privado:
            raise HTTPException(409, f"la finca {caso['finca_id']} no tiene teléfono inscrito")
        mensaje = caso["resultado"]["mensaje"]
        xml = twiml(mensaje, privado.get("idioma", "quz"))

        sid_cuenta, token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
        origen = os.environ.get("TWILIO_FROM")
        simulada = not (sid_cuenta and token and origen)
        sid = None
        if not simulada:
            r = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid_cuenta}/Calls.json",
                auth=(sid_cuenta, token), timeout=30,
                data={"To": privado["telefono"], "From": origen, "Twiml": xml, "TimeLimit": 30},
            )
            if r.status_code >= 400:
                raise HTTPException(502, {"twilio": r.status_code, "detalle": r.text[:500]})
            sid = r.json().get("sid")
        con.execute("INSERT INTO llamadas (caso_id, sid, simulada, mensaje, fecha) VALUES (?, ?, ?, ?, ?)",
                    (caso_id, sid, int(simulada), mensaje, datetime.now(timezone.utc).isoformat()))
        con.commit()
    return {"caso_id": caso_id, "simulada": simulada, "sid": sid, "twiml": xml}


@app.get("/salud")
def salud():
    return Response("ok", media_type="text/plain")
