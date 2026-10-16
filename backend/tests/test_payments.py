from io import BytesIO
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ActorType, InvoiceStatus, Role
from app.models import BankTransaction, Contract, Document, Event, Payment, PaymentAttribution
from app.document_crypto import decrypt_document_content
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_bank_statement_proposal_confirmation_is_supervised_and_idempotent(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="bank-match", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "BANK-001")
    invoice.payer.rut = "76086428-5"
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    content = (
        "id movimiento,fecha,monto,descripcion,rut contraparte,moneda\n"
        "TX-BANK-001,2026-02-10,100000,Transferencia factura BANK-001,76086428-5,CLP\n"
    ).encode("utf-8")
    preview = client.post(
        "/api/v1/payments/bank-statements",
        data={"client_id": str(tenant.id), "commit": "false"},
        files={"file": ("cartola.csv", BytesIO(content), "text/csv")},
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.json()["can_commit"] is True
    imported = client.post(
        "/api/v1/payments/bank-statements",
        data={"client_id": str(tenant.id), "commit": "true"},
        files={"file": ("cartola.csv", BytesIO(content), "text/csv")},
        headers=headers,
    )
    assert imported.status_code == 200
    assert imported.json()["imported_count"] == 1
    assert imported.json()["proposals_created"] >= 1
    proposals = client.get(
        f"/api/v1/payments/reconciliation-proposals?client_id={tenant.id}&status=pending",
        headers=headers,
    ).json()
    proposal = proposals[0]
    assert proposal["score"] == "100.00"
    assert proposal["invoices"][0]["folio"] == invoice.folio
    confirmed = client.post(
        f"/api/v1/payments/reconciliation-proposals/{proposal['id']}/decision",
        json={
            "client_id": str(tenant.id),
            "decision": "confirmed",
            "note": "RUT, monto y fecha revisados por operador.",
        },
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID
    payment = db.scalar(
        select(Payment).where(Payment.bank_transaction_id == proposal["bank_transaction_id"])
    )
    assert payment is not None
    assert payment.verified is True
    assert payment.source == "bank_statement"
    transaction = db.get(BankTransaction, payment.bank_transaction_id)
    assert transaction is not None and transaction.status == "matched"
    repeated = client.post(
        f"/api/v1/payments/reconciliation-proposals/{proposal['id']}/decision",
        json={"client_id": str(tenant.id), "decision": "confirmed"},
        headers=headers,
    )
    assert repeated.status_code == 409
    assert db.scalar(
        select(Event).where(
            Event.invoice_id == invoice.id,
            Event.event_type == "reconciliation.confirmed",
        )
    ) is not None


def test_manual_payment_requires_evidence_and_does_not_duplicate(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="manual-payment", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "MAN-001")
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    form = {
        "client_id": str(tenant.id),
        "invoice_id": str(invoice.id),
        "amount": "100000",
        "paid_on": "2026-02-12",
        "reference": "COMPROBANTE-MAN-001",
    }
    evidence = b"comprobante ficticio de transferencia"
    created = client.post(
        "/api/v1/payments/manual",
        data=form,
        files={"evidence": ("comprobante-MAN-001.txt", BytesIO(evidence), "text/plain")},
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["verified"] is True
    assert created.json()["evidence_document_id"] is not None
    document = db.get(Document, uuid.UUID(created.json()["evidence_document_id"]))
    assert document is not None
    assert document.content != evidence
    assert document.encryption_version == "aesgcm-v1"
    assert decrypt_document_content(document) == evidence
    repeated = client.post(
        "/api/v1/payments/manual",
        data=form,
        files={"evidence": ("comprobante-MAN-001.txt", BytesIO(evidence), "text/plain")},
        headers=headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == created.json()["id"]
    assert len(
        list(db.scalars(select(Payment).where(Payment.invoice_id == invoice.id)))
    ) == 1


def test_payment_attribution_freezes_contract_rule_and_monthly_report(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="commission", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "COM-001")
    invoice.due_on = date.today() - timedelta(days=5)
    contract = Contract(
        client_id=tenant.id,
        version=1,
        active=True,
        rules={
            "commission": {
                "preventive_percent": "2.5",
                "recovery_percent": "7.5",
            }
        },
    )
    db.add(contract)
    db.add(
        Event(
            client_id=tenant.id,
            invoice_id=invoice.id,
            event_type="workflow.action_ready",
            actor_type=ActorType.SYSTEM,
            mode="automatic",
            payload={"test": True},
        )
    )
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    form = {
        "client_id": str(tenant.id),
        "invoice_id": str(invoice.id),
        "amount": "100000",
        "paid_on": date.today().isoformat(),
        "reference": "COMISION-COM-001",
    }
    created = client.post(
        "/api/v1/payments/manual",
        data=form,
        files={"evidence": ("comprobante.txt", BytesIO(b"evidencia ficticia"), "text/plain")},
        headers=headers,
    )
    assert created.status_code == 200
    attribution = db.scalar(
        select(PaymentAttribution).where(
            PaymentAttribution.payment_id == uuid.UUID(created.json()["id"])
        )
    )
    assert attribution is not None
    assert attribution.contract_id == contract.id
    assert attribution.category == "arrears_recovery"
    assert attribution.percentage == Decimal("7.5000")
    assert attribution.commission_amount == Decimal("7500.00")
    preventive_invoice = create_invoice(db, tenant, "COM-002")
    preventive_invoice.due_on = date.today() + timedelta(days=2)
    db.add(
        Event(
            client_id=tenant.id,
            invoice_id=preventive_invoice.id,
            event_type="payability.preventive_confirmation_changed",
            actor_type=ActorType.HUMAN,
            actor_id=admin.id,
            mode="manual",
            payload={"confirmed": True},
        )
    )
    db.commit()
    preventive = client.post(
        "/api/v1/payments/manual",
        data={
            **form,
            "invoice_id": str(preventive_invoice.id),
            "reference": "COMISION-COM-002",
        },
        files={"evidence": ("preventivo.txt", BytesIO(b"evidencia preventiva"), "text/plain")},
        headers=headers,
    )
    assert preventive.status_code == 200
    preventive_attribution = db.scalar(
        select(PaymentAttribution).where(
            PaymentAttribution.payment_id == uuid.UUID(preventive.json()["id"])
        )
    )
    assert preventive_attribution is not None
    assert preventive_attribution.category == "preventive_on_time"
    assert preventive_attribution.percentage == Decimal("2.5000")
    assert preventive_attribution.commission_amount == Decimal("2500.00")
    period = date.today().strftime("%Y-%m")
    report = client.get(
        f"/api/v1/payments/commission-report?client_id={tenant.id}&period={period}",
        headers=headers,
    )
    assert report.status_code == 200
    assert report.json()["totals"]["commission_amount"] == "10000.00"
    assert {item["category"] for item in report.json()["details"]} == {
        "arrears_recovery",
        "preventive_on_time",
    }
    exported = client.get(
        f"/api/v1/payments/commission-report.csv?client_id={tenant.id}&period={period}",
        headers=headers,
    )
    assert exported.status_code == 200
    assert "COM-001" in exported.text
    assert "7500.00" in exported.text
