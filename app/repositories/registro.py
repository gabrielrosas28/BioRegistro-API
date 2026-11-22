import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Registro, StatusRegistro, Validacao
from app.models.tipos import agora_utc
from app.schemas.registro import FiltrosRegistro
from app.core.geo import Caixa


class RegistroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def existe(self, registro_id: uuid.UUID) -> bool:
        return self.db.scalar(select(Registro.id).where(Registro.id == registro_id)) is not None

    def buscar_ativo(self, registro_id: uuid.UUID, detalhado: bool = False) -> Registro | None:
        consulta = (
            select(Registro)
            .where(Registro.id == registro_id, Registro.deleted_at.is_(None))
            .options(joinedload(Registro.coletor), joinedload(Registro.especie))
            .execution_options(populate_existing=True)
        )
        if detalhado:
            consulta = consulta.options(
                selectinload(Registro.validacoes).joinedload(Validacao.validador)
            )
        return self.db.scalar(consulta)

    def listar(
        self,
        filtros: FiltrosRegistro,
        apenas_validados: bool,
        incluir_do_coletor: int | None = None,
    ) -> tuple[list[Registro], int]:
        condicoes = self._condicoes(filtros, apenas_validados, incluir_do_coletor)
        total = self.db.scalar(select(func.count()).select_from(Registro).where(*condicoes)) or 0
        consulta: Select[tuple[Registro]] = (
            select(Registro)
            .where(*condicoes)
            .options(joinedload(Registro.coletor), joinedload(Registro.especie))
            .order_by(Registro.criado_em.desc(), Registro.id)
            .offset((filtros.pagina - 1) * filtros.tamanho)
            .limit(filtros.tamanho)
        )
        return list(self.db.scalars(consulta)), total

    def coordenadas_na_caixa(
        self, caixa: Caixa, apenas_validados: bool, incluir_do_coletor: int | None
    ) -> list[tuple[uuid.UUID, float, float]]:
        if caixa.cruza_antimeridiano:
            faixa_lon = or_(
                Registro.longitude >= caixa.lon_min, Registro.longitude <= caixa.lon_max
            )
        else:
            faixa_lon = Registro.longitude.between(caixa.lon_min, caixa.lon_max)
        consulta = select(Registro.id, Registro.latitude, Registro.longitude).where(
            Registro.deleted_at.is_(None),
            *self._visibilidade(apenas_validados, incluir_do_coletor),
            Registro.latitude.between(caixa.lat_min, caixa.lat_max),
            faixa_lon,
        )
        return [(id_, lat, lon) for id_, lat, lon in self.db.execute(consulta)]

    def buscar_varios(self, ids: Iterable[uuid.UUID]) -> list[Registro]:
        consulta = (
            select(Registro)
            .where(Registro.id.in_(list(ids)), Registro.deleted_at.is_(None))
            .options(joinedload(Registro.coletor), joinedload(Registro.especie))
        )
        return list(self.db.scalars(consulta))

    def ids_existentes(self, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        consulta = select(Registro.id).where(Registro.id.in_(list(ids)))
        return set(self.db.scalars(consulta))

    def alterados_desde(
        self, desde: datetime | None, apenas_validados: bool, incluir_do_coletor: int | None
    ) -> list[Registro]:
        condicoes = [
            Registro.deleted_at.is_(None),
            *self._visibilidade(apenas_validados, incluir_do_coletor),
        ]
        if desde is not None:
            condicoes.append(Registro.atualizado_em >= desde)
        consulta = (
            select(Registro)
            .where(*condicoes)
            .options(
                joinedload(Registro.coletor),
                joinedload(Registro.especie),
                selectinload(Registro.validacoes).joinedload(Validacao.validador),
            )
            .order_by(Registro.atualizado_em, Registro.id)
        )
        return list(self.db.scalars(consulta).unique())

    def excluidos_desde(
        self, desde: datetime, apenas_validados: bool, incluir_do_coletor: int | None
    ) -> list[tuple[uuid.UUID, datetime]]:
        consulta = (
            select(Registro.id, Registro.deleted_at)
            .where(
                Registro.deleted_at >= desde,
                *self._visibilidade(apenas_validados, incluir_do_coletor),
            )
            .order_by(Registro.deleted_at, Registro.id)
        )
        return [(id_, excluido_em) for id_, excluido_em in self.db.execute(consulta)]

    def adicionar(self, registro: Registro) -> None:
        self.db.add(registro)
        self.db.flush()

    def atualizar_se_pendente(self, registro_id: uuid.UUID, valores: dict[str, Any]) -> bool:
        return self._alterar_pendente(registro_id, **valores)

    def excluir_se_pendente(self, registro_id: uuid.UUID) -> bool:
        return self._alterar_pendente(registro_id, deleted_at=agora_utc())

    def decidir_se_pendente(self, registro_id: uuid.UUID, status: StatusRegistro) -> bool:
        return self._alterar_pendente(registro_id, status=status)

    def _alterar_pendente(self, registro_id: uuid.UUID, **valores: Any) -> bool:
        comando = (
            update(Registro)
            .where(
                Registro.id == registro_id,
                Registro.status == StatusRegistro.PENDENTE,
                Registro.deleted_at.is_(None),
            )
            .values(**valores, atualizado_em=agora_utc())
            .execution_options(synchronize_session=False)
        )
        return self.db.execute(comando).rowcount == 1

    @staticmethod
    def _condicoes(
        filtros: FiltrosRegistro, apenas_validados: bool, incluir_do_coletor: int | None
    ) -> list[ColumnElement[bool]]:
        condicoes: list[ColumnElement[bool]] = [
            Registro.deleted_at.is_(None),
            *RegistroRepository._visibilidade(apenas_validados, incluir_do_coletor),
        ]
        if filtros.status is not None:
            condicoes.append(Registro.status == filtros.status)
        if filtros.especie_id is not None:
            condicoes.append(Registro.especie_id == filtros.especie_id)
        if filtros.coletor_id is not None:
            condicoes.append(Registro.coletor_id == filtros.coletor_id)
        if filtros.data_inicio is not None:
            condicoes.append(Registro.data_coleta >= filtros.data_inicio)
        if filtros.data_fim is not None:
            condicoes.append(Registro.data_coleta <= filtros.data_fim)
        return condicoes

    @staticmethod
    def _visibilidade(
        apenas_validados: bool, incluir_do_coletor: int | None
    ) -> list[ColumnElement[bool]]:
        if not apenas_validados:
            return []
        visivel = Registro.status == StatusRegistro.VALIDADO
        if incluir_do_coletor is not None:
            visivel = or_(visivel, Registro.coletor_id == incluir_do_coletor)
        return [visivel]
