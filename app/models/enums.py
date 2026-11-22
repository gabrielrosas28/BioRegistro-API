from enum import StrEnum


class Papel(StrEnum):
    COLETOR = "coletor"
    VALIDADOR = "validador"
    ADMIN = "admin"


class StatusRegistro(StrEnum):
    PENDENTE = "pendente"
    VALIDADO = "validado"
    REJEITADO = "rejeitado"


class Decisao(StrEnum):
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"
