from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.registro import Registro


class Especie(Base):
    __tablename__ = "especies"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_popular: Mapped[str] = mapped_column(String(120))
    nome_cientifico: Mapped[str] = mapped_column(String(160), unique=True)
    familia: Mapped[str | None] = mapped_column(String(120))

    registros: Mapped[list["Registro"]] = relationship(back_populates="especie")
