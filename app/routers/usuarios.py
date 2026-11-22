from fastapi import APIRouter, status

from app.models import Usuario
from app.routers.dependencias import Admin, Sessao
from app.schemas.comum import Erro
from app.schemas.usuario import UsuarioCriacao, UsuarioLeitura
from app.services.usuario import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post(
    "",
    response_model=UsuarioLeitura,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um usuário",
    description="Disponível apenas para administradores. O papel padrão é `coletor`.",
    responses={
        401: {"model": Erro, "description": "Token ausente, inválido ou expirado"},
        403: {"model": Erro, "description": "Usuário não é administrador"},
        409: {"model": Erro, "description": "E-mail já cadastrado"},
    },
)
def cadastrar_usuario(dados: UsuarioCriacao, db: Sessao, _: Admin) -> Usuario:
    return UsuarioService(db).cadastrar(dados)
