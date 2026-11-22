from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Registro, StatusRegistro, Usuario
from app.models.tipos import agora_utc, para_utc
from app.repositories.especie import EspecieRepository
from app.repositories.registro import RegistroRepository
from app.schemas.registro import RegistroDetalhe
from app.schemas.sync import AlteracoesSync, ErroLote, LoteSync, RegistroExcluido, ResultadoLote
from app.services.erros import Conflito
from app.services.registro import escopo_visibilidade

TENTATIVAS_LOTE = 2


class SyncService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registros = RegistroRepository(db)
        self.especies = EspecieRepository(db)

    def receber_lote(self, lote: LoteSync, autor: Usuario) -> ResultadoLote:
        for _ in range(TENTATIVAS_LOTE):
            try:
                return self._gravar_lote(lote, autor)
            except IntegrityError:
                self.db.rollback()
        raise Conflito("O lote conflitou com outra sincronização; envie novamente")

    def alteracoes(self, desde: datetime | None, usuario: Usuario) -> AlteracoesSync:
        sincronizado_em = agora_utc()
        desde = para_utc(desde) if desde is not None else None
        escopo = escopo_visibilidade(usuario)
        alterados = self.registros.alterados_desde(desde, *escopo)
        excluidos = self.registros.excluidos_desde(desde, *escopo) if desde is not None else []
        return AlteracoesSync(
            alterados=[RegistroDetalhe.model_validate(r) for r in alterados],
            excluidos=[RegistroExcluido(id=i, excluido_em=quando) for i, quando in excluidos],
            sincronizado_em=sincronizado_em,
        )

    def _gravar_lote(self, lote: LoteSync, autor: Usuario) -> ResultadoLote:
        ja_existem = self.registros.ids_existentes(item.id for item in lote.registros)
        especies = self.especies.ids_existentes({item.especie_id for item in lote.registros})
        resultado = ResultadoLote(criados=[], ignorados=[], erros=[])
        for item in lote.registros:
            if item.id in ja_existem:
                resultado.ignorados.append(item.id)
            elif item.especie_id not in especies:
                resultado.erros.append(ErroLote(id=item.id, motivo="Espécie não encontrada"))
            else:
                self.db.add(
                    Registro(
                        **item.model_dump(), coletor_id=autor.id, status=StatusRegistro.PENDENTE
                    )
                )
                ja_existem.add(item.id)
                resultado.criados.append(item.id)
        self.db.commit()
        return resultado
