from datetime import datetime, timezone
from decimal import Decimal
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import (
    Contact,
    Contract,
    Document,
    Event,
    Invoice,
    Message,
    MessageInvoice,
    WorkflowJob,
)
from app.schemas import ContractRules
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _communication_job(
    db: Session,
    *,
    tenant,
    invoice,
    channel: str = "email",
    action_type: str = "payment_due",
) -> tuple[Contact, WorkflowJob]:
    tenant.sender_name = "Cobranza Demo"
    tenant.sender_email = "cobranza@example.test"
    tenant.bank_details = {
        "bank": "Banco Demo",
        "account_type": "Cuenta corriente",
        "account_number": "12345678",
        "account_holder": tenant.name,
        "rut": tenant.rut,
        "email": "pagos@example.test",
    }
    contact = Contact(
        client_id=tenant.id,
        payer_id=invoice.payer_id,
        name="Andrea Cuentas por Pagar",
        role="accounts_payable",
        email="andrea@example.test",
        phone="+56911112222",
    )
    contract = Contract(
        client_id=tenant.id,
        version=1,
        rules=ContractRules(channels=[channel]).model_dump(mode="json"),
        active=True,
    )
    db.add_all([contact, contract])
    db.flush()
    job = WorkflowJob(
        client_id=tenant.id,
        invoice_id=invoice.id,
        payer_id=invoice.payer_id,
        recipient_contact_id=contact.id,
        contract_id=contract.id,
        idempotency_key=f"communication-{invoice.folio}-{channel}-{action_type}",
        action_type=action_type,
        stage="due",
        status="done",
        scheduled_for=datetime(2026, 10, 15, 13, 0, tzinfo=timezone.utc),
        processed_at=datetime(2026, 10, 15, 13, 0, tzinfo=timezone.utc),
        attempts=1,
        mode="manual",
        payload={
            "invoice_ids": [str(invoice.id)],
            "recipient_role": "accounts_payable",
            "missing_items": {},
        },
    )
    db.add(job)
    db.commit()
    return contact, job


def test_prepare_email_is_idempotent_and_includes_payment_data_and_attachments(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-email", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-001")
    _, job = _communication_job(db, tenant=tenant, invoice=invoice)
    db.add(
        Document(
            client_id=tenant.id,
            invoice_id=invoice.id,
            kind="invoice_pdf",
            object_key="demo/comm-001.pdf",
            original_name="factura-COMM-001.pdf",
            sha256="a" * 64,
        )
    )
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}

    first = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    )
    second = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    payload = first.json()
    assert payload["id"] == second.json()["id"]
    assert payload["status"] == "draft"
    assert payload["channel"] == "email"
    assert "COMM-001" in payload["body"]
    assert "Banco Demo" in payload["body"]
    assert payload["destination"] == "andrea@example.test"
    assert payload["attachment_names"] == ["factura-COMM-001.pdf"]
    assert db.query(Message).count() == 1


def test_simulated_delivery_records_cost_per_invoice_and_audit(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-cost", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-002")
    _, job = _communication_job(db, tenant=tenant, invoice=invoice)
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    prepared = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/communications/messages/{prepared['id']}/simulate?client_id={tenant.id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "simulated"
    assert Decimal(response.json()["messaging_cost"]) == Decimal("0.001000")
    link = db.scalar(
        select(MessageInvoice).where(
            MessageInvoice.message_id == uuid.UUID(prepared["id"])
        )
    )
    assert link is not None
    assert link.allocated_messaging_cost == Decimal("0.001000")
    assert db.scalar(
        select(Event).where(
            Event.invoice_id == invoice.id,
            Event.event_type == "communication.simulated",
        )
    ) is not None


def test_opt_out_blocks_a_pending_message(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-optout", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-003")
    contact, job = _communication_job(db, tenant=tenant, invoice=invoice)
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    prepared = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/communications/contacts/{contact.id}/opt-out",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "opted_out": True,
            "reason": "Solicitud del contacto",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["opted_out_email"] is True
    message = db.get(Message, uuid.UUID(prepared["id"]))
    assert message is not None
    assert message.status == "blocked"
    assert "email_opt_out" in message.safety_flags
    blocked_send = client.post(
        f"/api/v1/communications/messages/{message.id}/simulate?client_id={tenant.id}",
        headers=headers,
    )
    assert blocked_send.status_code == 409


def test_unsafe_template_uses_fallback_and_whatsapp_is_assisted_only(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-safety", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-004")
    _, job = _communication_job(
        db,
        tenant=tenant,
        invoice=invoice,
        channel="whatsapp_assisted",
        action_type="escalate_case",
    )
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    template = client.post(
        "/api/v1/communications/templates",
        json={
            "client_id": str(tenant.id),
            "template_key": "escalate_case",
            "channel": "whatsapp_assisted",
            "stage": "escalation",
            "recipient_role": "accounts_payable",
            "tone": "direct",
            "body_template": "Hola {recipient_name}. Iniciaremos una demanda por {invoice_summary}.",
            "approved": False,
        },
        headers=headers,
    )
    assert template.status_code == 200

    prepared = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    )

    assert prepared.status_code == 200
    payload = prepared.json()
    assert payload["status"] == "assisted_ready"
    assert payload["safety_status"] == "fallback"
    assert "legal_pressure" in payload["safety_flags"]
    assert "demanda" not in payload["body"].lower()
    assert payload["provider_payload"]["external_delivery"] is False
    assert payload["provider_payload"]["assisted_link"].startswith("https://wa.me/")


def test_inbound_email_is_idempotent_and_correlates_reply_invoice_and_attachment(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-inbound", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-005")
    contact, job = _communication_job(db, tenant=tenant, invoice=invoice)
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    outbound = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/communications/messages/{outbound['id']}/simulate?client_id={tenant.id}",
        headers=headers,
    )
    payload = {
        "client_id": str(tenant.id),
        "channel": "email",
        "provider_id": "mail-demo-005",
        "sender": contact.email,
        "in_reply_to_provider_id": f"local-sim-{outbound['id']}",
        "subject": "RE: confirmación de pago",
        "body": "Factura recibida. Pago programado para el viernes.",
        "invoice_folios": [invoice.folio],
        "attachments": [{"original_name": "comprobante-programacion.pdf"}],
    }

    first = client.post(
        "/api/v1/communications/inbound/simulate", json=payload, headers=headers
    )
    second = client.post(
        "/api/v1/communications/inbound/simulate", json=payload, headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    response = first.json()
    assert response["id"] == second.json()["id"]
    assert response["direction"] == "inbound"
    assert response["status"] == "received"
    assert response["thread_id"] == outbound["thread_id"]
    assert response["invoice_folios"] == ["COMM-005"]
    assert response["attachment_names"] == ["comprobante-programacion.pdf"]
    assert response["provider_payload"]["correlation"]["reply"] is True
    assert response["provider_payload"]["external_delivery"] is False


def test_inbound_whatsapp_uses_external_thread_and_phone_correlation(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-whatsapp-in", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-006")
    contact, job = _communication_job(
        db, tenant=tenant, invoice=invoice, channel="whatsapp_assisted"
    )
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    outbound = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    ).json()
    response = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "whatsapp",
            "provider_id": "wa-demo-006",
            "sender": contact.phone,
            "external_thread_key": "wa-thread-demo-006",
            "in_reply_to_provider_id": None,
            "body": "Sí, la factura quedó aprobada.",
            "invoice_folios": [invoice.folio],
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contact_id"] == str(contact.id)
    assert payload["thread_id"] == outbound["thread_id"]
    assert payload["channel"] == "whatsapp"
    assert payload["invoice_folios"] == ["COMM-006"]


def test_manual_response_and_local_delivery_read_state_are_audited(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-manual", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COMM-007")
    contact, job = _communication_job(db, tenant=tenant, invoice=invoice)
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    outbound = client.post(
        f"/api/v1/communications/jobs/{job.id}/prepare?client_id={tenant.id}",
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/communications/messages/{outbound['id']}/simulate?client_id={tenant.id}",
        headers=headers,
    )

    delivered = client.post(
        f"/api/v1/communications/messages/{outbound['id']}/delivery-status",
        json={"client_id": str(tenant.id), "status": "delivered"},
        headers=headers,
    )
    read = client.post(
        f"/api/v1/communications/messages/{outbound['id']}/delivery-status",
        json={"client_id": str(tenant.id), "status": "read"},
        headers=headers,
    )
    manual = client.post(
        "/api/v1/communications/manual-responses",
        json={
            "client_id": str(tenant.id),
            "contact_id": str(contact.id),
            "invoice_ids": [str(invoice.id)],
            "channel": "phone",
            "subject": "Llamada de cuentas por pagar",
            "body": "Informan que el pago se procesará el próximo viernes.",
        },
        headers=headers,
    )

    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert read.status_code == 200
    assert read.json()["status"] == "read"
    assert manual.status_code == 200
    assert manual.json()["direction"] == "inbound"
    assert manual.json()["mode"] == "manual"
    assert manual.json()["invoice_folios"] == ["COMM-007"]
    event_types = set(
        db.scalars(select(Event.event_type).where(Event.invoice_id == invoice.id))
    )
    assert "communication.delivery_status_changed" in event_types
    assert "communication.manual_response_recorded" in event_types


def test_inbound_and_manual_correlation_never_cross_client_boundaries(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="communication-isolation-a", role=Role.ADMIN)
    other_tenant, _ = create_tenant_user(
        db, suffix="communication-isolation-b", role=Role.ADMIN
    )
    own_invoice = create_invoice(db, tenant, "COMM-008-A")
    foreign_invoice = create_invoice(db, other_tenant, "COMM-008-B")
    contact, _ = _communication_job(db, tenant=tenant, invoice=own_invoice)
    db.add(
        Invoice(
            client_id=tenant.id,
            payer_id=own_invoice.payer_id,
            document_type="nota_credito",
            folio=own_invoice.folio,
            issued_on=own_invoice.issued_on,
            due_on=own_invoice.due_on,
            total_amount=Decimal("25000"),
        )
    )
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}

    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "mail-isolation-008",
            "sender": contact.email,
            "body": "Referencia recibida con un folio que no pertenece a esta pyme.",
            "invoice_folios": [foreign_invoice.folio],
        },
        headers=headers,
    )
    manual = client.post(
        "/api/v1/communications/manual-responses",
        json={
            "client_id": str(tenant.id),
            "invoice_ids": [str(foreign_invoice.id)],
            "channel": "phone",
            "body": "Este registro no debe aceptar una factura de otra pyme.",
        },
        headers=headers,
    )
    ambiguous = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "mail-ambiguous-008",
            "sender": contact.email,
            "body": "El folio coincide con más de un tipo documental.",
            "invoice_folios": [own_invoice.folio],
        },
        headers=headers,
    )

    assert inbound.status_code == 200
    assert inbound.json()["invoice_ids"] == []
    assert inbound.json()["provider_payload"]["correlation"][
        "unmatched_invoice_folios"
    ] == [foreign_invoice.folio]
    assert inbound.json()["provider_payload"]["correlation"]["needs_review"] is True
    assert manual.status_code == 409
    assert ambiguous.status_code == 200
    assert ambiguous.json()["invoice_ids"] == []
    assert ambiguous.json()["provider_payload"]["correlation"][
        "ambiguous_invoice_folios"
    ] == [own_invoice.folio]
    assert ambiguous.json()["provider_payload"]["correlation"]["needs_review"] is True
