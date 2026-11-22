from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Especie
from app.repositories.especie import EspecieRepository
from app.schemas.especie import EspecieEntrada
from app.services.erros import Conflito, NaoEncontrado

MENSAGEM_NOME_DUPLICADO = "Já existe uma espécie com este nome científico"


class EspecieService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.especies = EspecieRepository(db)

    def listar(self) -> list[Especie]:
        return self.especies.listar()

    def cadastrar(self, dados: EspecieEntrada) -> Especie:
        self._garantir_nome_livre(dados.nome_cientifico)
        return self._salvar(Especie(**dados.model_dump()))

    def atualizar(self, especie_id: int, dados: EspecieEntrada) -> Especie:
        especie = self.especies.buscar_por_id(especie_id)
        if especie is None:
            raise NaoEncontrado("Espécie não encontrada")
        self._garantir_nome_livre(dados.nome_cientifico, ignorar_id=especie_id)
        for campo, valor in dados.model_dump().items():
            setattr(especie, campo, valor)
        return self._salvar(especie)

    def _garantir_nome_livre(self, nome_cientifico: str, ignorar_id: int | None = None) -> None:
        existente = self.especies.buscar_por_nome_cientifico(nome_cientifico)
        if existente is not None and existente.id != ignorar_id:
            raise Conflito(MENSAGEM_NOME_DUPLICADO)

    def _salvar(self, especie: Especie) -> Especie:
        try:
            return self.especies.salvar(especie)
        except IntegrityError as erro:
            self.db.rollback()
            raise Conflito(MENSAGEM_NOME_DUPLICADO) from erro
