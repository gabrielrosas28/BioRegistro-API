from sqlalchemy import select

from app.core.seguranca import verificar_senha
from app.criar_admin import main
from app.models import Papel, Usuario

ARGUMENTOS = ["--nome", "Coordenação", "--email", "Admin@Exemplo.com", "--senha", "senha-admin-123"]


def test_cria_administrador(fabrica_sessao, db, capsys):
    assert main(ARGUMENTOS, fabrica_sessao) == 0
    usuario = db.scalar(select(Usuario).where(Usuario.email == "admin@exemplo.com"))
    assert usuario.papel == Papel.ADMIN
    assert verificar_senha("senha-admin-123", usuario.senha_hash)
    assert "Administrador criado: admin@exemplo.com" in capsys.readouterr().out


def test_admin_criado_consegue_cadastrar_especie(fabrica_sessao, cliente):
    main(ARGUMENTOS, fabrica_sessao)
    token = cliente.post(
        "/auth/login", data={"username": "admin@exemplo.com", "password": "senha-admin-123"}
    ).json()["access_token"]
    resposta = cliente.post(
        "/especies",
        json={"nome_popular": "Copaíba", "nome_cientifico": "Copaifera langsdorffii"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 201


def test_email_ja_cadastrado(fabrica_sessao, capsys):
    main(ARGUMENTOS, fabrica_sessao)
    assert main(ARGUMENTOS, fabrica_sessao) == 1
    assert "Já existe um usuário com este e-mail" in capsys.readouterr().err


def test_senha_curta(fabrica_sessao, capsys):
    argumentos = ["--nome", "X", "--email", "x@exemplo.com", "--senha", "123"]
    assert main(argumentos, fabrica_sessao) == 1
    assert "senha" in capsys.readouterr().err


def test_pede_a_senha_quando_omitida(fabrica_sessao, db, monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda _: "senha-digitada-123")
    assert main(ARGUMENTOS[:4], fabrica_sessao) == 0
    usuario = db.scalar(select(Usuario))
    assert verificar_senha("senha-digitada-123", usuario.senha_hash)
