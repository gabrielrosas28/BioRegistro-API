import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import StatusRegistro
from app.models.tipos import DataHoraUTC, agora_utc, coluna_enum

if TYPE_CHECKING:
    from app.models.especie import Especie
    from app.models.usuario import Usuario
    from app.models.validacao import Validacao


class Registro(Base):
    __tablename__ = "registros"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="latitude_valida"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="longitude_valida"),
        Index("ix_registros_lat_lon", "latitude", "longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    coletor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    especie_id: Mapped[int] = mapped_column(ForeignKey("especies.id"), index=True)
    descricao: Mapped[str] = mapped_column(Text)
    uso_tradicional: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False))
    longitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False))
    foto_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[StatusRegistro] = mapped_column(
        coluna_enum(StatusRegistro, "status_registro"),
        default=StatusRegistro.PENDENTE,
        index=True,
    )
    data_coleta: Mapped[date] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(DataHoraUTC(), default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(
        DataHoraUTC(), default=agora_utc, onupdate=agora_utc, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DataHoraUTC())

    coletor: Mapped["Usuario"] = relationship(back_populates="registros")
    especie: Mapped["Especie"] = relationship(back_populates="registros")
    validacoes: Mapped[list["Validacao"]] = relationship(
        back_populates="registro", order_by="Validacao.criado_em"
    )
