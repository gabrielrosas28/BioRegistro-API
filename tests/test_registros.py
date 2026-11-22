import uuid
from datetime import datetime, timedelta

import pytest

from app.models import Papel, Registro, StatusRegistro
from app.schemas.registro import hoje_utc
from tests.conftest import cabecalho, criar_registro, dados_registro


def definir_status(db, registro_id, status):
    registro = db.get(Registro, uuid.UUID(registro_id))
    registro.status = status
    db.commit()


def campos_com_erro(resposta):
    return {erro["loc"][-1] for erro in resposta.json()["detail"]}


def test_coletor_cria_registro_pendente(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai)
    assert corpo["status"] == "pendente"
    assert uuid.UUID(corpo["id"])
    assert corpo["coletor"] == {"id": coletor.id, "nome": coletor.nome}
    assert corpo["especie"]["nome_cientifico"] == "Euterpe oleracea"
    assert corpo["validacoes"] == []
    assert corpo["foto_url"] is None


def test_datas_saem_em_utc(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai)
    for campo in ("criado_em", "atualizado_em"):
        assert datetime.fromisoformat(corpo[campo]).utcoffset() == timedelta(0)


def test_status_enviado_pelo_cliente_e_ignorado(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, status="validado")
    assert corpo["status"] == "pendente"


def test_registro_usa_uuid_do_aparelho(cliente, coletor, acai):
    id_aparelho = str(uuid.uuid4())
    corpo = criar_registro(cliente, coletor, acai, id=id_aparelho)
    assert corpo["id"] == id_aparelho


def test_uuid_repetido_devolve_409(cliente, coletor, acai):
    id_aparelho = str(uuid.uuid4())
    criar_registro(cliente, coletor, acai, id=id_aparelho)
    resposta = cliente.post(
        "/registros",
        json=dados_registro(acai, id=id_aparelho),
        headers=cabecalho(coletor),
    )
    assert resposta.status_code == 409


def test_criar_exige_login(cliente, acai):
    assert cliente.post("/registros", json=dados_registro(acai)).status_code == 401


def test_validador_tambem_registra_observacoes(cliente, validador, acai):
    assert criar_registro(cliente, validador, acai)["coletor"]["id"] == validador.id


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("latitude", 90.1), ("latitude", -90.5), ("longitude", 180.1), ("longitude", -181)],
)
def test_coordenadas_invalidas_devolvem_422(cliente, coletor, acai, campo, valor):
    resposta = cliente.post(
        "/registros", json=dados_registro(acai, **{campo: valor}), headers=cabecalho(coletor)
    )
    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == {campo}


def test_limites_das_coordenadas_sao_aceitos(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, latitude=-90, longitude=180)
    assert (corpo["latitude"], corpo["longitude"]) == (-90, 180)


def test_coordenada_arredondada_em_seis_casas(cliente, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, latitude=-1.45583349, longitude=-48.5038886)
    assert (corpo["latitude"], corpo["longitude"]) == (-1.455833, -48.503889)


def test_data_futura_devolve_422(cliente, coletor, acai):
    amanha = (hoje_utc() + timedelta(days=1)).isoformat()
    resposta = cliente.post(
        "/registros", json=dados_registro(acai, data_coleta=amanha), headers=cabecalho(coletor)
    )
    assert resposta.status_code == 422
    assert campos_com_erro(resposta) == {"data_coleta"}


def test_data_de_hoje_e_aceita(cliente, coletor, acai):
    assert criar_registro(cliente, coletor, acai, data_coleta=hoje_utc().isoformat())


def test_especie_inexistente_devolve_422(cliente, coletor, acai):
    resposta = cliente.post(
        "/registros", json=dados_registro(acai, especie_id=999), headers=cabecalho(coletor)
    )
    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "Espécie não encontrada"}


@pytest.mark.parametrize("campo", ["descricao", "uso_tradicional"])
def test_textos_em_branco_devolvem_422(cliente, coletor, acai, campo):
    resposta = cliente.post(
        "/registros", json=dados_registro(acai, **{campo: "   "}), headers=cabecalho(coletor)
    )
    assert resposta.status_code == 422


def test_dono_edita_registro_pendente(cliente, coletor, acai, andiroba):
    original = criar_registro(cliente, coletor, acai)
    novo = dados_registro(andiroba, descricao="Árvore adulta", latitude=-3.1, longitude=-60.0)
    resposta = cliente.put(f"/registros/{original['id']}", json=novo, headers=cabecalho(coletor))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["especie"]["id"] == andiroba.id
    assert corpo["descricao"] == "Árvore adulta"
    assert (corpo["latitude"], corpo["longitude"]) == (-3.1, -60.0)
    assert corpo["status"] == "pendente"
    assert corpo["atualizado_em"] > original["atualizado_em"]
    assert corpo["criado_em"] == original["criado_em"]


def test_edicao_valida_os_dados(cliente, coletor, acai):
    registro = criar_registro(cliente, coletor, acai)
    resposta = cliente.put(
        f"/registros/{registro['id']}",
        json=dados_registro(acai, latitude=95),
        headers=cabecalho(coletor),
    )
    assert resposta.status_code == 422


def test_outro_coletor_nao_ve_nem_edita_registro_pendente(cliente, coletor, criar_usuario, acai):
    registro = criar_registro(cliente, coletor, acai)
    intruso = criar_usuario("intruso@exemplo.com")
    url = f"/registros/{registro['id']}"
    assert cliente.put(url, json=dados_registro(acai), headers=cabecalho(intruso)).status_code == 404
    assert cliente.delete(url, headers=cabecalho(intruso)).status_code == 404


def test_quem_ve_o_registro_mas_nao_e_dono_recebe_403(cliente, coletor, validador, acai):
    registro = criar_registro(cliente, coletor, acai)
    url = f"/registros/{registro['id']}"
    resposta = cliente.put(url, json=dados_registro(acai), headers=cabecalho(validador))
    assert resposta.status_code == 403
    assert cliente.delete(url, headers=cabecalho(validador)).status_code == 403


@pytest.mark.parametrize("status", [StatusRegistro.VALIDADO, StatusRegistro.REJEITADO])
def test_registro_decidido_nao_pode_ser_editado_nem_excluido(cliente, db, coletor, acai, status):
    registro = criar_registro(cliente, coletor, acai)
    definir_status(db, registro["id"], status)
    url = f"/registros/{registro['id']}"
    resposta = cliente.put(url, json=dados_registro(acai), headers=cabecalho(coletor))
    assert resposta.status_code == 409
    assert cliente.delete(url, headers=cabecalho(coletor)).status_code == 409


def test_editar_registro_inexistente(cliente, coletor, acai):
    resposta = cliente.put(
        f"/registros/{uuid.uuid4()}", json=dados_registro(acai), headers=cabecalho(coletor)
    )
    assert resposta.status_code == 404


def test_exclusao_e_logica(cliente, db, coletor, acai):
    registro = criar_registro(cliente, coletor, acai)
    url = f"/registros/{registro['id']}"
    resposta = cliente.delete(url, headers=cabecalho(coletor))
    assert resposta.status_code == 204
    assert resposta.content == b""
    assert cliente.get(url, headers=cabecalho(coletor)).status_code == 404
    assert cliente.get("/registros", headers=cabecalho(coletor)).json()["total"] == 0
    assert cliente.delete(url, headers=cabecalho(coletor)).status_code == 404
    db.expire_all()
    no_banco = db.get(Registro, uuid.UUID(registro["id"]))
    assert no_banco.deleted_at is not None
    assert no_banco.atualizado_em >= no_banco.deleted_at


@pytest.fixture
def cenario(cliente, db, coletor, validador, criar_usuario, acai, andiroba):
    outro = criar_usuario("outro@exemplo.com", nome="Outro Coletor")
    registros = {
        "pendente_coletor": criar_registro(cliente, coletor, acai, data_coleta="2026-10-01"),
        "validado_coletor": criar_registro(cliente, coletor, andiroba, data_coleta="2026-10-15"),
        "pendente_outro": criar_registro(cliente, outro, acai, data_coleta="2026-11-01"),
        "validado_outro": criar_registro(cliente, outro, acai, data_coleta="2026-11-10"),
        "rejeitado_outro": criar_registro(cliente, outro, andiroba, data_coleta="2026-11-15"),
    }
    definir_status(db, registros["validado_coletor"]["id"], StatusRegistro.VALIDADO)
    definir_status(db, registros["validado_outro"]["id"], StatusRegistro.VALIDADO)
    definir_status(db, registros["rejeitado_outro"]["id"], StatusRegistro.REJEITADO)
    return {nome: r["id"] for nome, r in registros.items()} | {"outro": outro}


def ids_listados(cliente, usuario=None, **params):
    headers = cabecalho(usuario) if usuario else {}
    resposta = cliente.get("/registros", params=params, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return {r["id"] for r in resposta.json()["itens"]}


def test_visitante_so_ve_validados(cliente, cenario):
    assert ids_listados(cliente) == {cenario["validado_coletor"], cenario["validado_outro"]}
    assert ids_listados(cliente, status="pendente") == set()


def test_coletor_ve_validados_e_os_proprios(cliente, coletor, cenario):
    assert ids_listados(cliente, coletor) == {
        cenario["pendente_coletor"],
        cenario["validado_coletor"],
        cenario["validado_outro"],
    }


@pytest.mark.parametrize("papel", [Papel.VALIDADOR, Papel.ADMIN])
def test_validador_e_admin_veem_todos(cliente, criar_usuario, cenario, papel):
    usuario = criar_usuario(f"{papel}@teste.com", papel)
    assert len(ids_listados(cliente, usuario)) == 5


def test_filtros_da_listagem(cliente, validador, cenario, acai, andiroba):
    assert ids_listados(cliente, validador, status="pendente") == {
        cenario["pendente_coletor"],
        cenario["pendente_outro"],
    }
    assert ids_listados(cliente, validador, especie_id=andiroba.id) == {
        cenario["validado_coletor"],
        cenario["rejeitado_outro"],
    }
    assert ids_listados(cliente, validador, coletor_id=cenario["outro"].id) == {
        cenario["pendente_outro"],
        cenario["validado_outro"],
        cenario["rejeitado_outro"],
    }
    assert ids_listados(
        cliente, validador, data_inicio="2026-10-15", data_fim="2026-11-10"
    ) == {cenario["validado_coletor"], cenario["pendente_outro"], cenario["validado_outro"]}
    assert ids_listados(
        cliente, validador, status="validado", especie_id=acai.id
    ) == {cenario["validado_outro"]}


def test_paginacao(cliente, validador, cenario):
    vistos = []
    for pagina in (1, 2, 3):
        resposta = cliente.get(
            "/registros", params={"pagina": pagina, "tamanho": 2}, headers=cabecalho(validador)
        ).json()
        assert resposta["total"] == 5
        assert (resposta["pagina"], resposta["tamanho"]) == (pagina, 2)
        vistos += [r["id"] for r in resposta["itens"]]
    assert len(vistos) == len(set(vistos)) == 5
    assert vistos[0] == cenario["rejeitado_outro"]


@pytest.mark.parametrize(
    "params",
    [
        {"tamanho": 101},
        {"tamanho": 0},
        {"pagina": 0},
        {"status": "aprovado"},
        {"data_inicio": "2026-11-10", "data_fim": "2026-11-01"},
    ],
)
def test_parametros_invalidos_da_listagem(cliente, params):
    assert cliente.get("/registros", params=params).status_code == 422


def test_token_invalido_em_rota_publica_devolve_401(cliente):
    resposta = cliente.get("/registros", headers={"Authorization": "Bearer lixo"})
    assert resposta.status_code == 401


def test_visitante_nao_ve_detalhe_de_pendente(cliente, coletor, cenario):
    assert cliente.get(f"/registros/{cenario['pendente_coletor']}").status_code == 404
    url = f"/registros/{cenario['pendente_coletor']}"
    assert cliente.get(url, headers=cabecalho(coletor)).status_code == 200


def test_detalhe_publico_de_validado_nao_expoe_email(cliente, cenario):
    resposta = cliente.get(f"/registros/{cenario['validado_outro']}")
    assert resposta.status_code == 200
    assert "email" not in resposta.json()["coletor"]


def test_detalhe_de_id_invalido(cliente):
    assert cliente.get("/registros/nao-e-uuid").status_code == 422
    assert cliente.get(f"/registros/{uuid.uuid4()}").status_code == 404
