import uuid

import pytest

from app.models import Registro, StatusRegistro
from tests.conftest import cabecalho, criar_registro

CENTRO = {"lat": -1.455833, "lon": -48.503889}


def em(lat, lon):
    return {"latitude": lat, "longitude": lon}


def validar(db, *registros):
    for corpo in registros:
        db.get(Registro, uuid.UUID(corpo["id"])).status = StatusRegistro.VALIDADO
    db.commit()


def buscar(cliente, usuario=None, **params):
    headers = cabecalho(usuario) if usuario is not None else {}
    return cliente.get("/registros/proximos", params={**CENTRO, **params}, headers=headers)


def test_devolve_so_os_registros_dentro_do_raio_em_ordem(cliente, db, coletor, acai):
    longe = criar_registro(cliente, coletor, acai, **em(-1.455833, -48.10))
    perto = criar_registro(cliente, coletor, acai, **em(-1.46, -48.50))
    meio = criar_registro(cliente, coletor, acai, **em(-1.50, -48.45))
    fora = criar_registro(cliente, coletor, acai, **em(-3.119028, -60.021731))
    validar(db, longe, perto, meio, fora)

    resposta = buscar(cliente, raio_km=50)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [r["id"] for r in corpo] == [perto["id"], meio["id"], longe["id"]]
    distancias = [r["distancia_km"] for r in corpo]
    assert distancias == sorted(distancias)
    assert distancias[0] == pytest.approx(0.6, abs=0.1)
    assert distancias[-1] == pytest.approx(44.9, abs=0.2)
    assert corpo[0]["especie"]["nome_popular"] == "Açaí"


def test_canto_da_caixa_fora_do_raio_nao_entra(cliente, db, coletor, acai):
    canto = criar_registro(cliente, coletor, acai, **em(0.7, 0.7))
    validar(db, canto)
    resposta = cliente.get("/registros/proximos", params={"lat": 0, "lon": 0, "raio_km": 100})
    assert resposta.json() == []


def test_visitante_so_ve_validados(cliente, db, coletor, acai):
    validado = criar_registro(cliente, coletor, acai)
    criar_registro(cliente, coletor, acai)
    validar(db, validado)
    assert [r["id"] for r in buscar(cliente, raio_km=1).json()] == [validado["id"]]


def test_coletor_ve_os_proprios_pendentes(cliente, criar_usuario, coletor, acai):
    outro = criar_usuario("outro@exemplo.com")
    meu = criar_registro(cliente, coletor, acai)
    criar_registro(cliente, outro, acai)
    assert [r["id"] for r in buscar(cliente, coletor, raio_km=1).json()] == [meu["id"]]


def test_validador_ve_todos(cliente, criar_usuario, validador, coletor, acai):
    outro = criar_usuario("outro@exemplo.com")
    criar_registro(cliente, coletor, acai)
    criar_registro(cliente, outro, acai)
    assert len(buscar(cliente, validador, raio_km=1).json()) == 2


def test_excluidos_nao_aparecem(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai)
    cliente.delete(f"/registros/{corpo['id']}", headers=cabecalho(coletor))
    assert buscar(cliente, coletor, raio_km=1).json() == []


def test_limite(cliente, db, coletor, acai):
    registros = [
        criar_registro(cliente, coletor, acai, **em(-1.455833 + i / 1000, -48.503889))
        for i in range(5)
    ]
    validar(db, *registros)
    corpo = buscar(cliente, raio_km=10, limite=2).json()
    assert [r["id"] for r in corpo] == [registros[0]["id"], registros[1]["id"]]


def test_busca_atravessando_o_antimeridiano(cliente, db, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, **em(-16.5, 179.95))
    validar(db, corpo)
    resposta = cliente.get(
        "/registros/proximos", params={"lat": -16.5, "lon": -179.95, "raio_km": 20}
    )
    assert [r["id"] for r in resposta.json()] == [corpo["id"]]
    assert resposta.json()[0]["distancia_km"] == pytest.approx(10.66, abs=0.05)


def test_busca_perto_do_polo(cliente, db, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, **em(-89.95, 180))
    validar(db, corpo)
    resposta = cliente.get("/registros/proximos", params={"lat": -89.9, "lon": 0, "raio_km": 20})
    assert [r["id"] for r in resposta.json()] == [corpo["id"]]
    assert resposta.json()[0]["distancia_km"] == pytest.approx(16.68, abs=0.05)


def test_rota_nao_e_confundida_com_o_id(cliente):
    resposta = cliente.get("/registros/proximos", params={**CENTRO, "raio_km": 5})
    assert resposta.status_code == 200
    assert resposta.json() == []


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 91, "lon": 0, "raio_km": 1},
        {"lat": 0, "lon": -181, "raio_km": 1},
        {"lat": 0, "lon": 0, "raio_km": 0},
        {"lat": 0, "lon": 0, "raio_km": 20001},
        {"lat": 0, "lon": 0},
        {"lat": 0, "lon": 0, "raio_km": 1, "limite": 0},
        {"lat": 0, "lon": 0, "raio_km": 1, "limite": 501},
        {"lat": "abc", "lon": 0, "raio_km": 1},
    ],
)
def test_parametros_invalidos(cliente, params):
    assert cliente.get("/registros/proximos", params=params).status_code == 422
