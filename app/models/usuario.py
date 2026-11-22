from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Papel
from app.models.tipos import agora_utc, coluna_enum

if TYPE_CHECKING:
    from app.models.registro import Registro
    from app.models.validacao import Validacao


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[Papel] = mapped_column(coluna_enum(Papel, "papel"), default=Papel.COLETOR)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    registros: Mapped[list["Registro"]] = relationship(back_populates="coletor")
    validacoes: Mapped[list["Validacao"]] = relationship(back_populates="validador")
