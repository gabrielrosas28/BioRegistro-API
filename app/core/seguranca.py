from datetime import UTC, datetime, timedelta
from functools import cache

import bcrypt
import jwt

from app.core.config import get_settings

LIMITE_BYTES_SENHA = 72


def gerar_hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(senha.encode(), salt).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    dados = senha.encode()
    if len(dados) > LIMITE_BYTES_SENHA:
        return False
    return bcrypt.checkpw(dados, senha_hash.encode())


@cache
def hash_ficticio() -> str:
    return gerar_hash_senha("senha-que-nunca-sera-usada")


def criar_token(usuario_id: int) -> str:
    cfg = get_settings()
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "iat": agora,
        "exp": agora + timedelta(minutes=cfg.jwt_expiracao_minutos),
    }
    return jwt.encode(payload, cfg.secret_key, algorithm=cfg.jwt_algoritmo)


def ler_token(token: str) -> int | None:
    cfg = get_settings()
    try:
        payload = jwt.decode(
            token,
            cfg.secret_key,
            algorithms=[cfg.jwt_algoritmo],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
