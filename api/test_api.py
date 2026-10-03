"""python -m pytest api -q"""
import copy
import json
import re
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = json.loads((RAIZ / "contracts/caso.example.json").read_text(encoding="utf-8"))


def nuevo_cliente():
    """Recarga api.app para que lea las variables de entorno del test."""
    import importlib

    import api.app as modulo
    importlib.reload(modulo)
    from fastapi.testclient import TestClient
    return TestClient(modulo.app)


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAKRA_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("CHAKRA_FOTOS", str(tmp_path / "fotos"))
    privado = tmp_path / "privado.json"
    privado.write_text(json.dumps({"LC-001": {"telefono": "+51900000000", "idioma": "quz"}}))
    monkeypatch.setenv("CHAKRA_FINCAS_PRIVADAS", str(privado))
    for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "CHAKRA_FINCAS_PRIVADAS_JSON",
              "CHAKRA_AUDIO", "CHAKRA_REGLAS", "PUBLIC_BASE_URL", "RENDER_EXTERNAL_URL"):
        monkeypatch.delenv(v, raising=False)
    return nuevo_cliente()


def caso(estado="amarillo", mensaje="R_BROCA", creado="2026-08-15T09:12:00-05:00"):
    c = copy.deepcopy(EJEMPLO)
    c["caso_id"] = str(uuid.uuid4())
    c["creado"] = creado
    c["resultado"]["estado"], c["resultado"]["mensaje"] = estado, mensaje
    return c


def enviar(cliente, c, foto=True):
    files = {"foto": ("x.jpg", b"\xff\xd8jpeg", "image/jpeg")} if foto else None
    return cliente.post("/casos", data={"caso": json.dumps(c)}, files=files)


def test_idempotente(cliente):
    c = caso()
    assert enviar(cliente, c).status_code == 201
    r = enviar(cliente, c)
    assert r.status_code == 200 and r.json()["duplicado"] is True
    assert len(cliente.get("/casos").json()) == 1


def test_rechaza_caso_invalido(cliente):
    c = caso()
    c["resultado"]["estado"] = "rojo"
    r = enviar(cliente, c)
    assert r.status_code == 422 and "estado" in json.dumps(r.json())


def test_orden_por_prioridad(cliente):
    for est, msg in [("verde", "R_VERDE"), ("tecnico_urgente", "R_TECNICO_URGENTE"),
                     ("amarillo", "R_BROCA"), ("tecnico", "R_TECNICO")]:
        enviar(cliente, caso(est, msg), foto=False)
    estados = [c["resultado"]["estado"] for c in cliente.get("/casos").json()]
    assert estados == ["tecnico_urgente", "tecnico", "amarillo", "verde"]


def test_foto_se_sirve(cliente):
    c = caso()
    enviar(cliente, c)
    url = cliente.get("/casos").json()[0]["foto_url"]
    assert cliente.get(url).content == b"\xff\xd8jpeg"


def test_llamada_simulada_sin_credenciales(cliente):
    c = caso()
    enviar(cliente, c)
    r = cliente.post(f"/llamadas/{c['caso_id']}").json()
    assert r["simulada"] is True
    assert r["twiml"].count("R_BROCA.mp3") == 2 and "L_INTRO.mp3" in r["twiml"]
    assert "+51" not in json.dumps(cliente.get("/casos").json())  # el teléfono nunca sale por la API
    assert cliente.get("/casos").json()[0]["ultima_llamada"]


def test_llamada_finca_sin_telefono(cliente):
    c = caso()
    c["finca_id"] = "LC-005"
    enviar(cliente, c)
    assert cliente.post(f"/llamadas/{c['caso_id']}").status_code == 409


# --- Panel, reglas, audio de la llamada y despliegue ---

def urls_play(twiml: str) -> list[str]:
    return re.findall(r"<Play>(.*?)</Play>", twiml)


def test_panel_se_sirve(cliente):
    r = cliente.get("/panel")  # redirige a /panel/
    assert r.status_code == 200 and "Panel del técnico" in r.text and 'src="panel.js"' in r.text
    js = cliente.get("/panel/panel.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert "text/css" in cliente.get("/panel/panel.css").headers["content-type"]
    assert cliente.get("/", follow_redirects=False).headers["location"] == "/panel/"


def test_reglas_con_fuente_y_tipo(cliente):
    r = cliente.get("/reglas")
    assert r.status_code == 200
    reglas = r.json()["reglas"]
    assert reglas and all(x["fuente"] and x["tipo"] in {"oficial", "literatura", "supuesto"} for x in reglas)
    assert set(EJEMPLO["resultado"]["reglas"]) <= {x["id"] for x in reglas}  # el panel encuentra las del caso
    assert r.json()["origen"].endswith(".json")


def test_reglas_desde_variable(cliente, tmp_path, monkeypatch):
    propio = tmp_path / "rules.json"
    propio.write_text(json.dumps({"version": "x", "reglas": [{"id": "R-X-01"}]}), encoding="utf-8")
    monkeypatch.setenv("CHAKRA_REGLAS", str(propio))
    assert nuevo_cliente().get("/reglas").json()["reglas"][0]["id"] == "R-X-01"


def test_twiml_usa_mp3_que_existen(cliente):
    c = caso()
    enviar(cliente, c)
    r = cliente.post(f"/llamadas/{c['caso_id']}").json()
    urls = urls_play(r["twiml"])
    assert len(urls) == 3 and all(u.endswith(".mp3") for u in urls)  # Twilio <Play> no acepta Opus
    for u in set(urls):
        audio = cliente.get(u.removeprefix("http://localhost:8000"))
        assert audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg" and len(audio.content) > 1000
    # La finca LC-001 es quechua; mientras no haya quz grabado, se usa el castellano y se avisa
    if not (RAIZ / "audio/quz/R_BROCA.mp3").exists():
        assert r["respaldo"] is True and set(r["idioma_audio"].values()) == {"es"}


def test_respaldo_castellano_por_archivo(cliente, tmp_path, monkeypatch):
    audio = tmp_path / "audio"
    for ruta in ("es/L_INTRO.mp3", "es/R_BROCA.mp3", "quz/L_INTRO.mp3"):
        (audio / ruta).parent.mkdir(parents=True, exist_ok=True)
        (audio / ruta).write_bytes(b"ID3")
    monkeypatch.setenv("CHAKRA_AUDIO", str(audio))
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.ejemplo.org/")
    cli = nuevo_cliente()
    c = caso()
    enviar(cli, c)
    r = cli.post(f"/llamadas/{c['caso_id']}").json()
    assert urls_play(r["twiml"]) == ["https://api.ejemplo.org/audio/quz/L_INTRO.mp3",
                                     "https://api.ejemplo.org/audio/es/R_BROCA.mp3",
                                     "https://api.ejemplo.org/audio/es/R_BROCA.mp3"]
    assert r["idioma_audio"] == {"L_INTRO": "quz", "R_BROCA": "es"} and r["respaldo"] is True


def test_falta_audio_no_llama(cliente, tmp_path, monkeypatch):
    monkeypatch.setenv("CHAKRA_AUDIO", str(tmp_path / "vacio"))
    cli = nuevo_cliente()
    c = caso()
    enviar(cli, c)
    r = cli.post(f"/llamadas/{c['caso_id']}")
    assert r.status_code == 409 and "L_INTRO.mp3" in r.text
    assert cli.get("/casos").json()[0]["llamadas"] == []


def test_historial_de_llamadas_sin_telefono(cliente):
    c = caso()
    enviar(cliente, c)
    cliente.post(f"/llamadas/{c['caso_id']}")
    cliente.post(f"/llamadas/{c['caso_id']}")
    lista = cliente.get("/casos").json()
    assert [x["simulada"] for x in lista[0]["llamadas"]] == [True, True]
    assert lista[0]["ultima_llamada"] == lista[0]["llamadas"][0]["fecha"]
    assert "+51" not in json.dumps(lista) and "telefono" not in json.dumps(lista)


def test_fincas_privadas_desde_secreto(cliente, monkeypatch):
    monkeypatch.setenv("CHAKRA_FINCAS_PRIVADAS_JSON", json.dumps({"LC-005": {"telefono": "+51911111111", "idioma": "es"}}))
    cli = nuevo_cliente()
    c = caso()
    c["finca_id"] = "LC-005"
    enviar(cli, c)
    r = cli.post(f"/llamadas/{c['caso_id']}").json()
    assert r["simulada"] is True and r["respaldo"] is False and "/audio/es/R_BROCA.mp3" in r["twiml"]
    assert "+51" not in json.dumps(r)


def test_catalogo_de_audios_valido_y_completo():
    from jsonschema import Draft202012Validator
    esquema = json.loads((RAIZ / "contracts/mensajes.schema.json").read_text(encoding="utf-8"))
    catalogo = json.loads((RAIZ / "audio/mensajes.json").read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(esquema).iter_errors(catalogo))
    for codigo, m in catalogo["mensajes"].items():
        assert (RAIZ / m["archivos"]["es"]).is_file(), codigo
        assert (RAIZ / m["archivos_llamada"]["es"]).is_file(), codigo
        if m["sintetico"]:  # se rotula en el demo: la nota dice qué voz sintética es
            assert "sintétic" in m.get("nota", "").lower(), codigo
