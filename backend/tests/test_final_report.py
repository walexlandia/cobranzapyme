import json
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import Payment
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_final_report_is_anonymized_reproducible_and_cannot_approve_synthetic_g4(
    client: TestClient, db: Session
) -> None:
    first, first_user = create_tenant_user(db, suffix="final-report-private-a")
    second, _ = create_tenant_user(db, suffix="final-report-private-b")
    _, admin = create_tenant_user(db, suffix="final-report-admin", role=Role.ADMIN)
    first.baseline_dso = Decimal("50")
    first.baseline_on_time_percent = Decimal("20")
    second.baseline_dso = Decimal("45")
    second.baseline_on_time_percent = Decimal("30")
    first_invoice = create_invoice(db, first, "PRIVATE-FOLIO-A")
    second_invoice = create_invoice(db, second, "PRIVATE-FOLIO-B")
    first_payer_name = first_invoice.payer.legal_name
    db.add_all(
        [
            Payment(
                client_id=first.id,
                invoice_id=first_invoice.id,
                amount=Decimal("100000"),
                paid_on=date(2026, 2, 5),
                verified=True,
                source="manual",
                idempotency_key="final-report-payment-a",
            ),
            Payment(
                client_id=second.id,
                invoice_id=second_invoice.id,
                amount=Decimal("100000"),
                paid_on=date(2026, 2, 6),
                verified=True,
                source="manual",
                idempotency_key="final-report-payment-b",
            ),
        ]
    )
    db.commit()
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, first_user.email)}"}
    query = (
        "date_from=2026-01-01&date_to=2026-02-28&minimum_group_size=1"
        "&evidence_kind=synthetic"
    )

    response = client.get(f"/api/v1/metrics/final-report?{query}", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload)
    assert payload["schema_version"] == "fase-8.1-v1"
    assert payload["g4"]["ready"] is False
    assert payload["g4"]["recommendation"] == "pending"
    assert payload["fingerprint_sha256"]
    assert any(row["dimension"] == "payer" for row in payload["segments"])
    assert first.name not in serialized
    assert first.rut not in serialized
    assert first_payer_name not in serialized
    assert "PRIVATE-FOLIO-A" not in serialized
    assert str(first.id) not in serialized
    repeated = client.get(f"/api/v1/metrics/final-report?{query}", headers=admin_headers)
    assert repeated.status_code == 200
    assert repeated.json()["fingerprint_sha256"] == payload["fingerprint_sha256"]

    exported = client.get(
        f"/api/v1/metrics/anonymized-dataset.csv?{query}", headers=admin_headers
    )
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "payer,PAGADOR-" in exported.text
    assert first.name not in exported.text
    assert first.rut not in exported.text

    document = client.get(f"/api/v1/metrics/final-report.md?{query}", headers=admin_headers)
    assert document.status_code == 200
    assert "Informe final V-10" in document.text
    assert "Pendiente de evidencia suficiente" in document.text
    assert first.name not in document.text
    assert client.get(
        f"/api/v1/metrics/final-report?{query}", headers=client_headers
    ).status_code == 403
