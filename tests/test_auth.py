from app.core.seguranca import criar_token, ler_token
from tests.conftest import SENHA_PADRAO


def login(cliente, email, senha):
    return cliente.post("/auth/login", data={"username": email, "password": senha})


def test_login_devolve_token(cliente, coletor):
    resposta = login(cliente, "coletor@exemplo.com", SENHA_PADRAO)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == 3600
    assert ler_token(corpo["access_token"]) == coletor.id


def test_login_ignora_maiusculas_e_espacos_no_email(cliente, coletor):
    resposta = login(cliente, "  Coletor@Exemplo.COM ", SENHA_PADRAO)
    assert resposta.status_code == 200


def test_login_com_senha_errada(cliente, coletor):
    resposta = login(cliente, "coletor@exemplo.com", "senha-errada")
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "E-mail ou senha incorretos"}
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_login_com_email_inexistente_tem_a_mesma_resposta(cliente, coletor):
    resposta = login(cliente, "ninguem@exemplo.com", SENHA_PADRAO)
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "E-mail ou senha incorretos"}


def test_login_sem_campos(cliente):
    assert cliente.post("/auth/login", data={}).status_code == 422


def test_token_do_login_acessa_rota_protegida(cliente, admin):
    token = login(cliente, "admin@exemplo.com", SENHA_PADRAO).json()["access_token"]
    resposta = cliente.post(
        "/especies",
        json={"nome_popular": "Andiroba", "nome_cientifico": "Carapa guianensis"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 201


def test_rota_protegida_sem_token(cliente):
    resposta = cliente.post("/especies", json={})
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Não autenticado"}
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_rota_protegida_com_token_invalido(cliente):
    resposta = cliente.post("/especies", json={}, headers={"Authorization": "Bearer abc.def.ghi"})
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Token inválido ou expirado"}


def test_token_de_usuario_que_nao_existe_mais(cliente):
    resposta = cliente.post(
        "/especies", json={}, headers={"Authorization": f"Bearer {criar_token(9999)}"}
    )
    assert resposta.status_code == 401


def test_swagger_tem_botao_de_autorizacao(cliente):
    esquemas = cliente.get("/openapi.json").json()["components"]["securitySchemes"]
    assert esquemas["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "/auth/login"
