import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.document_crypto import decrypt_document_content
from app.domain import Role
from app.models import (
    ClientDocumentSubmission,
    Document,
    Event,
    PayabilityItem,
)
from app.services.payability import ensure_checklist
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_client_upload_is_encrypted_deduplicated_and_scoped(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="document-client")
    other_tenant, _ = create_tenant_user(db, suffix="document-other")
    invoice = create_invoice(db, tenant, "DOC-001")
    ensure_checklist(db, invoice)
    db.commit()
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.responsible_role == "client",
            PayabilityItem.required.is_(True),
        )
    )
    assert item is not None
    headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    data = {"invoice_id": str(invoice.id), "payability_item_id": str(item.id)}
    content = b"Documento sintetico para prueba de carga segura"

    first = client.post(
        "/api/v1/client-portal/documents",
        data=data,
        files={"document": ("orden-compra.pdf", content, "application/pdf")},
        headers=headers,
    )
    duplicate = client.post(
        "/api/v1/client-portal/documents",
        data=data,
        files={"document": ("orden-compra.pdf", content, "application/pdf")},
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert db.scalar(
        select(func.count(ClientDocumentSubmission.id)).where(
            ClientDocumentSubmission.payability_item_id == item.id
        )
    ) == 1
    submission = db.get(ClientDocumentSubmission, uuid.UUID(first.json()["id"]))
    assert submission is not None
    document = db.get(Document, submission.document_id)
    assert document is not None
    assert document.content != content
    assert document.encryption_version == "aesgcm-v1"
    assert decrypt_document_content(document) == content
    assert client.get(
        f"/api/v1/client-portal/document-submissions?client_id={other_tenant.id}",
        headers=headers,
    ).status_code == 403


def test_operator_accepts_document_and_completes_item_with_audit(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="document-review-client")
    _, operator = create_tenant_user(db, suffix="document-review-operator", role=Role.OPERATOR)
    invoice = create_invoice(db, tenant, "DOC-REVIEW-001")
    ensure_checklist(db, invoice)
    db.commit()
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.responsible_role == "client",
            PayabilityItem.required.is_(True),
        )
    )
    assert item is not None
    client_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    uploaded = client.post(
        "/api/v1/client-portal/documents",
        data={"invoice_id": str(invoice.id), "payability_item_id": str(item.id)},
        files={"document": ("respaldo.png", b"imagen-sintetica", "image/png")},
        headers=client_headers,
    )
    operator_headers = {"Authorization": f"Bearer {_token(client, operator.email)}"}
    pending = client.get(
        f"/api/v1/client-portal/document-submissions?client_id={tenant.id}&status=pending",
        headers=operator_headers,
    )
    reviewed = client.post(
        f"/api/v1/client-portal/document-submissions/{uploaded.json()['id']}/review",
        json={
            "client_id": str(tenant.id),
            "decision": "accepted",
            "note": "Documento legible y asociado a la factura correcta.",
        },
        headers=operator_headers,
    )

    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "accepted"
    db.refresh(item)
    assert item.status == "fulfilled"
    assert item.evidence["client_submission_id"] == uploaded.json()["id"]
    event_types = set(
        db.scalars(select(Event.event_type).where(Event.invoice_id == invoice.id))
    )
    assert "client_document.submitted" in event_types
    assert "client_document.reviewed" in event_types
    assert "payability.item_changed" in event_types


def test_rejection_requires_note_and_keeps_requirement_open(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="document-reject-client")
    _, admin = create_tenant_user(db, suffix="document-reject-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "DOC-REJECT-001")
    ensure_checklist(db, invoice)
    db.commit()
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.responsible_role == "client",
            PayabilityItem.required.is_(True),
        )
    )
    assert item is not None
    uploaded = client.post(
        "/api/v1/client-portal/documents",
        data={"invoice_id": str(invoice.id), "payability_item_id": str(item.id)},
        files={"document": ("guia.pdf", b"guia-sintetica", "application/pdf")},
        headers={"Authorization": f"Bearer {_token(client, client_user.email)}"},
    )
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    without_note = client.post(
        f"/api/v1/client-portal/document-submissions/{uploaded.json()['id']}/review",
        json={"client_id": str(tenant.id), "decision": "rejected"},
        headers=headers,
    )
    rejected = client.post(
        f"/api/v1/client-portal/document-submissions/{uploaded.json()['id']}/review",
        json={
            "client_id": str(tenant.id),
            "decision": "rejected",
            "note": "El archivo no permite leer el número de la guía.",
        },
        headers=headers,
    )

    assert without_note.status_code == 422
    assert rejected.status_code == 200
    db.refresh(item)
    assert item.status in {"pending", "requested"}
