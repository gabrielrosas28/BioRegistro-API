from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers import auth, especies, registros, usuarios
from app.services.erros import ErroNegocio, NaoAutenticado

settings = get_settings()

app = FastAPI(
    title=settings.nome_app,
    version="1.0.0",
    description=(
        "Registro de observações de campo sobre a sociobiodiversidade, "
        "com validação por especialistas e sincronização offline."
    ),
)


@app.exception_handler(ErroNegocio)
def tratar_erro_negocio(_: Request, erro: ErroNegocio) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(erro, NaoAutenticado) else None
    return JSONResponse({"detail": erro.mensagem}, status_code=erro.status_code, headers=headers)


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(especies.router)
app.include_router(registros.router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
