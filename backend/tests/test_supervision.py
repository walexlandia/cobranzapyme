from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import (
    Contact,
    Contract,
    Event,
    PayabilityItem,
    PayerProfile,
    PayerProfileRevision,
    WorkflowState,
)
from app.schemas import ContractRules
from app.services.payability import ensure_checklist
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_review_updates_evaluation_checklist_stage_and_precision_gate(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="supervision", role=Role.ADMIN)
    tenant.sender_name = "Equipo Cobranza Pyme"
    tenant.sender_email = "cobranza@pyme-supervision.example.test"
    invoice = create_invoice(db, tenant, "SUP-001")
    contact = Contact(
        client_id=tenant.id,
        payer_id=invoice.payer_id,
        name="Persona Evaluación",
        role="accounts_payable",
        email="persona.evaluacion@example.test",
        phone="+56961112222",
    )
    contract = Contract(
        client_id=tenant.id,
        version=1,
        rules=ContractRules().model_dump(mode="json"),
        active=True,
    )
    db.add_all([contact, contract])
    db.flush()
    state = WorkflowState(
        client_id=tenant.id,
        invoice_id=invoice.id,
        contract_id=contract.id,
        stage="preventive",
        status="active",
    )
    db.add(state)
    ensure_checklist(db, invoice)
    db.commit()
    payment_item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.item_type == "payment_scheduled",
        )
    )
    assert payment_item is not None
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "supervision-demo-001",
            "sender": contact.email,
            "body": "La factura SUP-001 quedó con pago programado para el 24/10/2026 por $1.250.000.",
            "invoice_folios": [invoice.folio],
        },
        headers=headers,
    )
    assert inbound.status_code == 200
    case = client.get(
        f"/api/v1/exceptions?client_id={tenant.id}&status=open", headers=headers
    ).json()[0]
    suggestion = client.get(
        f"/api/v1/communications/exception-responses/{case['id']}/suggestion?client_id={tenant.id}",
        headers=headers,
    )
    assert suggestion.status_code == 200
    assert suggestion.json()["external_delivery"] is False
    draft = client.post(
        f"/api/v1/communications/exception-responses/{case['id']}/draft",
        json={
            "client_id": str(tenant.id),
            "channel": suggestion.json()["channel"],
            "subject": suggestion.json()["subject"],
            "body": suggestion.json()["body"],
        },
        headers=headers,
    )
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    assert draft.json()["mode"] == "manual"
    assert draft.json()["provider_payload"]["external_delivery"] is False
    assert draft.json()["provider_payload"]["requires_human_review"] is True
    assert draft.json()["sent_at"] is None
    repeated_draft = client.post(
        f"/api/v1/communications/exception-responses/{case['id']}/draft",
        json={
            "client_id": str(tenant.id),
            "channel": suggestion.json()["channel"],
            "subject": suggestion.json()["subject"],
            "body": suggestion.json()["body"],
        },
        headers=headers,
    )
    assert repeated_draft.status_code == 200
    assert repeated_draft.json()["id"] == draft.json()["id"]
    reviewed = client.post(
        f"/api/v1/exceptions/{case['id']}/review",
        json={
            "client_id": str(tenant.id),
            "category": "payment_scheduled",
            "extracted_data": case["classification"]["extracted_data"],
            "human_minutes": "3.25",
            "note": "Confirmado con la respuesta recibida.",
            "checklist_updates": [
                {
                    "item_id": str(payment_item.id),
                    "status": "fulfilled",
                    "evidence": {"payment_date": "2026-10-24", "source": "human_review"},
                }
            ],
            "workflow_stage": "due",
        },
        headers=headers,
    )
    assert reviewed.status_code == 200
    db.refresh(payment_item)
    db.refresh(state)
    assert payment_item.status == "fulfilled"
    assert state.stage == "due"
    evaluation_sets = client.get(
        f"/api/v1/evaluation/sets?client_id={tenant.id}", headers=headers
    ).json()
    assert len(evaluation_sets) == 1
    assert evaluation_sets[0]["sample_count"] == 1
    redacted = evaluation_sets[0]["examples"][0]["redacted_text"]
    assert contact.email not in redacted
    assert invoice.folio not in redacted
    assert "1.250.000" not in redacted
    policies = client.get(
        f"/api/v1/classification-policies?client_id={tenant.id}", headers=headers
    ).json()
    policy = next(item for item in policies if item["category"] == "payment_scheduled")
    assert Decimal(policy["current_precision"]) == Decimal("1.0000")
    assert policy["sample_count"] == 1
    assert policy["eligible_for_automation"] is False
    automatic = client.post(
        f"/api/v1/classification-policies/{policy['id']}",
        json={"client_id": str(tenant.id), "mode": "automatic"},
        headers=headers,
    )
    assert automatic.status_code == 409
    report = client.get(
        f"/api/v1/evaluation/report?client_id={tenant.id}", headers=headers
    )
    assert report.status_code == 200
    assert report.json()["total_examples"] == 1
    assert report.json()["reviewed_cases"] == 1
    assert report.json()["total_human_minutes"] == "3.25"
    exported = client.get(
        f"/api/v1/evaluation/report.csv?client_id={tenant.id}", headers=headers
    )
    assert exported.status_code == 200
    assert "payment_scheduled" in exported.text
    frozen = client.post(
        f"/api/v1/evaluation/sets/{evaluation_sets[0]['id']}/freeze?client_id={tenant.id}",
        headers=headers,
    )
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"


def test_local_escalation_and_profile_proposal_require_human_approval(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="proposal", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "SUP-002")
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    inbound = client.post(
        "/api/v1/communications/inbound/simulate",
        json={
            "client_id": str(tenant.id),
            "channel": "email",
            "provider_id": "supervision-demo-002",
            "sender": "desconocido@example.test",
            "body": "El proveedor no está registrado; el ciclo de pago es cada viernes.",
            "invoice_folios": [invoice.folio],
        },
        headers=headers,
    )
    assert inbound.status_code == 200
    case = client.get(
        f"/api/v1/exceptions?client_id={tenant.id}&status=open", headers=headers
    ).json()[0]
    escalated = client.post(
        f"/api/v1/exceptions/{case['id']}/escalate",
        json={
            "client_id": str(tenant.id),
            "note": "Confirmar con la pyme el ciclo informado antes de actualizar la ficha.",
        },
        headers=headers,
    )
    assert escalated.status_code == 200
    assert escalated.json()["priority"] == 100
    assert escalated.json()["detail"]["client_escalation"]["external_delivery"] is False
    invalid_proposal = client.post(
        "/api/v1/payer-profile-proposals",
        json={
            "client_id": str(tenant.id),
            "exception_id": case["id"],
            "proposed_changes": {"campo_inventado": "no permitido"},
            "rationale": "Debe ser rechazada antes de tocar la ficha global.",
        },
        headers=headers,
    )
    assert invalid_proposal.status_code == 422
    proposal = client.post(
        "/api/v1/payer-profile-proposals",
        json={
            "client_id": str(tenant.id),
            "exception_id": case["id"],
            "proposed_changes": {"payment_cycle": "Todos los viernes"},
            "rationale": "Dato informado en la respuesta del pagador.",
        },
        headers=headers,
    )
    assert proposal.status_code == 200
    profile_before = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == invoice.payer_id))
    assert profile_before is None or profile_before.payment_cycle != "Todos los viernes"
    decided = client.post(
        f"/api/v1/payer-profile-proposals/{proposal.json()['id']}/decision",
        json={
            "client_id": str(tenant.id),
            "decision": "approved",
            "note": "Aprobado por operador.",
        },
        headers=headers,
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    profile = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == invoice.payer_id))
    assert profile is not None
    assert profile.payment_cycle == "Todos los viernes"
    assert db.scalar(
        select(PayerProfileRevision).where(PayerProfileRevision.payer_profile_id == profile.id)
    ) is not None
    assert db.scalar(
        select(Event).where(
            Event.invoice_id == invoice.id,
            Event.event_type == "exception.escalated_to_client",
        )
    ) is not None
