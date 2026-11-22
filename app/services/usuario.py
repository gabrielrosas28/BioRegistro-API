from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.seguranca import gerar_hash_senha
from app.models import Usuario
from app.repositories.usuario import UsuarioRepository
from app.schemas.usuario import UsuarioCriacao
from app.services.erros import Conflito

MENSAGEM_EMAIL_DUPLICADO = "Já existe um usuário com este e-mail"


class UsuarioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usuarios = UsuarioRepository(db)

    def cadastrar(self, dados: UsuarioCriacao) -> Usuario:
        if self.usuarios.buscar_por_email(dados.email) is not None:
            raise Conflito(MENSAGEM_EMAIL_DUPLICADO)
        usuario = Usuario(
            nome=dados.nome,
            email=dados.email,
            senha_hash=gerar_hash_senha(dados.senha),
            papel=dados.papel,
        )
        try:
            return self.usuarios.salvar(usuario)
        except IntegrityError as erro:
            self.db.rollback()
            raise Conflito(MENSAGEM_EMAIL_DUPLICADO) from erro
