from typing import Annotated

from pydantic import BaseModel, StringConstraints

Texto120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Texto160 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class Erro(BaseModel):
    detail: str
