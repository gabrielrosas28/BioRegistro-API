import pytest

from app.core.seguranca import verificar_senha
from app.models import Papel, Usuario
from tests.conftest import cabecalho


def dados_usuario(**extra):
    dados = {
        "nome": "Maria Silva",
        "email": "maria@exemplo.com",
        "senha": "senha-forte-123",
        "papel": "validador",
    }
    dados.update(extra)
    return dados


def test_admin_cadastra_usuario(cliente, admin, db):
    resposta = cliente.post("/usuarios", json=dados_usuario(), headers=cabecalho(admin))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Maria Silva"
    assert corpo["email"] == "maria@exemplo.com"
    assert corpo["papel"] == "validador"
    assert "senha" not in corpo
    assert "senha_hash" not in corpo
    assert corpo["criado_em"]

    usuario = db.get(Usuario, corpo["id"])
    assert usuario.senha_hash != "senha-forte-123"
    assert verificar_senha("senha-forte-123", usuario.senha_hash)


def test_papel_padrao_e_coletor(cliente, admin):
    dados = dados_usuario()
    del dados["papel"]
    resposta = cliente.post("/usuarios", json=dados, headers=cabecalho(admin))
    assert resposta.json()["papel"] == Papel.COLETOR


def test_email_e_salvo_em_minusculas(cliente, admin):
    resposta = cliente.post(
        "/usuarios", json=dados_usuario(email="Maria@Exemplo.COM"), headers=cabecalho(admin)
    )
    assert resposta.json()["email"] == "maria@exemplo.com"


def test_usuario_cadastrado_consegue_fazer_login(cliente, admin):
    cliente.post("/usuarios", json=dados_usuario(), headers=cabecalho(admin))
    resposta = cliente.post(
        "/auth/login", data={"username": "maria@exemplo.com", "password": "senha-forte-123"}
    )
    assert resposta.status_code == 200


def test_email_duplicado(cliente, admin):
    cliente.post("/usuarios", json=dados_usuario(), headers=cabecalho(admin))
    resposta = cliente.post(
        "/usuarios", json=dados_usuario(email="MARIA@exemplo.com"), headers=cabecalho(admin)
    )
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Já existe um usuário com este e-mail"}


@pytest.mark.parametrize("papel", [Papel.COLETOR, Papel.VALIDADOR])
def test_apenas_admin_cadastra_usuario(cliente, criar_usuario, papel):
    usuario = criar_usuario(f"{papel}@exemplo.com", papel)
    resposta = cliente.post("/usuarios", json=dados_usuario(), headers=cabecalho(usuario))
    assert resposta.status_code == 403


def test_cadastro_sem_token(cliente):
    assert cliente.post("/usuarios", json=dados_usuario()).status_code == 401


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("email", "nao-e-email"),
        ("email", "a" * 150 + "@exemplo.com"),
        ("senha", "curta"),
        ("senha", "ç" * 37),
        ("nome", ""),
        ("nome", "   "),
        ("nome", "x" * 121),
        ("papel", "superusuario"),
    ],
)
def test_dados_invalidos(cliente, admin, campo, valor):
    resposta = cliente.post(
        "/usuarios", json=dados_usuario(**{campo: valor}), headers=cabecalho(admin)
    )
    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", campo]
