from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.routers.dependencias import Sessao, UsuarioAtual
from app.schemas.comum import Erro
from app.schemas.sync import AlteracoesSync, LoteSync, ResultadoLote
from app.services.sync import SyncService

router = APIRouter(prefix="/sync", tags=["Sincronização"])

ERRO_401 = {401: {"model": Erro, "description": "Token ausente, inválido ou expirado"}}


@router.post(
    "/registros",
    response_model=ResultadoLote,
    summary="Recebe um lote de registros criados offline",
    description=(
        "Cada registro traz o UUID gerado no aparelho. UUIDs que já existem no servidor "
        "são ignorados, então reenviar o mesmo lote não duplica dados. Itens com espécie "
        "inexistente voltam em `erros` sem impedir o resto do lote. Até 500 registros por envio."
    ),
    responses={
        **ERRO_401,
        409: {"model": Erro, "description": "Conflito com outra sincronização simultânea"},
        422: {"description": "Lote vazio, grande demais ou com dados inválidos"},
    },
)
def receber_lote(lote: LoteSync, db: Sessao, usuario: UsuarioAtual) -> ResultadoLote:
    return SyncService(db).receber_lote(lote, usuario)


@router.get(
    "/registros",
    response_model=AlteracoesSync,
    summary="Devolve o que mudou desde a última sincronização",
    description=(
        "Lista os registros criados ou alterados a partir de `desde`, os excluídos no mesmo "
        "período e a hora do servidor, que deve ser usada como `desde` na próxima chamada. "
        "Sem `desde`, devolve todos os registros visíveis. Datas sem fuso são lidas como UTC."
    ),
    responses=ERRO_401,
)
def alteracoes(
    db: Sessao,
    usuario: UsuarioAtual,
    desde: Annotated[
        datetime | None, Query(description="Data e hora da última sincronização (ISO 8601)")
    ] = None,
) -> AlteracoesSync:
    return SyncService(db).alteracoes(desde, usuario)
