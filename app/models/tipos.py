from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Dialect, Enum, TypeDecorator


def agora_utc() -> datetime:
    return datetime.now(UTC)


def para_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)


class DataHoraUTC(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, valor: datetime | None, dialect: Dialect) -> datetime | None:
        return None if valor is None else para_utc(valor)

    def process_result_value(self, valor: datetime | None, dialect: Dialect) -> datetime | None:
        return None if valor is None else para_utc(valor)


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
