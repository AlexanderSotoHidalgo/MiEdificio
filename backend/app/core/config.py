from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MiEdificio API"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://miedificio:miedificio_local@db:5432/miedificio"
    jwt_secret: str = "local-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    storage_backend: Literal["local", "minio"] = "local"
    upload_dir: Path = Path("/data/uploads")
    max_upload_mb: int = Field(default=5, gt=0, le=5)
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "miedificio-receipts"
    minio_secure: bool = False
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, gt=0, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    email_from: str = "MiEdificio <no-reply@miedificio.local>"
    frontend_url: str = "http://localhost:5173"
    initial_admin_email: str = "admin@miedificio.pe"
    initial_admin_password: str = "Admin123!"
    initial_admin_name: str = "Administración MiEdificio"
    initial_building_name: str = "Condominio Los Cedros"
    initial_building_address: str = "Av. Los Cedros 245"
    initial_building_district: str = "Santiago de Surco"
    seed_demo_data: bool = False
    run_migrations: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            insecure_secrets = {"local-only-secret-change-me", "change-me", ""}
            if self.jwt_secret in insecure_secrets or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must contain at least 32 non-default characters")
            if self.seed_demo_data:
                raise ValueError("SEED_DEMO_DATA must be false in production")
        if self.storage_backend == "minio" and not (
            self.minio_access_key and self.minio_secret_key
        ):
            raise ValueError("MinIO credentials are required when STORAGE_BACKEND=minio")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
