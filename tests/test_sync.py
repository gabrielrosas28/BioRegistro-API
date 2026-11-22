import uuid
from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.models import Registro, StatusRegistro
from tests.conftest import cabecalho, criar_registro, dados_registro


def item(especie, **extra):
    return {"id": str(uuid.uuid4()), **dados_registro(especie), **extra}


def enviar(cliente, usuario, itens):
    return cliente.post("/sync/registros", json={"registros": itens}, headers=cabecalho(usuario))


def alteracoes(cliente, usuario, desde=None):
    params = {"desde": desde} if desde is not None else {}
    return cliente.get("/sync/registros", params=params, headers=cabecalho(usuario))


def total_registros(db):
    return db.scalar(select(func.count()).select_from(Registro))


def envelhecer(db, minutos=10):
    passado = datetime.now(UTC) - timedelta(minutes=minutos)
    db.execute(update(Registro).values(criado_em=passado, atualizado_em=passado))
    db.commit()


def test_lote_cria_registros_com_o_uuid_do_aparelho(cliente, db, coletor, acai):
    itens = [item(acai), item(acai, latitude=-2.0)]
    resposta = enviar(cliente, coletor, itens)
    assert resposta.status_code == 200
    assert resposta.json() == {
        "criados": [itens[0]["id"], itens[1]["id"]],
        "ignorados": [],
        "erros": [],
    }
    registro = db.get(Registro, uuid.UUID(itens[1]["id"]))
    assert registro.status == StatusRegistro.PENDENTE
    assert registro.coletor_id == coletor.id
    assert registro.latitude == -2.0


def test_reenviar_o_mesmo_lote_nao_duplica(cliente, db, coletor, acai):
    itens = [item(acai), item(acai), item(acai)]
    enviar(cliente, coletor, itens)
    resposta = enviar(cliente, coletor, itens)
    assert resposta.status_code == 200
    assert resposta.json() == {
        "criados": [],
        "ignorados": [i["id"] for i in itens],
        "erros": [],
    }
    assert total_registros(db) == 3


def test_lote_parcialmente_reenviado(cliente, db, coletor, acai):
    antigo, novo = item(acai), item(acai)
    enviar(cliente, coletor, [antigo])
    resposta = enviar(cliente, coletor, [antigo, novo])
    assert resposta.json()["criados"] == [novo["id"]]
    assert resposta.json()["ignorados"] == [antigo["id"]]
    assert total_registros(db) == 2


def test_uuid_repetido_dentro_do_lote(cliente, db, coletor, acai):
    repetido = item(acai)
    resposta = enviar(cliente, coletor, [repetido, {**repetido, "descricao": "Outra versão"}])
    assert resposta.json()["criados"] == [repetido["id"]]
    assert resposta.json()["ignorados"] == [repetido["id"]]
    assert db.get(Registro, uuid.UUID(repetido["id"])).descricao != "Outra versão"


def test_uuid_de_outro_coletor_nao_e_sobrescrito(cliente, db, criar_usuario, coletor, acai):
    outro = criar_usuario("outro@exemplo.com")
    existente = criar_registro(cliente, outro, acai, id=str(uuid.uuid4()))
    resposta = enviar(cliente, coletor, [item(acai, id=existente["id"], descricao="Invasão")])
    assert resposta.json()["ignorados"] == [existente["id"]]
    registro = db.get(Registro, uuid.UUID(existente["id"]))
    assert registro.coletor_id == outro.id
    assert registro.descricao != "Invasão"


def test_uuid_de_registro_excluido_nao_volta(cliente, db, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai, id=str(uuid.uuid4()))
    cliente.delete(f"/registros/{corpo['id']}", headers=cabecalho(coletor))
    resposta = enviar(cliente, coletor, [item(acai, id=corpo["id"])])
    assert resposta.json()["ignorados"] == [corpo["id"]]
    assert db.get(Registro, uuid.UUID(corpo["id"])).deleted_at is not None


def test_especie_inexistente_nao_trava_o_lote(cliente, db, coletor, acai):
    bom, ruim = item(acai), {**item(acai), "especie_id": 999}
    resposta = enviar(cliente, coletor, [ruim, bom])
    assert resposta.status_code == 200
    assert resposta.json() == {
        "criados": [bom["id"]],
        "ignorados": [],
        "erros": [{"id": ruim["id"], "motivo": "Espécie não encontrada"}],
    }
    assert total_registros(db) == 1


def test_item_invalido_recusa_o_lote(cliente, db, coletor, acai):
    resposta = enviar(cliente, coletor, [item(acai), item(acai, latitude=95)])
    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", "registros", 1, "latitude"]
    assert total_registros(db) == 0


def test_lote_exige_uuid(cliente, coletor, acai):
    resposta = enviar(cliente, coletor, [dados_registro(acai)])
    assert resposta.status_code == 422


def test_lote_vazio_ou_grande_demais(cliente, coletor, acai):
    assert enviar(cliente, coletor, []).status_code == 422
    assert enviar(cliente, coletor, [item(acai) for _ in range(501)]).status_code == 422


def test_lote_de_500_registros(cliente, db, coletor, acai):
    resposta = enviar(cliente, coletor, [item(acai) for _ in range(500)])
    assert len(resposta.json()["criados"]) == 500
    assert total_registros(db) == 500


def test_sync_exige_login(cliente, acai):
    assert cliente.post("/sync/registros", json={"registros": [item(acai)]}).status_code == 401
    assert cliente.get("/sync/registros").status_code == 401


def test_primeira_sincronizacao_devolve_tudo_que_o_usuario_ve(
    cliente, db, criar_usuario, coletor, acai
):
    outro = criar_usuario("outro@exemplo.com")
    meu = criar_registro(cliente, coletor, acai)
    validado_de_outro = criar_registro(cliente, outro, acai)
    criar_registro(cliente, outro, acai)
    db.get(Registro, uuid.UUID(validado_de_outro["id"])).status = StatusRegistro.VALIDADO
    db.commit()

    resposta = alteracoes(cliente, coletor)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert {r["id"] for r in corpo["alterados"]} == {meu["id"], validado_de_outro["id"]}
    assert corpo["excluidos"] == []
    sincronizado = datetime.fromisoformat(corpo["sincronizado_em"])
    assert sincronizado.utcoffset() == timedelta(0)
    assert abs(datetime.now(UTC) - sincronizado) < timedelta(seconds=30)


def test_devolve_so_o_que_mudou_desde_a_data(cliente, db, coletor, acai):
    criar_registro(cliente, coletor, acai)
    envelhecer(db)
    desde = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    novo = criar_registro(cliente, coletor, acai)
    corpo = alteracoes(cliente, coletor, desde).json()
    assert [r["id"] for r in corpo["alterados"]] == [novo["id"]]


def test_edicao_e_validacao_aparecem_como_alteracao(cliente, db, coletor, validador, acai):
    editado = criar_registro(cliente, coletor, acai)
    validado = criar_registro(cliente, coletor, acai)
    criar_registro(cliente, coletor, acai)
    envelhecer(db)
    desde = alteracoes(cliente, coletor).json()["sincronizado_em"]

    cliente.put(
        f"/registros/{editado['id']}",
        json=dados_registro(acai, descricao="Descrição corrigida em campo"),
        headers=cabecalho(coletor),
    )
    cliente.post(
        f"/registros/{validado['id']}/validacao",
        json={"decisao": "rejeitado", "comentario": "Foto sem o fruto visível"},
        headers=cabecalho(validador),
    )

    corpo = alteracoes(cliente, coletor, desde).json()
    por_id = {r["id"]: r for r in corpo["alterados"]}
    assert set(por_id) == {editado["id"], validado["id"]}
    assert por_id[editado["id"]]["descricao"] == "Descrição corrigida em campo"
    assert por_id[validado["id"]]["status"] == "rejeitado"
    assert por_id[validado["id"]]["validacoes"][0]["comentario"] == "Foto sem o fruto visível"


def test_exclusoes_sao_informadas(cliente, db, coletor, acai):
    corpo = criar_registro(cliente, coletor, acai)
    envelhecer(db)
    desde = alteracoes(cliente, coletor).json()["sincronizado_em"]
    cliente.delete(f"/registros/{corpo['id']}", headers=cabecalho(coletor))

    resposta = alteracoes(cliente, coletor, desde).json()
    assert resposta["alterados"] == []
    assert [e["id"] for e in resposta["excluidos"]] == [corpo["id"]]
    assert datetime.fromisoformat(resposta["excluidos"][0]["excluido_em"]) >= (
        datetime.fromisoformat(desde)
    )


def test_exclusao_de_outro_coletor_nao_aparece(cliente, db, criar_usuario, coletor, acai):
    outro = criar_usuario("outro@exemplo.com")
    corpo = criar_registro(cliente, outro, acai)
    desde = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    cliente.delete(f"/registros/{corpo['id']}", headers=cabecalho(outro))
    assert alteracoes(cliente, coletor, desde).json()["excluidos"] == []
    assert len(alteracoes(cliente, outro, desde).json()["excluidos"]) == 1


def test_pendente_de_outro_coletor_nao_aparece(cliente, criar_usuario, coletor, validador, acai):
    outro = criar_usuario("outro@exemplo.com")
    criar_registro(cliente, outro, acai)
    assert alteracoes(cliente, coletor).json()["alterados"] == []
    assert len(alteracoes(cliente, validador).json()["alterados"]) == 1


def test_nada_novo_depois_de_sincronizar(cliente, db, coletor, acai):
    criar_registro(cliente, coletor, acai)
    envelhecer(db)
    desde = alteracoes(cliente, coletor).json()["sincronizado_em"]
    corpo = alteracoes(cliente, coletor, desde).json()
    assert corpo["alterados"] == []
    assert corpo["excluidos"] == []


def test_desde_sem_fuso_e_lido_como_utc(cliente, db, coletor, acai):
    criar_registro(cliente, coletor, acai)
    envelhecer(db, minutos=120)
    uma_hora_atras = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)
    assert alteracoes(cliente, coletor, uma_hora_atras.isoformat()).json()["alterados"] == []
    tres_horas_atras = uma_hora_atras - timedelta(hours=2)
    assert len(alteracoes(cliente, coletor, tres_horas_atras.isoformat()).json()["alterados"]) == 1


def test_desde_com_outro_fuso(cliente, db, coletor, acai):
    criar_registro(cliente, coletor, acai)
    envelhecer(db, minutos=120)
    belem = datetime.now(UTC).astimezone(timezone(timedelta(hours=-3)))
    desde = (belem - timedelta(hours=1)).isoformat()
    assert alteracoes(cliente, coletor, desde).json()["alterados"] == []


def test_desde_invalido(cliente, coletor):
    assert alteracoes(cliente, coletor, "ontem").status_code == 422


def test_ciclo_completo_offline(cliente, db, coletor, validador, acai):
    lote = [item(acai), item(acai)]
    assert enviar(cliente, coletor, lote).json()["criados"] == [i["id"] for i in lote]
    primeira = alteracoes(cliente, coletor).json()
    assert {r["id"] for r in primeira["alterados"]} == {i["id"] for i in lote}

    envelhecer(db)
    desde = alteracoes(cliente, coletor).json()["sincronizado_em"]
    cliente.post(
        f"/registros/{lote[0]['id']}/validacao",
        json={"decisao": "aprovado"},
        headers=cabecalho(validador),
    )
    assert enviar(cliente, coletor, lote).json()["ignorados"] == [i["id"] for i in lote]

    segunda = alteracoes(cliente, coletor, desde).json()
    assert [(r["id"], r["status"]) for r in segunda["alterados"]] == [(lote[0]["id"], "validado")]
    assert total_registros(db) == 2
