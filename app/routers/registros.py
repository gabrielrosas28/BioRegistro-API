import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.models import Registro
from app.routers.dependencias import Sessao, UsuarioAtual, UsuarioOpcional, Validador
from app.schemas.comum import Erro
from app.schemas.registro import (
    BuscaProximos,
    FiltrosRegistro,
    PaginaRegistros,
    RegistroCriacao,
    RegistroDetalhe,
    RegistroEntrada,
    RegistroProximo,
    ValidacaoEntrada,
)
from app.services.registro import RegistroService

router = APIRouter(prefix="/registros", tags=["Registros"])

ERRO_401 = {401: {"model": Erro, "description": "Token ausente, inválido ou expirado"}}
ERRO_404 = {404: {"model": Erro, "description": "Registro não encontrado"}}
ERROS_DONO = {
    **ERRO_401,
    403: {"model": Erro, "description": "O registro é de outro coletor"},
    **ERRO_404,
    409: {"model": Erro, "description": "O registro não está mais pendente"},
}

VISIBILIDADE = (
    "Sem login, só aparecem registros validados. O coletor vê os validados e os próprios; "
    "validadores e administradores veem todos."
)


@router.post(
    "",
    response_model=RegistroDetalhe,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um registro de campo",
    description=(
        "O registro entra como `pendente`. O `id` pode ser o UUID gerado no aparelho; "
        "se for omitido, o servidor gera um."
    ),
    responses={
        **ERRO_401,
        409: {"model": Erro, "description": "Já existe um registro com este id"},
        422: {"description": "Dados inválidos ou espécie inexistente"},
    },
)
def criar_registro(dados: RegistroCriacao, db: Sessao, usuario: UsuarioAtual) -> Registro:
    return RegistroService(db).criar(dados, usuario)


@router.get(
    "",
    response_model=PaginaRegistros,
    summary="Lista registros com filtros e paginação",
    description=f"{VISIBILIDADE} O período filtra pela data da coleta.",
    responses=ERRO_401,
)
def listar_registros(
    filtros: Annotated[FiltrosRegistro, Query()], db: Sessao, usuario: UsuarioOpcional
) -> PaginaRegistros:
    return RegistroService(db).listar(filtros, usuario)


@router.get(
    "/proximos",
    response_model=list[RegistroProximo],
    summary="Busca registros dentro de um raio",
    description=(
        "Calcula a distância pela fórmula de Haversine e devolve os registros dentro de "
        f"`raio_km`, do mais próximo ao mais distante. {VISIBILIDADE}"
    ),
    responses=ERRO_401,
)
def buscar_proximos(
    busca: Annotated[BuscaProximos, Query()], db: Sessao, usuario: UsuarioOpcional
) -> list[RegistroProximo]:
    return RegistroService(db).proximos(busca, usuario)


@router.get(
    "/{registro_id}",
    response_model=RegistroDetalhe,
    summary="Detalha um registro com o histórico de validação",
    description=VISIBILIDADE,
    responses={**ERRO_401, **ERRO_404},
)
def detalhar_registro(registro_id: uuid.UUID, db: Sessao, usuario: UsuarioOpcional) -> Registro:
    return RegistroService(db).detalhar(registro_id, usuario)


@router.put(
    "/{registro_id}",
    response_model=RegistroDetalhe,
    summary="Edita um registro pendente",
    description="Só o coletor que criou o registro pode editá-lo, e apenas enquanto estiver pendente.",
    responses={**ERROS_DONO, 422: {"description": "Dados inválidos ou espécie inexistente"}},
)
def editar_registro(
    registro_id: uuid.UUID, dados: RegistroEntrada, db: Sessao, usuario: UsuarioAtual
) -> Registro:
    return RegistroService(db).atualizar(registro_id, dados, usuario)


@router.delete(
    "/{registro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui um registro pendente",
    description=(
        "A exclusão é lógica: o registro some das consultas, mas continua no banco "
        "para a sincronização avisar o aplicativo."
    ),
    responses=ERROS_DONO,
)
def excluir_registro(registro_id: uuid.UUID, db: Sessao, usuario: UsuarioAtual) -> Response:
    RegistroService(db).excluir(registro_id, usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{registro_id}/validacao",
    response_model=RegistroDetalhe,
    status_code=status.HTTP_201_CREATED,
    summary="Aprova ou rejeita um registro pendente",
    description=(
        "Exclusivo para validadores. A rejeição exige comentário com no mínimo 10 caracteres "
        "e ninguém valida o próprio registro."
    ),
    responses={
        **ERRO_401,
        403: {"model": Erro, "description": "Não é validador ou o registro é dele"},
        **ERRO_404,
        409: {"model": Erro, "description": "O registro já foi validado ou rejeitado"},
        422: {"description": "Rejeição sem comentário suficiente"},
    },
)
def validar_registro(
    registro_id: uuid.UUID, dados: ValidacaoEntrada, db: Sessao, validador: Validador
) -> Registro:
    return RegistroService(db).validar(registro_id, dados, validador)
