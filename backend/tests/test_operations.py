from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain import Role
from app.observability import RuntimeTelemetry
from tests.conftest import create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_observability_is_admin_only_and_aggregate(
    client: TestClient, db: Session
) -> None:
    _, admin = create_tenant_user(db, suffix="ops-admin", role=Role.ADMIN)
    _, operator = create_tenant_user(db, suffix="ops-operator", role=Role.OPERATOR)

    forbidden = client.get(
        "/api/v1/operations/observability",
        headers={"Authorization": f"Bearer {_token(client, operator.email)}"},
    )
    response = client.get(
        "/api/v1/operations/observability",
        headers={"Authorization": f"Bearer {_token(client, admin.email)}"},
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] in {"healthy", "warning", "critical"}
    assert "pending_jobs" in payload["workload"]
    assert "total_requests" in payload["runtime"]
    serialized = response.text.lower()
    assert "email" not in serialized
    assert "client_id" not in serialized


def test_runtime_telemetry_uses_bounded_dimensions() -> None:
    telemetry = RuntimeTelemetry()
    first = telemetry.begin()
    telemetry.finish(first, 204)
    second = telemetry.begin()
    telemetry.finish(second, 503)

    snapshot = telemetry.snapshot()
    assert snapshot["total_requests"] == 2
    assert snapshot["inflight_requests"] == 0
    assert snapshot["status_families"]["2xx"] == 1
    assert snapshot["status_families"]["5xx"] == 1
    assert set(snapshot["latency_buckets"]) == {
        "lt_100_ms",
        "100_to_499_ms",
        "500_to_1999_ms",
        "gte_2000_ms",
    }
