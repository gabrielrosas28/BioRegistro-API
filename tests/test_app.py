from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_health():
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_documentacao_disponivel():
    assert cliente.get("/docs").status_code == 200
    assert cliente.get("/redoc").status_code == 200
    assert cliente.get("/openapi.json").json()["info"]["title"] == "BioRegistro API"
