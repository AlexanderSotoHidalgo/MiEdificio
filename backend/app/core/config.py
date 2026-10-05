from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MiEdificio API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://miedificio:miedificio_local@db:5432/miedificio"
    jwt_secret: str = "local-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    upload_dir: Path = Path("/data/uploads")
    max_upload_mb: int = 8
    seed_demo_data: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

