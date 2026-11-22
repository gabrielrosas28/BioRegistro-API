class ErroNegocio(Exception):
    status_code = 400

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoAutenticado(ErroNegocio):
    status_code = 401


class AcessoNegado(ErroNegocio):
    status_code = 403


class NaoEncontrado(ErroNegocio):
    status_code = 404


class Conflito(ErroNegocio):
    status_code = 409


class DadosInvalidos(ErroNegocio):
    status_code = 422
