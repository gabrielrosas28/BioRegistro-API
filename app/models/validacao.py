import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Decisao
from app.models.tipos import agora_utc, coluna_enum

if TYPE_CHECKING:
    from app.models.registro import Registro
    from app.models.usuario import Usuario


class Validacao(Base):
    __tablename__ = "validacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    registro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("registros.id"), index=True)
    validador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    decisao: Mapped[Decisao] = mapped_column(coluna_enum(Decisao, "decisao"))
    comentario: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    registro: Mapped["Registro"] = relationship(back_populates="validacoes")
    validador: Mapped["Usuario"] = relationship(back_populates="validacoes")
