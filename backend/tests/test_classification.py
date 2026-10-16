import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import Contact, Event, ExceptionCase, MessageClassification
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_inbound_response_is_classified_extracted_and_queued_for_review(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="classification", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "CLASS-001")
    contact = Contact(
        client_id=tenant.id,
        payer_id=invoice.payer_id,
        name="Carolina Pagos",
        role="accounts_payable",
        email="carolina.classification@example.test",
        phone="+56960001111",
    )
    db.add(contact)
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}

    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "classification-demo-001",
            "sender": contact.email,
            "subject": "Programación factura CLASS-001",
            "body": (
                "El pago quedó programado para el 24/10/2026 por CLP 1.250.000. "
                "La referencia es OC-7788 y HES-9922."
            ),
            "invoice_folios": [invoice.folio],
        },
        headers=headers,
    )
    queue = client.get(
        f"/api/v1/exceptions?client_id={tenant.id}&status=open", headers=headers
    )

    assert inbound.status_code == 200
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    case = queue.json()[0]
    assert case["kind"] == "supervised_review"
    assert case["classification"]["category"] == "payment_scheduled"
    assert Decimal(case["classification"]["confidence"]) >= Decimal("0.9000")
    assert case["classification"]["extracted_data"] == {
        "payment_dates": ["2026-10-24"],
        "amounts": [1250000],
        "purchase_orders": ["7788"],
        "hes_numbers": ["9922"],
        "receipt_document_ids": [],
    }
    detail = client.get(
        f"/api/v1/exceptions/{case['id']}?client_id={tenant.id}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["context"]["invoice"]["folio"] == "CLASS-001"
    assert any(
        event["event_type"] == "classification.created"
        for event in detail.json()["context"]["events"]
    )


def test_human_review_creates_immutable_revision_and_records_time(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="classification-review", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "CLASS-002")
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "classification-demo-002",
            "sender": "desconocido@example.test",
            "body": "Pagaremos el 30/10/2026.",
            "invoice_folios": [invoice.folio],
        },
        headers=headers,
    )
    assert inbound.status_code == 200
    case = client.get(
        f"/api/v1/exceptions?client_id={tenant.id}&status=open", headers=headers
    ).json()[0]
    original = case["classification"]

    reviewed = client.post(
        f"/api/v1/exceptions/{case['id']}/review",
        json={
            "client_id": str(tenant.id),
            "category": "payment_promise",
            "extracted_data": {
                **original["extracted_data"],
                "payment_dates": ["2026-10-30"],
            },
            "human_minutes": "7.50",
            "note": "Fecha y categoría confirmadas telefónicamente.",
        },
        headers=headers,
    )

    assert reviewed.status_code == 200
    payload = reviewed.json()
    assert payload["status"] == "resolved"
    assert Decimal(payload["human_minutes"]) == Decimal("7.50")
    assert payload["classification"]["version"] == 2
    assert payload["classification"]["decision_source"] == "human"
    assert payload["classification"]["supersedes_id"] == original["id"]
    history = list(
        db.scalars(
            select(MessageClassification)
            .where(MessageClassification.message_id == uuid.UUID(inbound.json()["id"]))
            .order_by(MessageClassification.version)
        )
    )
    assert [item.category for item in history] == [
        original["category"],
        "payment_promise",
    ]
    assert db.scalar(
        select(Event).where(
            Event.invoice_id == invoice.id,
            Event.event_type == "classification.human_decision",
        )
    ) is not None
    assert db.scalar(select(ExceptionCase).where(ExceptionCase.id == uuid.UUID(case["id"]))).status == "resolved"


def test_unmatched_response_gets_high_priority_correlation_review(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="classification-unmatched", role=Role.ADMIN)
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "whatsapp",
            "provider_id": "classification-demo-003",
            "sender": "+56999998888",
            "body": "Gracias por la información.",
            "invoice_folios": ["NO-EXISTE"],
        },
        headers=headers,
    )
    assert inbound.status_code == 200
    case = client.get(
        f"/api/v1/exceptions?client_id={tenant.id}&status=open", headers=headers
    ).json()[0]
    assert case["kind"] == "correlation_review"
    assert case["classification"]["category"] == "other"
    assert case["priority"] >= 90
