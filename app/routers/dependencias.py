from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.seguranca import ler_token
from app.models import Papel, Usuario
from app.repositories.usuario import UsuarioRepository

esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

Sessao = Annotated[Session, Depends(get_db)]


def nao_autenticado(mensagem: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensagem,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_atual(db: Sessao, token: Annotated[str | None, Depends(esquema_oauth2)]) -> Usuario:
    if not token:
        raise nao_autenticado("Não autenticado")
    usuario_id = ler_token(token)
    usuario = None if usuario_id is None else UsuarioRepository(db).buscar_por_id(usuario_id)
    if usuario is None:
        raise nao_autenticado("Token inválido ou expirado")
    return usuario


def exigir_papel(*papeis: Papel) -> Callable[[Usuario], Usuario]:
    def verificar(usuario: Annotated[Usuario, Depends(usuario_atual)]) -> Usuario:
        if usuario.papel not in papeis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu papel não tem permissão para esta ação",
            )
        return usuario

    return verificar


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]
Admin = Annotated[Usuario, Depends(exigir_papel(Papel.ADMIN))]
