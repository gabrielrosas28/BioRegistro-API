from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.seguranca import criar_token, hash_ficticio, verificar_senha
from app.models import Usuario
from app.repositories.usuario import UsuarioRepository
from app.schemas.auth import Token
from app.services.erros import NaoAutenticado


class AuthService:
    def __init__(self, db: Session) -> None:
        self.usuarios = UsuarioRepository(db)

    def autenticar(self, email: str, senha: str) -> Usuario:
        usuario = self.usuarios.buscar_por_email(email.strip().lower())
        if usuario is None:
            verificar_senha(senha, hash_ficticio())
            raise NaoAutenticado("E-mail ou senha incorretos")
        if not verificar_senha(senha, usuario.senha_hash):
            raise NaoAutenticado("E-mail ou senha incorretos")
        return usuario

    def login(self, email: str, senha: str) -> Token:
        usuario = self.autenticar(email, senha)
        return Token(
            access_token=criar_token(usuario.id),
            expires_in=get_settings().jwt_expiracao_minutos * 60,
        )
