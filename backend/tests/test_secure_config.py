import pytest
from pydantic import ValidationError

from app.config import Settings


def _safe_settings(**overrides: str) -> dict[str, str]:
    values = {
        "environment": "pilot",
        "database_url": "postgresql+psycopg://app:strong-password@db:5432/recupera",
        "jwt_secret": "jwt-secret-with-more-than-thirty-two-characters",
        "document_encryption_key": "document-key-with-more-than-thirty-two-chars",
        "report_anonymization_key": "report-key-with-more-than-thirty-two-characters",
        "demo_admin_password": "admin-password-not-used-anywhere-else",
        "cors_origins": "",
    }
    values.update(overrides)
    return values


def test_pilot_settings_accept_independent_non_default_secrets() -> None:
    settings = Settings(_env_file=None, **_safe_settings())
    assert settings.environment == "pilot"
    assert settings.cors_origin_list == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret": "local-development-secret-change-before-pilot"},
        {
            "report_anonymization_key": (
                "document-key-with-more-than-thirty-two-chars"
            )
        },
        {"cors_origins": "http://localhost:3000"},
        {"cors_origins": "*"},
        {"app_version": "0.0.0"},
        {"demo_admin_password": "short-password"},
    ],
)
def test_pilot_settings_reject_unsafe_values(overrides: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="Configuración insegura"):
        Settings(_env_file=None, **_safe_settings(**overrides))
