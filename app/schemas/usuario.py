from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.seguranca import LIMITE_BYTES_SENHA
from app.models import Papel
from app.schemas.comum import Texto120

TAMANHO_MAXIMO_EMAIL = 160


class UsuarioCriacao(BaseModel):
    nome: Texto120
    email: EmailStr
    senha: str = Field(min_length=8)
    papel: Papel = Papel.COLETOR

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Maria Silva",
                    "email": "maria@exemplo.com",
                    "senha": "senha-forte-123",
                    "papel": "coletor",
                }
            ]
        }
    )

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        valor = valor.lower()
        if len(valor) > TAMANHO_MAXIMO_EMAIL:
            raise ValueError(f"o e-mail deve ter no máximo {TAMANHO_MAXIMO_EMAIL} caracteres")
        return valor

    @field_validator("senha")
    @classmethod
    def limitar_senha(cls, valor: str) -> str:
        if len(valor.encode()) > LIMITE_BYTES_SENHA:
            raise ValueError(f"a senha deve ter no máximo {LIMITE_BYTES_SENHA} bytes")
        return valor


class UsuarioLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    papel: Papel
    criado_em: datetime
