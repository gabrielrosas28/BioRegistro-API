import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.models import Decisao, StatusRegistro
from app.schemas.especie import EspecieLeitura

TAMANHO_MAXIMO_TEXTO = 5000
TAMANHO_MINIMO_COMENTARIO_REJEICAO = 10
TAMANHO_MAXIMO_PAGINA = 100
RAIO_MAXIMO_KM = 20000
LIMITE_MAXIMO_PROXIMOS = 500
CASAS_DECIMAIS_COORDENADA = 6

TextoLongo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_TEXTO)
]


def hoje_utc() -> date:
    return datetime.now(UTC).date()


class RegistroEntrada(BaseModel):
    especie_id: int = Field(gt=0)
    descricao: TextoLongo
    uso_tradicional: TextoLongo
    latitude: float = Field(ge=-90, le=90, description="Graus decimais, WGS 84")
    longitude: float = Field(ge=-180, le=180, description="Graus decimais, WGS 84")
    data_coleta: date

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "especie_id": 1,
                    "descricao": "Touceira com cachos maduros na beira do igarapé",
                    "uso_tradicional": "Fruto batido para o vinho de açaí",
                    "latitude": -1.455833,
                    "longitude": -48.503889,
                    "data_coleta": "2026-11-20",
                }
            ]
        }
    )

    @field_validator("latitude", "longitude")
    @classmethod
    def arredondar_coordenada(cls, valor: float) -> float:
        return round(valor, CASAS_DECIMAIS_COORDENADA)

    @field_validator("data_coleta")
    @classmethod
    def data_nao_futura(cls, valor: date) -> date:
        if valor > hoje_utc():
            raise ValueError("a data da coleta não pode ser futura")
        return valor


class RegistroCriacao(RegistroEntrada):
    id: uuid.UUID | None = Field(
        default=None,
        description="UUID gerado no aparelho. Se omitido, o servidor gera um.",
    )


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class ValidacaoLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    validador: UsuarioResumo
    decisao: Decisao
    comentario: str | None
    criado_em: datetime


class RegistroLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coletor: UsuarioResumo
    especie: EspecieLeitura
    descricao: str
    uso_tradicional: str
    latitude: float
    longitude: float
    foto_url: str | None
    status: StatusRegistro
    data_coleta: date
    criado_em: datetime
    atualizado_em: datetime


class RegistroDetalhe(RegistroLeitura):
    validacoes: list[ValidacaoLeitura]


class ValidacaoEntrada(BaseModel):
    decisao: Decisao
    comentario: str | None = Field(
        default=None,
        max_length=TAMANHO_MAXIMO_TEXTO,
        description=(
            f"Obrigatório na rejeição, com no mínimo "
            f"{TAMANHO_MINIMO_COMENTARIO_REJEICAO} caracteres"
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "decisao": "rejeitado",
                    "comentario": "A foto não permite confirmar a espécie",
                }
            ]
        }
    )

    @model_validator(mode="before")
    @classmethod
    def sempre_validar_comentario(cls, dados: Any) -> Any:
        if isinstance(dados, dict) and "comentario" not in dados:
            return {**dados, "comentario": None}
        return dados

    @field_validator("comentario")
    @classmethod
    def exigir_comentario_na_rejeicao(cls, valor: str | None, info: ValidationInfo) -> str | None:
        valor = valor.strip() if valor else None
        rejeicao = info.data.get("decisao") == Decisao.REJEITADO
        if rejeicao and (valor is None or len(valor) < TAMANHO_MINIMO_COMENTARIO_REJEICAO):
            raise ValueError(
                f"a rejeição exige um comentário com no mínimo "
                f"{TAMANHO_MINIMO_COMENTARIO_REJEICAO} caracteres"
            )
        return valor or None


class FiltrosRegistro(BaseModel):
    status: StatusRegistro | None = None
    especie_id: int | None = Field(default=None, gt=0)
    coletor_id: int | None = Field(default=None, gt=0)
    data_inicio: date | None = Field(default=None, description="Data da coleta a partir de")
    data_fim: date | None = Field(default=None, description="Data da coleta até")
    pagina: int = Field(default=1, ge=1)
    tamanho: int = Field(default=20, ge=1, le=TAMANHO_MAXIMO_PAGINA)

    @model_validator(mode="after")
    def periodo_valido(self) -> Self:
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            raise ValueError("data_inicio não pode ser posterior a data_fim")
        return self


class PaginaRegistros(BaseModel):
    itens: list[RegistroLeitura]
    total: int
    pagina: int
    tamanho: int


class BuscaProximos(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude do ponto de referência (WGS 84)")
    lon: float = Field(ge=-180, le=180, description="Longitude do ponto de referência (WGS 84)")
    raio_km: float = Field(gt=0, le=RAIO_MAXIMO_KM, description="Raio da busca em km")
    limite: int = Field(
        default=50,
        ge=1,
        le=LIMITE_MAXIMO_PROXIMOS,
        description="Quantidade máxima de registros devolvidos",
    )


class RegistroProximo(RegistroLeitura):
    distancia_km: float
