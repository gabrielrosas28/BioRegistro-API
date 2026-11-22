from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import criar_engine

RAIZ = Path(__file__).resolve().parent.parent


def config_alembic(url: str) -> Config:
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def url_banco(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'teste.db').as_posix()}"


@pytest.fixture
def engine(url_banco: str) -> Generator[Engine, None, None]:
    command.upgrade(config_alembic(url_banco), "head")
    eng = criar_engine(url_banco)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    sessao = sessionmaker(bind=engine, expire_on_commit=False)()
    yield sessao
    sessao.close()
