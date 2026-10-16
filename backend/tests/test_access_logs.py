import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import DataAccessLog
from tests.conftest import create_tenant_user


def test_authenticated_request_creates_minimized_access_log(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="access-log", role=Role.ADMIN)
    token = client.post(
        "/api/v1/auth/token",
        data={"username": admin.email, "password": "TestPassword123!"},
    ).json()["access_token"]
    response = client.get(
        f"/api/v1/invoices?client_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    log = db.scalar(
        select(DataAccessLog)
        .where(DataAccessLog.request_id == uuid.UUID(response.headers["x-request-id"]))
    )
    assert log is not None
    assert log.user_id == admin.id
    assert log.client_id == tenant.id
    assert log.path == "/api/v1/invoices"
    assert log.status_code == 200
    assert log.remote_hash is not None
