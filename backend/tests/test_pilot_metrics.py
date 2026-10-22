from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain import ActorType, Role
from app.models import (
    DelayCause,
    Event,
    ExceptionCase,
    Message,
    MessageInvoice,
    PayabilityItem,
    Payment,
    PaymentAttribution,
)
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_pilot_metrics_are_auditable_exportable_and_role_scoped(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="pilot-metrics")
    _, admin = create_tenant_user(db, suffix="pilot-metrics-admin", role=Role.ADMIN)
    tenant.baseline_dso = Decimal("45")
    tenant.baseline_on_time_percent = Decimal("35")
    on_time_invoice = create_invoice(db, tenant, "METRIC-ON-TIME")
    late_invoice = create_invoice(db, tenant, "METRIC-LATE")
    created_at = datetime(2026, 2, 3, 12, tzinfo=timezone.utc)
    on_time_payment = Payment(
        client_id=tenant.id,
        invoice_id=on_time_invoice.id,
        amount=Decimal("100000"),
        paid_on=date(2026, 2, 5),
        verified=True,
        source="manual",
        reference="METRIC-001",
        idempotency_key="metric-payment-001",
        created_at=created_at,
    )
    late_payment = Payment(
        client_id=tenant.id,
        invoice_id=late_invoice.id,
        amount=Decimal("100000"),
        paid_on=date(2026, 2, 20),
        verified=True,
        source="bank_statement",
        reference="METRIC-002",
        idempotency_key="metric-payment-002",
        created_at=created_at,
    )
    db.add_all([on_time_payment, late_payment])
    db.flush()
    db.add_all(
        [
            PaymentAttribution(
                client_id=tenant.id,
                payment_id=on_time_payment.id,
                invoice_id=on_time_invoice.id,
                category="preventive",
                percentage=Decimal("1"),
                base_amount=Decimal("100000"),
                commission_amount=Decimal("1000"),
                rationale={"fixture": True},
            ),
            PaymentAttribution(
                client_id=tenant.id,
                payment_id=late_payment.id,
                invoice_id=late_invoice.id,
                category="recovery",
                percentage=Decimal("2"),
                base_amount=Decimal("100000"),
                commission_amount=Decimal("2000"),
                rationale={"fixture": True},
            ),
            Event(
                client_id=tenant.id,
                invoice_id=on_time_invoice.id,
                event_type="workflow.action_ready",
                actor_type=ActorType.SYSTEM,
                mode="automatic",
                payload={"fixture": True},
                created_at=created_at,
            ),
            Event(
                client_id=tenant.id,
                invoice_id=late_invoice.id,
                event_type="workflow.action_ready",
                actor_type=ActorType.SYSTEM,
                mode="automatic",
                payload={"fixture": True},
                created_at=created_at,
            ),
            ExceptionCase(
                client_id=tenant.id,
                invoice_id=late_invoice.id,
                kind="payment_commitment",
                status="resolved",
                priority=10,
                detail={"fixture": True},
                human_minutes=Decimal("30"),
                human_minutes_measured=True,
                resolution={"fixture": True},
                created_at=created_at,
            ),
            DelayCause(
                client_id=tenant.id,
                invoice_id=late_invoice.id,
                category="purchase_order",
                detail="Dato sintético",
                source="test_fixture",
                created_at=created_at,
            ),
            PayabilityItem(
                client_id=tenant.id,
                invoice_id=late_invoice.id,
                item_type="purchase_order",
                label="Orden de compra",
                status="fulfilled",
                required=True,
                blocks_payability=True,
                responsible_role="client",
                evidence={"fixture": True},
                created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
            ),
        ]
    )
    automatic_message = Message(
        client_id=tenant.id,
        invoice_id=on_time_invoice.id,
        payer_id=on_time_invoice.payer_id,
        channel="email",
        direction="outbound",
        mode="automatic",
        body="Mensaje automático sintético",
        status="sent",
        idempotency_key="metric-message-automatic",
        created_at=created_at,
    )
    manual_message = Message(
        client_id=tenant.id,
        invoice_id=late_invoice.id,
        payer_id=late_invoice.payer_id,
        channel="email",
        direction="outbound",
        mode="manual",
        body="Mensaje manual sintético",
        status="sent",
        idempotency_key="metric-message-manual",
        created_at=created_at,
    )
    db.add_all([automatic_message, manual_message])
    db.flush()
    db.add_all(
        [
            MessageInvoice(
                client_id=tenant.id,
                message_id=automatic_message.id,
                invoice_id=on_time_invoice.id,
                allocated_llm_cost=Decimal("0.10"),
                allocated_messaging_cost=Decimal("0.02"),
                created_at=created_at,
            ),
            MessageInvoice(
                client_id=tenant.id,
                message_id=manual_message.id,
                invoice_id=late_invoice.id,
                allocated_llm_cost=Decimal("0.05"),
                allocated_messaging_cost=Decimal("0.01"),
                created_at=created_at,
            ),
        ]
    )
    db.commit()

    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    query = f"client_id={tenant.id}&date_from=2026-02-01&date_to=2026-02-28"
    response = client.get(f"/api/v1/metrics/pilot?{query}", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcomes"]["managed_invoices"] == 2
    assert payload["outcomes"]["settled_invoices"] == 2
    assert payload["outcomes"]["average_dso"] == "33.50"
    assert payload["outcomes"]["on_time_percent"] == "50.00"
    assert payload["outcomes"]["recovered_amount"] == "100000.00"
    assert payload["operations"]["human_minutes"] == "30.00"
    assert payload["operations"]["messages"]["automatic_percent"] == "50.00"
    assert payload["economics"]["commission_clp"] == "3000.00"
    assert payload["economics"]["technology_cost_clp"] == "171.00"
    assert payload["economics"]["margin_clp"] == "-1171.00"
    assert payload["delay_causes"][0]["category"] == "purchase_order"
    assert payload["resolution_times"][0]["average_hours"] == "24.00"

    exported = client.get(f"/api/v1/metrics/pilot.csv?{query}", headers=admin_headers)
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "managed_invoices" in exported.text
    assert "resolution_time,purchase_order" in exported.text
    assert client.get(f"/api/v1/metrics/pilot?{query}", headers=client_headers).status_code == 403
    trend = client.get(
        "/api/v1/metrics/client-trend?date_from=2026-02-01&date_to=2026-02-28",
        headers=client_headers,
    )
    assert trend.status_code == 200
    assert trend.json()["client_id"] == str(tenant.id)
    assert "economics" not in trend.json()
