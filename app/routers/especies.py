from fastapi import APIRouter, status

from app.models import Especie
from app.routers.dependencias import Admin, Sessao
from app.schemas.comum import Erro
from app.schemas.especie import EspecieEntrada, EspecieLeitura
from app.services.especie import EspecieService

router = APIRouter(prefix="/especies", tags=["Espécies"])

ERROS_ADMIN = {
    401: {"model": Erro, "description": "Token ausente, inválido ou expirado"},
    403: {"model": Erro, "description": "Usuário não é administrador"},
}


@router.get(
    "",
    response_model=list[EspecieLeitura],
    summary="Lista as espécies",
    description="Rota pública, ordenada pelo nome popular.",
)
def listar_especies(db: Sessao) -> list[Especie]:
    return EspecieService(db).listar()


@router.post(
    "",
    response_model=EspecieLeitura,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma espécie",
    responses={**ERROS_ADMIN, 409: {"model": Erro, "description": "Nome científico já cadastrado"}},
)
def cadastrar_especie(dados: EspecieEntrada, db: Sessao, _: Admin) -> Especie:
    return EspecieService(db).cadastrar(dados)


@router.put(
    "/{especie_id}",
    response_model=EspecieLeitura,
    summary="Edita uma espécie",
    responses={
        **ERROS_ADMIN,
        404: {"model": Erro, "description": "Espécie não encontrada"},
        409: {"model": Erro, "description": "Nome científico já cadastrado"},
    },
)
def editar_especie(especie_id: int, dados: EspecieEntrada, db: Sessao, _: Admin) -> Especie:
    return EspecieService(db).atualizar(especie_id, dados)
