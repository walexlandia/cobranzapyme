from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_client_sees_only_its_own_invoices(client: TestClient, db: Session) -> None:
    tenant_a, user_a = create_tenant_user(db, suffix="a")
    tenant_b, _ = create_tenant_user(db, suffix="b")
    invoice_a = create_invoice(db, tenant_a, "A-ONLY")
    create_invoice(db, tenant_b, "B-ONLY")
    token = _token(client, user_a.email)

    response = client.get("/api/v1/invoices", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(invoice_a.id)]


def test_client_cannot_request_another_tenant(client: TestClient, db: Session) -> None:
    _, user_a = create_tenant_user(db, suffix="cross-a")
    tenant_b, _ = create_tenant_user(db, suffix="cross-b")
    token = _token(client, user_a.email)

    response = client.get(
        f"/api/v1/invoices?client_id={tenant_b.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

