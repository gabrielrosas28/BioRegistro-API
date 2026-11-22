from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.core.database import Base, criar_engine
from tests.conftest import config_alembic

TABELAS = {"usuarios", "especies", "registros", "validacoes"}


def test_upgrade_cria_todas_as_tabelas(engine):
    tabelas = set(inspect(engine).get_table_names())
    assert TABELAS <= tabelas


def test_migracao_igual_aos_modelos(engine):
    with engine.connect() as conexao:
        contexto = MigrationContext.configure(conexao)
        diferencas = compare_metadata(contexto, Base.metadata)
    assert diferencas == []


def test_colunas_de_registros(engine):
    colunas = {c["name"] for c in inspect(engine).get_columns("registros")}
    assert colunas == {
        "id",
        "coletor_id",
        "especie_id",
        "descricao",
        "uso_tradicional",
        "latitude",
        "longitude",
        "foto_url",
        "status",
        "data_coleta",
        "criado_em",
        "atualizado_em",
        "deleted_at",
    }


def test_downgrade_remove_as_tabelas(url_banco):
    cfg = config_alembic(url_banco)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    eng = criar_engine(url_banco)
    tabelas = set(inspect(eng).get_table_names())
    eng.dispose()
    assert tabelas.isdisjoint(TABELAS)
