from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.schemas.comum import Texto120, Texto160


def vazio_para_nulo(valor: object) -> object:
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


FamiliaOpcional = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None,
    BeforeValidator(vazio_para_nulo),
]


class EspecieEntrada(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome_popular": "Açaí",
                    "nome_cientifico": "Euterpe oleracea",
                    "familia": "Arecaceae",
                }
            ]
        }
    )

    nome_popular: Texto120
    nome_cientifico: Texto160
    familia: FamiliaOpcional = None


class EspecieLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_popular: str
    nome_cientifico: str
    familia: str | None
