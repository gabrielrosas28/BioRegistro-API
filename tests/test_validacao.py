import uuid

import pytest

from app.models import Papel
from tests.conftest import cabecalho, criar_registro, dados_registro

COMENTARIO = "A foto não permite confirmar a espécie"


def validar(cliente, usuario, registro_id, **corpo):
    return cliente.post(
        f"/registros/{registro_id}/validacao", json=corpo, headers=cabecalho(usuario)
    )


@pytest.fixture
def pendente(cliente, coletor, acai):
    return criar_registro(cliente, coletor, acai)


def test_validador_aprova(cliente, validador, pendente):
    resposta = validar(cliente, validador, pendente["id"], decisao="aprovado")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "validado"
    assert corpo["atualizado_em"] > pendente["atualizado_em"]
    [validacao] = corpo["validacoes"]
    assert validacao["decisao"] == "aprovado"
    assert validacao["comentario"] is None
    assert validacao["validador"] == {"id": validador.id, "nome": validador.nome}


def test_validador_rejeita_com_comentario(cliente, validador, pendente):
    resposta = validar(
        cliente, validador, pendente["id"], decisao="rejeitado", comentario=f"  {COMENTARIO}  "
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["validacoes"][0]["comentario"] == COMENTARIO


def test_aprovacao_aceita_comentario_opcional(cliente, validador, pendente):
    resposta = validar(cliente, validador, pendente["id"], decisao="aprovado", comentario="Ok")
    assert resposta.json()["validacoes"][0]["comentario"] == "Ok"


def test_comentario_vazio_na_aprovacao_vira_nulo(cliente, validador, pendente):
    resposta = validar(cliente, validador, pendente["id"], decisao="aprovado", comentario="  ")
    assert resposta.json()["validacoes"][0]["comentario"] is None


@pytest.mark.parametrize("comentario", [None, "", "curto", "123456789", "   curto      "])
def test_rejeicao_sem_comentario_suficiente_devolve_422(
    cliente, validador, pendente, comentario
):
    corpo = {"decisao": "rejeitado"}
    if comentario is not None:
        corpo["comentario"] = comentario
    resposta = validar(cliente, validador, pendente["id"], **corpo)
    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", "comentario"]
    assert cliente.get(
        f"/registros/{pendente['id']}", headers=cabecalho(validador)
    ).json()["status"] == "pendente"


def test_comentario_com_dez_caracteres_e_aceito(cliente, validador, pendente):
    resposta = validar(
        cliente, validador, pendente["id"], decisao="rejeitado", comentario="1234567890"
    )
    assert resposta.status_code == 201


def test_decisao_invalida_devolve_422(cliente, validador, pendente):
    assert validar(cliente, validador, pendente["id"], decisao="talvez").status_code == 422


@pytest.mark.parametrize("papel", [Papel.COLETOR, Papel.ADMIN])
def test_so_validador_valida(cliente, criar_usuario, pendente, papel):
    usuario = criar_usuario(f"{papel}@teste.com", papel)
    resposta = validar(cliente, usuario, pendente["id"], decisao="aprovado")
    assert resposta.status_code == 403


def test_validar_exige_login(cliente, pendente):
    resposta = cliente.post(f"/registros/{pendente['id']}/validacao", json={"decisao": "aprovado"})
    assert resposta.status_code == 401


def test_validador_nao_valida_o_proprio_registro(cliente, validador, acai):
    proprio = criar_registro(cliente, validador, acai)
    resposta = validar(cliente, validador, proprio["id"], decisao="aprovado")
    assert resposta.status_code == 403
    assert "ele mesmo" in resposta.json()["detail"]
    detalhe = cliente.get(f"/registros/{proprio['id']}", headers=cabecalho(validador)).json()
    assert detalhe["status"] == "pendente"
    assert detalhe["validacoes"] == []


def test_outro_validador_valida_registro_de_validador(cliente, validador, criar_usuario, acai):
    proprio = criar_registro(cliente, validador, acai)
    colega = criar_usuario("colega@exemplo.com", Papel.VALIDADOR)
    assert validar(cliente, colega, proprio["id"], decisao="aprovado").status_code == 201


def test_registro_ja_decidido_devolve_409(cliente, validador, criar_usuario, pendente):
    assert validar(cliente, validador, pendente["id"], decisao="aprovado").status_code == 201
    colega = criar_usuario("colega@exemplo.com", Papel.VALIDADOR)
    resposta = validar(
        cliente, colega, pendente["id"], decisao="rejeitado", comentario=COMENTARIO
    )
    assert resposta.status_code == 409
    detalhe = cliente.get(f"/registros/{pendente['id']}").json()
    assert detalhe["status"] == "validado"
    assert len(detalhe["validacoes"]) == 1


def test_validar_registro_inexistente_ou_excluido(cliente, coletor, validador, pendente):
    assert validar(cliente, validador, uuid.uuid4(), decisao="aprovado").status_code == 404
    cliente.delete(f"/registros/{pendente['id']}", headers=cabecalho(coletor))
    assert validar(cliente, validador, pendente["id"], decisao="aprovado").status_code == 404


def test_validado_aparece_para_visitante_com_historico(cliente, validador, pendente):
    validar(cliente, validador, pendente["id"], decisao="aprovado")
    assert cliente.get("/registros").json()["total"] == 1
    detalhe = cliente.get(f"/registros/{pendente['id']}").json()
    assert detalhe["validacoes"][0]["validador"]["nome"] == validador.nome


def test_rejeitado_pode_ser_reenviado_como_novo_registro(
    cliente, coletor, validador, pendente, acai
):
    validar(cliente, validador, pendente["id"], decisao="rejeitado", comentario=COMENTARIO)
    novo = criar_registro(cliente, coletor, acai, descricao="Nova foto, cacho mais visível")
    assert novo["id"] != pendente["id"]
    assert novo["status"] == "pendente"
    antigo = cliente.get(f"/registros/{pendente['id']}", headers=cabecalho(coletor)).json()
    assert antigo["status"] == "rejeitado"
    assert cliente.put(
        f"/registros/{pendente['id']}", json=dados_registro(acai), headers=cabecalho(coletor)
    ).status_code == 409
