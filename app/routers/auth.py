from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.routers.dependencias import Sessao
from app.schemas.auth import Token
from app.schemas.comum import Erro
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=Token,
    summary="Gera um token JWT",
    description=(
        "Recebe o e-mail no campo `username` e a senha no campo `password` "
        "(formulário OAuth2). O token vale 60 minutos e deve ser enviado no "
        "cabeçalho `Authorization: Bearer <token>`."
    ),
    responses={401: {"model": Erro, "description": "E-mail ou senha incorretos"}},
)
def login(db: Sessao, formulario: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    return AuthService(db).login(formulario.username, formulario.password)
