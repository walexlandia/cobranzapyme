from datetime import date
from io import BytesIO
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.document_crypto import decrypt_document_content
from app.domain import Role
from app.models import (
    Contact,
    Contract,
    Document,
    MessageTemplate,
    PilotAuthorizationEvent,
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


def test_pilot_authorization_evidence_readiness_and_revocation(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="pilot-ready", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "PILOT-001")
    contract = Contract(
        client_id=tenant.id,
        version=1,
        active=True,
        rules=ContractRules(channels=["email"]).model_dump(mode="json"),
    )
    contact = Contact(
        client_id=tenant.id,
        payer_id=invoice.payer_id,
        name="Contacto autorizado",
        role="accounts_payable",
        email="autorizado@example.test",
    )
    template = MessageTemplate(
        client_id=tenant.id,
        template_key="payment_due",
        version=1,
        channel="email",
        stage="due",
        recipient_role="accounts_payable",
        tone="cordial",
        subject_template="Factura {{ invoice.folio }}",
        body_template="Mensaje aprobado para {{ payer.legal_name }}.",
        approved=True,
        active=True,
    )
    db.add_all([contract, contact, template])
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    evidence = b"mandato piloto ficticio firmado"
    approved = client.post(
        "/api/v1/pilot/authorizations",
        data={
            "client_id": str(tenant.id),
            "contract_id": str(contract.id),
            "channels_json": '["email"]',
            "authorized_contact_name": "Representante Demo",
            "authorized_contact_email": "representante@example.test",
            "valid_from": date.today().isoformat(),
            "note": "Autorización ficticia para prueba local.",
        },
        files={"evidence": ("mandato.txt", BytesIO(evidence), "text/plain")},
        headers=headers,
    )
    assert approved.status_code == 201
    authorization_id = uuid.UUID(approved.json()["id"])
    authorization = db.get(PilotAuthorizationEvent, authorization_id)
    assert authorization is not None and authorization.action == "approved"
    document = db.get(Document, authorization.evidence_document_id)
    assert document is not None
    assert document.content != evidence
    assert decrypt_document_content(document) == evidence
    readiness = client.get(
        f"/api/v1/pilot/readiness?client_id={tenant.id}", headers=headers
    )
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True
    revoked = client.post(
        f"/api/v1/pilot/authorizations/{authorization_id}/revoke",
        json={"client_id": str(tenant.id), "note": "Fin de la prueba controlada."},
        headers=headers,
    )
    assert revoked.status_code == 201
    assert revoked.json()["action"] == "revoked"
    readiness_after = client.get(
        f"/api/v1/pilot/readiness?client_id={tenant.id}", headers=headers
    )
    assert readiness_after.status_code == 200
    assert readiness_after.json()["ready"] is False
    assert readiness_after.json()["checks"]["authorized_channels"] is False
    history = list(
        db.scalars(
            select(PilotAuthorizationEvent)
            .where(PilotAuthorizationEvent.client_id == tenant.id)
            .order_by(PilotAuthorizationEvent.created_at)
        )
    )
    assert [event.action for event in history] == ["approved", "revoked"]
