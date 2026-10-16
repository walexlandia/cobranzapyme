from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Recupera API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://recupera:recupera_dev_only@db:5432/recupera"
    jwt_secret: str = Field(
        default="local-development-secret-change-before-pilot",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    document_encryption_key: str = Field(
        default="local-document-key-change-before-pilot-2026",
        min_length=32,
    )
    minio_endpoint: str = "minio:9000"
    minio_secure: bool = False
    minio_bucket: str = "recupera-documents"
    demo_admin_email: str = "admin@recupera.local"
    demo_admin_password: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

