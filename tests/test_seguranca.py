from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.seguranca import criar_token, gerar_hash_senha, ler_token, verificar_senha


def test_hash_nao_guarda_a_senha_em_texto():
    senha_hash = gerar_hash_senha("minha-senha-123")
    assert "minha-senha-123" not in senha_hash
    assert senha_hash.startswith("$2b$")


def test_verificar_senha():
    senha_hash = gerar_hash_senha("minha-senha-123")
    assert verificar_senha("minha-senha-123", senha_hash)
    assert not verificar_senha("outra-senha", senha_hash)


def test_hash_muda_a_cada_geracao():
    assert gerar_hash_senha("igual") != gerar_hash_senha("igual")


def test_senha_acima_de_72_bytes_nao_confere():
    senha_hash = gerar_hash_senha("a" * 72)
    assert not verificar_senha("a" * 73, senha_hash)


def test_token_carrega_o_id_do_usuario():
    assert ler_token(criar_token(42)) == 42


def test_token_expira_em_60_minutos():
    cfg = get_settings()
    payload = jwt.decode(criar_token(1), cfg.secret_key, algorithms=[cfg.jwt_algoritmo])
    assert payload["exp"] - payload["iat"] == 60 * 60


def test_token_expirado_e_recusado():
    cfg = get_settings()
    passado = datetime.now(UTC) - timedelta(minutes=61)
    token = jwt.encode(
        {"sub": "1", "iat": passado, "exp": passado + timedelta(minutes=60)},
        cfg.secret_key,
        algorithm=cfg.jwt_algoritmo,
    )
    assert ler_token(token) is None


def test_token_assinado_com_outra_chave_e_recusado():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "uma-chave-diferente-com-tamanho-suficiente",
        algorithm="HS256",
    )
    assert ler_token(token) is None


def test_token_sem_expiracao_e_recusado():
    cfg = get_settings()
    token = jwt.encode({"sub": "1"}, cfg.secret_key, algorithm=cfg.jwt_algoritmo)
    assert ler_token(token) is None


def test_token_malformado_e_recusado():
    assert ler_token("isto-nao-e-um-jwt") is None
