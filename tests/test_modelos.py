import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError

from app.models import Decisao, Especie, Papel, Registro, StatusRegistro, Usuario, Validacao


def criar_base(db):
    coletor = Usuario(nome="Ana", email="ana@exemplo.com", senha_hash="x")
    validador = Usuario(
        nome="Beto", email="beto@exemplo.com", senha_hash="x", papel=Papel.VALIDADOR
    )
    especie = Especie(nome_popular="Açaí", nome_cientifico="Euterpe oleracea", familia="Arecaceae")
    db.add_all([coletor, validador, especie])
    db.commit()
    return coletor, validador, especie


def novo_registro(coletor, especie, **extra):
    dados = {
        "coletor": coletor,
        "especie": especie,
        "descricao": "Touceira na beira do igarapé",
        "uso_tradicional": "Fruto usado na alimentação",
        "latitude": -1.455833,
        "longitude": -48.503889,
        "data_coleta": date(2026, 11, 20),
    }
    dados.update(extra)
    return Registro(**dados)


def test_usuario_entra_como_coletor_por_padrao(db):
    coletor, _, _ = criar_base(db)
    assert coletor.papel == Papel.COLETOR
    assert coletor.criado_em is not None


def test_registro_novo_fica_pendente(db):
    coletor, _, especie = criar_base(db)
    registro = novo_registro(coletor, especie)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    assert registro.status == StatusRegistro.PENDENTE
    assert isinstance(registro.id, uuid.UUID)
    assert registro.atualizado_em is not None
    assert registro.deleted_at is None
    assert registro.latitude == pytest.approx(-1.455833)


def test_registro_aceita_uuid_do_aparelho(db):
    coletor, _, especie = criar_base(db)
    id_aparelho = uuid.uuid4()
    db.add(novo_registro(coletor, especie, id=id_aparelho))
    db.commit()
    assert db.get(Registro, id_aparelho) is not None


def test_uuid_repetido_nao_duplica(db):
    coletor, _, especie = criar_base(db)
    id_aparelho = uuid.uuid4()
    db.add(novo_registro(coletor, especie, id=id_aparelho))
    db.commit()
    db.expunge_all()
    db.add(novo_registro(coletor, especie, id=id_aparelho))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(90.5, 0), (-91, 0), (0, 180.5), (0, -181)],
)
def test_coordenadas_fora_do_intervalo_sao_barradas_no_banco(db, latitude, longitude):
    coletor, _, especie = criar_base(db)
    db.add(novo_registro(coletor, especie, latitude=latitude, longitude=longitude))
    with pytest.raises(IntegrityError):
        db.commit()


def test_status_invalido_e_barrado_no_banco(db):
    coletor, _, especie = criar_base(db)
    db.add(novo_registro(coletor, especie))
    db.commit()
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE registros SET status = 'aprovadissimo'"))
        db.commit()


def test_status_invalido_e_barrado_no_orm(db):
    coletor, _, especie = criar_base(db)
    db.add(novo_registro(coletor, especie, status="qualquer"))
    with pytest.raises(StatementError):
        db.commit()


def test_email_e_nome_cientifico_sao_unicos(db):
    criar_base(db)
    db.add(Usuario(nome="Outra Ana", email="ana@exemplo.com", senha_hash="x"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(Especie(nome_popular="Juçara", nome_cientifico="Euterpe oleracea"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_historico_de_validacao_do_registro(db):
    coletor, validador, especie = criar_base(db)
    registro = novo_registro(coletor, especie)
    db.add(registro)
    db.commit()
    db.add(
        Validacao(
            registro=registro,
            validador=validador,
            decisao=Decisao.REJEITADO,
            comentario="Foto não permite identificar a espécie",
        )
    )
    db.add(Validacao(registro=registro, validador=validador, decisao=Decisao.APROVADO))
    db.commit()
    db.expire_all()
    decisoes = [v.decisao for v in db.get(Registro, registro.id).validacoes]
    assert decisoes == [Decisao.REJEITADO, Decisao.APROVADO]
    assert len(coletor.registros) == 1
    assert len(validador.validacoes) == 2
