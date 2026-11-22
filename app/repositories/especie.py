from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Especie


class EspecieRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def listar(self) -> list[Especie]:
        consulta = select(Especie).order_by(Especie.nome_popular, Especie.id)
        return list(self.db.scalars(consulta))

    def buscar_por_id(self, especie_id: int) -> Especie | None:
        return self.db.get(Especie, especie_id)

    def buscar_por_nome_cientifico(self, nome_cientifico: str) -> Especie | None:
        consulta = select(Especie).where(
            func.lower(Especie.nome_cientifico) == nome_cientifico.lower()
        )
        return self.db.scalar(consulta)

    def salvar(self, especie: Especie) -> Especie:
        self.db.add(especie)
        self.db.commit()
        self.db.refresh(especie)
        return especie
