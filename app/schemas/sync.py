import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.registro import RegistroDetalhe, RegistroEntrada

TAMANHO_MAXIMO_LOTE = 500

EXEMPLO_REGISTRO = {
    "id": "6f1c2b9e-3d4a-4f5b-8c7d-9e0a1b2c3d4e",
    "especie_id": 1,
    "descricao": "Touceira com cachos maduros na beira do igarapé",
    "uso_tradicional": "Fruto batido para o vinho de açaí",
    "latitude": -1.455833,
    "longitude": -48.503889,
    "data_coleta": "2026-11-20",
}


class RegistroSync(RegistroEntrada):
    model_config = ConfigDict(json_schema_extra={"examples": [EXEMPLO_REGISTRO]})

    id: uuid.UUID = Field(description="UUID gerado no aparelho")


class LoteSync(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"registros": [EXEMPLO_REGISTRO]}]})

    registros: list[RegistroSync] = Field(min_length=1, max_length=TAMANHO_MAXIMO_LOTE)


class ErroLote(BaseModel):
    id: uuid.UUID
    motivo: str


class ResultadoLote(BaseModel):
    criados: list[uuid.UUID]
    ignorados: list[uuid.UUID] = Field(description="UUIDs que já existiam no servidor")
    erros: list[ErroLote]


class RegistroExcluido(BaseModel):
    id: uuid.UUID
    excluido_em: datetime


class AlteracoesSync(BaseModel):
    alterados: list[RegistroDetalhe]
    excluidos: list[RegistroExcluido]
    sincronizado_em: datetime = Field(
        description="Hora do servidor; envie como `desde` na próxima sincronização"
    )
