from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import InvoiceStatus, Role
from app.models import (
    ClientPayerRelation,
    Contact,
    Contract,
    DelayCause,
    Event,
    Invoice,
    PayabilityItem,
    Payer,
    PayerProfile,
    WorkflowJob,
)
from app.schemas import ContractRules, PayerRequirements
from app.services.payability import checklist_status, ensure_checklist, get_or_create_profile
from app.services.workflow_engine import run_scheduler_cycle
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_checklist_is_generated_from_global_payer_profile(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="payability-checklist")
    invoice = create_invoice(db, tenant, "PAY-001")
    profile = get_or_create_profile(db, invoice.payer_id)
    profile.operational_requirements = PayerRequirements(
        requires_purchase_order=True,
        requires_hes=True,
        requires_supplier_portal=True,
    ).model_dump(mode="json")
    db.flush()

    items = ensure_checklist(db, invoice)
    db.commit()

    item_types = {item.item_type for item in items if item.required}
    assert item_types == {
        "sii_acceptance",
        "purchase_order",
        "hes_conformity",
        "supplier_portal",
    }
    assert db.scalar(
        select(Event).where(
            Event.invoice_id == invoice.id,
            Event.event_type == "payability.item_created",
        )
    ) is not None


def test_profile_response_never_exposes_private_tenant_data(
    client: TestClient, db: Session
) -> None:
    tenant_a, user_a = create_tenant_user(db, suffix="profile-a")
    tenant_b, _ = create_tenant_user(db, suffix="profile-b")
    payer = Payer(rut="PROFILE-SHARED", legal_name="Pagador compartido")
    db.add(payer)
    db.flush()
    for tenant, folio in ((tenant_a, "A-001"), (tenant_b, "B-001")):
        db.add(
            Invoice(
                client_id=tenant.id,
                payer_id=payer.id,
                folio=folio,
                issued_on=date(2026, 10, 1),
                due_on=date(2026, 10, 31),
                total_amount=100000,
            )
        )
    db.add(
        ClientPayerRelation(
            client_id=tenant_b.id,
            payer_id=payer.id,
            private_notes="Dato secreto de la otra pyme",
        )
    )
    get_or_create_profile(db, payer.id)
    db.commit()
    token = _token(client, user_a.email)

    response = client.get(
        f"/api/v1/payers/{payer.id}/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    serialized = response.text
    assert "Dato secreto" not in serialized
    assert str(tenant_b.id) not in serialized
    assert "operational_requirements" in response.json()


def test_client_cannot_read_an_unassociated_payer_profile(
    client: TestClient, db: Session
) -> None:
    tenant_a, user_a = create_tenant_user(db, suffix="profile-scope-a")
    tenant_b, _ = create_tenant_user(db, suffix="profile-scope-b")
    foreign_invoice = create_invoice(db, tenant_b, "FOREIGN-001")
    token = _token(client, user_a.email)

    response = client.get(
        f"/api/v1/payers/{foreign_invoice.payer_id}/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_profile_update_versions_rules_and_propagates_checklist(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="profile-version", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "PROFILE-001")
    token = _token(client, admin.email)
    payload = {
        "operational_requirements": {
            "requires_purchase_order": True,
            "requires_hes": True,
            "requires_delivery_note": False,
            "requires_supplier_portal": True,
            "other_requirements": [],
            "risk_days_before_due": 10,
        },
        "supplier_portal_url": "https://portal.example.test",
        "corporate_channels": {"email": "cxp@example.test"},
        "payment_cycle": "Viernes",
    }

    first = client.put(
        f"/api/v1/payers/{invoice.payer_id}/profile",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    second = client.put(
        f"/api/v1/payers/{invoice.payer_id}/profile",
        json={**payload, "payment_cycle": "Días 10 y 25"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    required = set(
        db.scalars(
            select(PayabilityItem.item_type).where(
                PayabilityItem.invoice_id == invoice.id,
                PayabilityItem.required.is_(True),
            )
        )
    )
    assert {"sii_acceptance", "purchase_order", "hes_conformity", "supplier_portal"} <= required


def test_sii_import_marks_claimed_invoice_and_audits_change(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="sii-import", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "SII-001")
    ensure_checklist(db, invoice)
    db.commit()
    token = _token(client, admin.email)
    content = (
        "Tipo documento;Folio;Estado SII;Fecha consulta;Plazo reclamo;Detalle\n"
        "factura;SII-001;Reclamada;2026-10-14;2026-10-15;OC inválida\n"
    )

    response = client.post(
        "/api/v1/imports/sii-status",
        data={"client_id": str(tenant.id), "commit": "true"},
        files={"file": ("estado-sii.csv", content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["imported_count"] == 1
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.CLAIMED
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.item_type == "sii_acceptance",
        )
    )
    assert item is not None
    assert item.status == "blocked"
    assert item.evidence["sii_status"] == "claimed"


def test_portal_evidence_and_delay_cause_are_audited(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="portal-delay", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "PORTAL-001")
    profile = get_or_create_profile(db, invoice.payer_id)
    profile.operational_requirements = PayerRequirements(
        requires_supplier_portal=True
    ).model_dump(mode="json")
    ensure_checklist(db, invoice)
    db.commit()
    token = _token(client, admin.email)
    headers = {"Authorization": f"Bearer {token}"}

    portal = client.post(
        f"/api/v1/payability/invoices/{invoice.id}/portal?client_id={tenant.id}",
        json={
            "entry_number": "ING-9981",
            "uploaded_at": datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc).isoformat(),
            "evidence_reference": "custodia/portal-001.png",
        },
        headers=headers,
    )
    cause = client.put(
        f"/api/v1/payability/invoices/{invoice.id}/delay-cause?client_id={tenant.id}",
        json={"category": "supplier_portal", "detail": "Carga tardía"},
        headers=headers,
    )

    assert portal.status_code == 200
    assert portal.json()["status"] == "fulfilled"
    assert cause.status_code == 200
    assert db.scalar(select(DelayCause).where(DelayCause.invoice_id == invoice.id)) is not None
    event_types = set(
        db.scalars(select(Event.event_type).where(Event.invoice_id == invoice.id))
    )
    assert {"payability.portal_registered", "delay_cause.changed"} <= event_types


def test_risk_status_changes_as_due_date_approaches(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="risk-status")
    invoice = create_invoice(db, tenant, "RISK-001")
    invoice.issued_on = date(2026, 10, 1)
    invoice.due_on = date(2026, 10, 31)
    profile = get_or_create_profile(db, invoice.payer_id)
    requirements = PayerRequirements(risk_days_before_due=7)
    profile.operational_requirements = requirements.model_dump(mode="json")
    items = ensure_checklist(db, invoice)

    early = checklist_status(invoice, items, requirements=requirements, today=date(2026, 10, 10))
    late = checklist_status(invoice, items, requirements=requirements, today=date(2026, 10, 26))

    assert early[0] == "incomplete"
    assert late[0] == "at_risk"


def test_pending_sii_after_claim_deadline_is_at_risk(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="sii-deadline")
    invoice = create_invoice(db, tenant, "SII-RISK-001")
    requirements = PayerRequirements(risk_days_before_due=7)
    items = ensure_checklist(db, invoice)
    sii_item = next(item for item in items if item.item_type == "sii_acceptance")
    sii_item.evidence = {
        "sii_status": "pending",
        "claim_deadline": "2026-01-20",
    }

    result = checklist_status(
        invoice,
        items,
        requirements=requirements,
        today=date(2026, 1, 25),
    )

    assert result[0] == "at_risk"


def test_preventive_confirmation_records_approval_and_schedule(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="preventive", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "PREVENTIVE-001")
    ensure_checklist(db, invoice)
    db.commit()
    token = _token(client, admin.email)

    response = client.post(
        f"/api/v1/payability/invoices/{invoice.id}/preventive-confirmation?client_id={tenant.id}",
        json={
            "approval_status": "approved",
            "approved_at": "2026-01-25T13:00:00Z",
            "scheduled_payment_date": "2026-02-05",
            "reference": "Confirmación CxP 1842",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = {item["item_type"]: item for item in response.json()["items"]}
    assert items["payment_approval"]["status"] == "fulfilled"
    assert items["payment_scheduled"]["status"] == "fulfilled"
    assert (
        items["payment_scheduled"]["evidence"]["scheduled_payment_date"]
        == "2026-02-05"
    )
    events = list(
        db.scalars(
            select(Event).where(
                Event.invoice_id == invoice.id,
                Event.event_type == "payability.preventive_confirmation_changed",
            )
        )
    )
    assert len(events) == 2


def test_workflow_requests_missing_requirement_from_correct_recipient(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="payability-routing")
    invoice = create_invoice(db, tenant, "ROUTE-001")
    profile = get_or_create_profile(db, invoice.payer_id)
    profile.operational_requirements = PayerRequirements(
        requires_purchase_order=False,
        requires_hes=True,
    ).model_dump(mode="json")
    requester = Contact(
        client_id=tenant.id,
        payer_id=invoice.payer_id,
        name="Solicitante",
        role="requester",
        email="requester@example.test",
    )
    db.add(requester)
    items = ensure_checklist(db, invoice)
    for item in items:
        if item.item_type == "sii_acceptance":
            item.status = "fulfilled"
            item.evidence = {"sii_status": "accepted"}
    db.add(
        Contract(
            client_id=tenant.id,
            version=1,
            rules=ContractRules().model_dump(mode="json"),
            active=True,
        )
    )
    db.commit()

    result = run_scheduler_cycle(
        db,
        client_id=tenant.id,
        now=datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc),
    )

    assert result.jobs_created == 1
    job = db.scalar(select(WorkflowJob).where(WorkflowJob.invoice_id == invoice.id))
    assert job is not None
    assert job.action_type == "request_missing_requirement"
    assert job.recipient_contact_id == requester.id
    assert "HES o conformidad del servicio" in job.payload["missing_items"][str(invoice.id)]
