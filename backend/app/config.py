from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config_validation import real_environment_issues
from app.version import APP_VERSION


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Recupera API"
    app_version: str = APP_VERSION
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
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
    report_anonymization_key: str = Field(
        default="local-report-key-change-before-real-pilot-2026",
        min_length=32,
    )
    minio_endpoint: str = "minio:9000"
    minio_secure: bool = False
    minio_bucket: str = "recupera-documents"
    demo_admin_email: str = "admin@recupera.local"
    demo_admin_password: str = "ChangeMe123!"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_real_environment(self) -> "Settings":
        issues = real_environment_issues({
            "ENVIRONMENT": self.environment,
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "DOCUMENT_ENCRYPTION_KEY": self.document_encryption_key,
            "REPORT_ANONYMIZATION_KEY": self.report_anonymization_key,
            "DEMO_ADMIN_PASSWORD": self.demo_admin_password,
            "CORS_ORIGINS": self.cors_origins,
        })
        if self.app_version != APP_VERSION:
            issues.append("APP_VERSION")
        if issues:
            raise ValueError(
                "Configuración insegura para pilot/production: "
                + ", ".join(issues)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

