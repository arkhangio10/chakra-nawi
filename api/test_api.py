"""python -m pytest api -q"""
import copy
import json
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = json.loads((RAIZ / "contracts/caso.example.json").read_text(encoding="utf-8"))


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAKRA_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("CHAKRA_FOTOS", str(tmp_path / "fotos"))
    privado = tmp_path / "privado.json"
    privado.write_text(json.dumps({"LC-001": {"telefono": "+51900000000", "idioma": "quz"}}))
    monkeypatch.setenv("CHAKRA_FINCAS_PRIVADAS", str(privado))
    for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"):
        monkeypatch.delenv(v, raising=False)
    import importlib

    import api.app as modulo
    importlib.reload(modulo)
    from fastapi.testclient import TestClient
    return TestClient(modulo.app)


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
