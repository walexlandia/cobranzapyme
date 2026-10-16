from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import InvoiceStatus, Role
from app.models import PayabilityItem, Payment
from app.services.payability import ensure_checklist
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_client_portal_is_read_only_scoped_and_date_aware(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="portal")
    other_tenant, _ = create_tenant_user(db, suffix="portal-other")
    paid = create_invoice(db, tenant, "PORTAL-PAID")
    risk = create_invoice(db, tenant, "PORTAL-RISK")
    payable = create_invoice(db, tenant, "PORTAL-PAYABLE")
    create_invoice(db, other_tenant, "PORTAL-HIDDEN")
    for invoice in (paid, risk, payable):
        ensure_checklist(db, invoice)
    paid.status = InvoiceStatus.PAID
    db.add(
        Payment(
            client_id=tenant.id,
            invoice_id=paid.id,
            amount=paid.total_amount,
            paid_on=date(2026, 2, 5),
            verified=True,
            source="manual",
            reference="PORTAL-TEST",
            verified_by=client_user.id,
            idempotency_key=f"portal-test:{paid.id}",
        )
    )
    for item in db.scalars(
        select(PayabilityItem).where(PayabilityItem.invoice_id == payable.id)
    ):
        if item.required and item.blocks_payability:
            item.status = "fulfilled"
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}

    response = client.get(
        "/api/v1/client-portal/summary?as_of=2026-02-08",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["client_id"] == str(tenant.id)
    assert {row["folio"] for row in payload["invoices"]} == {
        "PORTAL-PAID",
        "PORTAL-RISK",
        "PORTAL-PAYABLE",
    }
    assert payload["totals"]["paid_count"] == 1
    assert payload["totals"]["payable_count"] == 1
    assert payload["totals"]["at_risk_count"] == 1
    assert payload["totals"]["paid_amount"] == "100000.00"
    assert payload["totals"]["outstanding_amount"] == "200000.00"
    assert client.get(
        f"/api/v1/client-portal/summary?client_id={other_tenant.id}",
        headers=headers,
    ).status_code == 403


def test_operator_generates_weekly_json_and_csv_report(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="portal-report", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "WEEKLY-001")
    ensure_checklist(db, invoice)
    db.add(
        Payment(
            client_id=tenant.id,
            invoice_id=invoice.id,
            amount=Decimal("25000"),
            paid_on=date(2026, 2, 6),
            verified=True,
            source="bank_statement",
            reference="WEEKLY-TX",
            verified_by=admin.id,
            idempotency_key=f"weekly-test:{invoice.id}",
        )
    )
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    query = f"client_id={tenant.id}&week_ending=2026-02-08"

    report = client.get(f"/api/v1/client-portal/weekly-report?{query}", headers=headers)
    csv_report = client.get(
        f"/api/v1/client-portal/weekly-report.csv?{query}", headers=headers
    )

    assert report.status_code == 200
    assert report.json()["period_start"] == "2026-02-02"
    assert report.json()["payments_this_week_count"] == 1
    assert report.json()["payments_this_week_amount"] == "25000.00"
    assert csv_report.status_code == 200
    assert csv_report.content.startswith(b"\xef\xbb\xbf")
    assert "WEEKLY-001" in csv_report.text
    assert client.get("/api/v1/client-portal/summary", headers=headers).status_code == 422
