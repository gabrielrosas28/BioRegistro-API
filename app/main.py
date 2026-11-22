from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.nome_app,
    version="1.0.0",
    description=(
        "Registro de observações de campo sobre a sociobiodiversidade, "
        "com validação por especialistas e sincronização offline."
    ),
)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
