from collections.abc import Mapping


REAL_ENVIRONMENTS = {"pilot", "production"}
PLACEHOLDER_MARKERS = (
    "replace-with",
    "changeme",
    "dev_only",
    "development-secret",
    "local-document-key",
    "local-report-key",
)


def real_environment_issues(values: Mapping[str, str]) -> list[str]:
    if values.get("ENVIRONMENT", "").lower() not in REAL_ENVIRONMENTS:
        return []
    secret_keys = (
        "DATABASE_URL",
        "JWT_SECRET",
        "DOCUMENT_ENCRYPTION_KEY",
        "REPORT_ANONYMIZATION_KEY",
        "DEMO_ADMIN_PASSWORD",
    )
    issues = [
        key
        for key in secret_keys
        if any(marker in values.get(key, "").lower() for marker in PLACEHOLDER_MARKERS)
    ]
    if len(values.get("DEMO_ADMIN_PASSWORD", "")) < 16:
        issues.append("DEMO_ADMIN_PASSWORD")
    crypto_values = {
        values.get("JWT_SECRET", ""),
        values.get("DOCUMENT_ENCRYPTION_KEY", ""),
        values.get("REPORT_ANONYMIZATION_KEY", ""),
    }
    if "" in crypto_values or len(crypto_values) != 3:
        issues.append("INDEPENDENT_CRYPTO_KEYS")
    cors_origins = [
        item.strip()
        for item in values.get("CORS_ORIGINS", "").split(",")
        if item.strip()
    ]
    if any(origin == "*" or "localhost" in origin for origin in cors_origins):
        issues.append("CORS_ORIGINS")
    return sorted(set(issues))
