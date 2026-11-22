from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nome_app: str = "BioRegistro API"
    database_url: str = "sqlite:///./bioregistro.db"
    secret_key: str = "troque-esta-chave-antes-de-publicar-a-api"
    jwt_algoritmo: str = "HS256"
    jwt_expiracao_minutos: int = 60
    bcrypt_rounds: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
