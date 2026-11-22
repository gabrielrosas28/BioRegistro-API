from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import criar_engine, get_db
from app.core.seguranca import criar_token, gerar_hash_senha
from app.main import app
from app.models import Papel, Usuario

RAIZ = Path(__file__).resolve().parent.parent
SENHA_PADRAO = "senha-segura-123"


def config_alembic(url: str) -> Config:
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def cabecalho(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {criar_token(usuario.id)}"}


@pytest.fixture(autouse=True)
def bcrypt_rapido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "bcrypt_rounds", 4)


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
def fabrica_sessao(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(fabrica_sessao: sessionmaker[Session]) -> Generator[Session, None, None]:
    sessao = fabrica_sessao()
    yield sessao
    sessao.close()


@pytest.fixture
def cliente(fabrica_sessao: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def db_de_teste() -> Generator[Session, None, None]:
        with fabrica_sessao() as sessao:
            yield sessao

    app.dependency_overrides[get_db] = db_de_teste
    with TestClient(app) as cliente_teste:
        yield cliente_teste
    app.dependency_overrides.clear()


@pytest.fixture
def criar_usuario(db: Session) -> Callable[..., Usuario]:
    def criar(
        email: str, papel: Papel = Papel.COLETOR, senha: str = SENHA_PADRAO, nome: str = "Teste"
    ) -> Usuario:
        usuario = Usuario(nome=nome, email=email, senha_hash=gerar_hash_senha(senha), papel=papel)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    return criar


@pytest.fixture
def admin(criar_usuario: Callable[..., Usuario]) -> Usuario:
    return criar_usuario("admin@exemplo.com", Papel.ADMIN, nome="Administração")


@pytest.fixture
def coletor(criar_usuario: Callable[..., Usuario]) -> Usuario:
    return criar_usuario("coletor@exemplo.com", Papel.COLETOR, nome="Ana Coletora")


@pytest.fixture
def validador(criar_usuario: Callable[..., Usuario]) -> Usuario:
    return criar_usuario("validador@exemplo.com", Papel.VALIDADOR, nome="Beto Validador")
