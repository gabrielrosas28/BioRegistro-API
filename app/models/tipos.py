from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum


def agora_utc() -> datetime:
    return datetime.now(UTC)


def coluna_enum(enum_cls: type[PyEnum], nome: str) -> Enum:
    return Enum(
        enum_cls,
        name=nome,
        native_enum=False,
        length=20,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
