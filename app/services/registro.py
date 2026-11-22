import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Decisao, Papel, Registro, StatusRegistro, Usuario, Validacao
from app.repositories.especie import EspecieRepository
from app.repositories.registro import RegistroRepository
from app.schemas.registro import (
    FiltrosRegistro,
    PaginaRegistros,
    RegistroCriacao,
    RegistroEntrada,
    RegistroLeitura,
    ValidacaoEntrada,
)
from app.services.erros import AcessoNegado, Conflito, DadosInvalidos, NaoEncontrado

PAPEIS_QUE_VEEM_TUDO = {Papel.VALIDADOR, Papel.ADMIN}
STATUS_POR_DECISAO = {
    Decisao.APROVADO: StatusRegistro.VALIDADO,
    Decisao.REJEITADO: StatusRegistro.REJEITADO,
}
MENSAGEM_NAO_ENCONTRADO = "Registro não encontrado"


def pode_ver(usuario: Usuario | None, registro: Registro) -> bool:
    if registro.status == StatusRegistro.VALIDADO:
        return True
    if usuario is None:
        return False
    return usuario.papel in PAPEIS_QUE_VEEM_TUDO or registro.coletor_id == usuario.id


class RegistroService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registros = RegistroRepository(db)
        self.especies = EspecieRepository(db)

    def listar(self, filtros: FiltrosRegistro, usuario: Usuario | None) -> PaginaRegistros:
        ve_tudo = usuario is not None and usuario.papel in PAPEIS_QUE_VEEM_TUDO
        itens, total = self.registros.listar(
            filtros,
            apenas_validados=not ve_tudo,
            incluir_do_coletor=usuario.id if usuario is not None and not ve_tudo else None,
        )
        return PaginaRegistros(
            itens=[RegistroLeitura.model_validate(r) for r in itens],
            total=total,
            pagina=filtros.pagina,
            tamanho=filtros.tamanho,
        )

    def detalhar(self, registro_id: uuid.UUID, usuario: Usuario | None) -> Registro:
        registro = self.registros.buscar_ativo(registro_id, detalhado=True)
        if registro is None or not pode_ver(usuario, registro):
            raise NaoEncontrado(MENSAGEM_NAO_ENCONTRADO)
        return registro

    def criar(self, dados: RegistroCriacao, autor: Usuario) -> Registro:
        if dados.id is not None and self.registros.existe(dados.id):
            raise Conflito("Já existe um registro com este id")
        self._garantir_especie(dados.especie_id)
        registro = Registro(
            **dados.model_dump(exclude={"id"}),
            id=dados.id or uuid.uuid4(),
            coletor_id=autor.id,
            status=StatusRegistro.PENDENTE,
        )
        try:
            self.registros.adicionar(registro)
            self.db.commit()
        except IntegrityError as erro:
            self.db.rollback()
            raise Conflito("Já existe um registro com este id") from erro
        return self._recarregar(registro.id)

    def atualizar(
        self, registro_id: uuid.UUID, dados: RegistroEntrada, usuario: Usuario
    ) -> Registro:
        self._pendente_do_dono(registro_id, usuario, "editados")
        self._garantir_especie(dados.especie_id)
        if not self.registros.atualizar_se_pendente(registro_id, dados.model_dump()):
            self.db.rollback()
            raise Conflito("Só registros pendentes podem ser editados")
        self.db.commit()
        return self._recarregar(registro_id)

    def excluir(self, registro_id: uuid.UUID, usuario: Usuario) -> None:
        self._pendente_do_dono(registro_id, usuario, "excluídos")
        if not self.registros.excluir_se_pendente(registro_id):
            self.db.rollback()
            raise Conflito("Só registros pendentes podem ser excluídos")
        self.db.commit()

    def validar(
        self, registro_id: uuid.UUID, dados: ValidacaoEntrada, validador: Usuario
    ) -> Registro:
        registro = self.registros.buscar_ativo(registro_id)
        if registro is None:
            raise NaoEncontrado(MENSAGEM_NAO_ENCONTRADO)
        if registro.coletor_id == validador.id:
            raise AcessoNegado("Um validador não pode validar um registro criado por ele mesmo")
        if registro.status != StatusRegistro.PENDENTE:
            raise Conflito("Este registro já foi validado ou rejeitado")
        if not self.registros.decidir_se_pendente(registro_id, STATUS_POR_DECISAO[dados.decisao]):
            self.db.rollback()
            raise Conflito("Este registro já foi validado ou rejeitado")
        self.db.add(
            Validacao(
                registro_id=registro_id,
                validador_id=validador.id,
                decisao=dados.decisao,
                comentario=dados.comentario,
            )
        )
        self.db.commit()
        return self._recarregar(registro_id)

    def _pendente_do_dono(self, registro_id: uuid.UUID, usuario: Usuario, acao: str) -> Registro:
        registro = self.registros.buscar_ativo(registro_id)
        if registro is None or not pode_ver(usuario, registro):
            raise NaoEncontrado(MENSAGEM_NAO_ENCONTRADO)
        if registro.coletor_id != usuario.id:
            raise AcessoNegado("Só o coletor que criou o registro pode alterá-lo")
        if registro.status != StatusRegistro.PENDENTE:
            raise Conflito(f"Só registros pendentes podem ser {acao}")
        return registro

    def _garantir_especie(self, especie_id: int) -> None:
        if self.especies.buscar_por_id(especie_id) is None:
            raise DadosInvalidos("Espécie não encontrada")

    def _recarregar(self, registro_id: uuid.UUID) -> Registro:
        registro = self.registros.buscar_ativo(registro_id, detalhado=True)
        if registro is None:
            raise NaoEncontrado(MENSAGEM_NAO_ENCONTRADO)
        return registro
