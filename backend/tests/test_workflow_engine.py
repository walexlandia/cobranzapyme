from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType, InvoiceStatus, Role
from app.models import Contact, Contract, Event, Invoice, Payer, WorkflowControl, WorkflowJob, WorkflowState
from app.schemas import ContractRules
from app.services.workflow_engine import (
    determine_stage,
    next_allowed_at,
    process_due_jobs,
    run_scheduler_cycle,
)
from tests.conftest import create_invoice, create_tenant_user


def _rules() -> dict:
    return ContractRules(
        allowed_weekdays=[0, 1, 2, 3, 4],
        window_start="09:00",
        window_end="18:00",
        max_contacts_per_week=2,
        preventive_days_before_due=7,
        escalation_days_after_due=15,
    ).model_dump(mode="json")


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_stage_progression() -> None:
    class InvoiceStub:
        issued_on = date(2026, 10, 1)
        due_on = date(2026, 10, 31)
        status = InvoiceStatus.ISSUED

    invoice = InvoiceStub()
    rules = ContractRules(preventive_days_before_due=7, escalation_days_after_due=15)
    assert determine_stage(invoice, date(2026, 10, 1), rules) == "emission"
    assert determine_stage(invoice, date(2026, 10, 10), rules) == "documental"
    assert determine_stage(invoice, date(2026, 10, 25), rules) == "preventive"
    assert determine_stage(invoice, date(2026, 10, 31), rules) == "due"
    assert determine_stage(invoice, date(2026, 11, 5), rules) == "early_arrears"
    assert determine_stage(invoice, date(2026, 11, 20), rules) == "escalation"


def test_next_allowed_at_skips_weekend_and_respects_santiago_timezone() -> None:
    rules = ContractRules(window_start="09:00", window_end="18:00")
    saturday = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)
    scheduled = next_allowed_at(saturday, rules)
    assert scheduled.astimezone().tzinfo is not None
    assert scheduled.astimezone(ZoneInfo("America/Santiago")).isoformat().startswith(
        "2026-10-19T09:00:00"
    )


def test_scheduler_is_idempotent_and_records_contract_version(db: Session) -> None:
    tenant, admin = create_tenant_user(db, suffix="workflow", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "FLOW-001")
    contract = Contract(client_id=tenant.id, version=1, rules=_rules(), active=True)
    db.add(contract)
    db.commit()
    moment = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)

    first = run_scheduler_cycle(
        db, client_id=tenant.id, now=moment, mode="manual", actor_id=admin.id
    )
    second = run_scheduler_cycle(
        db, client_id=tenant.id, now=moment, mode="manual", actor_id=admin.id
    )

    assert first.jobs_created == 1
    assert second.jobs_created == 0
    assert second.jobs_skipped == 1
    assert db.scalar(
        select(func.count()).select_from(WorkflowJob).where(WorkflowJob.client_id == tenant.id)
    ) == 1
    state = db.scalar(select(WorkflowState).where(WorkflowState.invoice_id == invoice.id))
    assert state is not None
    assert state.contract_id == contract.id
    event = db.scalar(
        select(Event)
        .where(Event.invoice_id == invoice.id, Event.event_type == "workflow.job_scheduled")
        .order_by(Event.created_at.desc())
    )
    assert event is not None
    assert event.payload["contract_version"] == 1


def test_disputed_invoice_pauses_without_scheduling(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="paused")
    invoice = create_invoice(db, tenant, "FLOW-PAUSED")
    invoice.status = InvoiceStatus.DISPUTED
    db.add(Contract(client_id=tenant.id, version=1, rules=_rules(), active=True))
    db.commit()

    result = run_scheduler_cycle(
        db,
        client_id=tenant.id,
        now=datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc),
        mode="automatic",
    )

    assert result.jobs_created == 0
    state = db.scalar(select(WorkflowState).where(WorkflowState.invoice_id == invoice.id))
    assert state is not None
    assert state.status == "paused"
    assert state.pause_reason == "disputed"


def test_contract_endpoint_creates_incremental_versions(client: TestClient, db: Session) -> None:
    tenant, admin = create_tenant_user(db, suffix="contract-admin", role=Role.ADMIN)
    token = _token(client, admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"client_id": str(tenant.id), "rules": _rules(), "activate": True}

    first = client.post("/api/v1/contracts", json=payload, headers=headers)
    second = client.post("/api/v1/contracts", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    contracts = client.get(
        f"/api/v1/contracts?client_id={tenant.id}", headers=headers
    ).json()
    assert [item["version"] for item in contracts] == [2, 1]
    assert [item["active"] for item in contracts] == [True, False]


def test_scheduler_groups_invoices_by_payer_and_recipient(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="grouped")
    payer = Payer(rut="T-GROUP-1", legal_name="Pagador agrupado")
    db.add(payer)
    db.flush()
    recipient = Contact(
        client_id=tenant.id,
        payer_id=payer.id,
        name="Contacto CxP",
        role="accounts_payable",
        email="grouped@example.com",
    )
    db.add(recipient)
    for folio in ("GROUP-001", "GROUP-002"):
        db.add(
            Invoice(
                client_id=tenant.id,
                payer_id=payer.id,
                folio=folio,
                issued_on=date(2026, 9, 1),
                due_on=date(2026, 9, 30),
                total_amount=500000,
            )
        )
    db.add(Contract(client_id=tenant.id, version=1, rules=_rules(), active=True))
    db.commit()

    result = run_scheduler_cycle(
        db,
        client_id=tenant.id,
        now=datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc),
    )

    assert result.jobs_created == 1
    job = db.scalar(select(WorkflowJob).where(WorkflowJob.client_id == tenant.id))
    assert job is not None
    assert job.payer_id == payer.id
    assert job.recipient_contact_id == recipient.id
    assert len(job.payload["invoice_ids"]) == 2


def test_scheduled_resume_reactivates_invoice(db: Session) -> None:
    tenant, _ = create_tenant_user(db, suffix="resume")
    invoice = create_invoice(db, tenant, "RESUME-001")
    db.add(Contract(client_id=tenant.id, version=1, rules=_rules(), active=True))
    control = WorkflowControl(
        client_id=tenant.id,
        scope_type="invoice",
        scope_id=invoice.id,
        status="paused",
        reason="promise_of_payment",
        resume_at=datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc),
    )
    db.add(control)
    db.commit()

    result = run_scheduler_cycle(
        db,
        client_id=tenant.id,
        now=datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc),
    )

    db.refresh(control)
    assert control.status == "active"
    assert result.jobs_created == 1
    state = db.scalar(select(WorkflowState).where(WorkflowState.invoice_id == invoice.id))
    assert state is not None
    assert state.status == "active"


def test_operator_can_pause_and_resume_invoice(client: TestClient, db: Session) -> None:
    tenant, admin = create_tenant_user(db, suffix="control-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "CONTROL-001")
    token = _token(client, admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    base_payload = {
        "client_id": str(tenant.id),
        "scope_type": "invoice",
        "scope_id": str(invoice.id),
    }

    paused = client.post(
        "/api/v1/workflows/controls",
        json={**base_payload, "action": "pause", "reason": "operator_review"},
        headers=headers,
    )
    resumed = client.post(
        "/api/v1/workflows/controls",
        json={**base_payload, "action": "resume"},
        headers=headers,
    )

    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"


def test_invoice_event_timeline_is_chronological_and_tenant_scoped(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="timeline-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "TIMELINE-001")
    other_tenant, _ = create_tenant_user(db, suffix="timeline-other")
    other_invoice = create_invoice(db, other_tenant, "TIMELINE-OTHER")
    first_event = record_event(
        db,
        client_id=tenant.id,
        invoice_id=invoice.id,
        event_type="workflow.first",
        actor_type=ActorType.SYSTEM,
    )
    first_event.created_at = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)
    second_event = record_event(
        db,
        client_id=tenant.id,
        invoice_id=invoice.id,
        event_type="workflow.second",
        actor_type=ActorType.HUMAN,
        actor_id=admin.id,
    )
    second_event.created_at = datetime(2026, 10, 14, 10, 1, tzinfo=timezone.utc)
    db.commit()
    token = _token(client, admin.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        f"/api/v1/invoices/{invoice.id}/events?client_id={tenant.id}", headers=headers
    )
    denied = client.get(
        f"/api/v1/invoices/{other_invoice.id}/events?client_id={tenant.id}", headers=headers
    )

    assert response.status_code == 200
    assert [item["event_type"] for item in response.json()] == [
        "workflow.first",
        "workflow.second",
    ]
    assert denied.status_code == 404


def test_simulation_uses_controlled_date_without_writing(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="simulation-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "SIM-001")
    db.add(Contract(client_id=tenant.id, version=1, rules=_rules(), active=True))
    db.commit()
    counts_before = {
        "states": db.scalar(select(func.count()).select_from(WorkflowState)),
        "jobs": db.scalar(select(func.count()).select_from(WorkflowJob)),
        "events": db.scalar(select(func.count()).select_from(Event)),
    }
    token = _token(client, admin.email)

    response = client.post(
        "/api/v1/workflows/simulate",
        json={
            "client_id": str(tenant.id),
            "invoice_id": str(invoice.id),
            "simulation_date": "2026-02-09",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    decision = response.json()[0]
    assert decision["stage"] == "due"
    assert decision["action_type"] == "payment_due"
    assert {window["stage"] for window in decision["stage_windows"]} == {
        "emission",
        "documental",
        "preventive",
        "due",
        "early_arrears",
        "escalation",
    }
    assert counts_before == {
        "states": db.scalar(select(func.count()).select_from(WorkflowState)),
        "jobs": db.scalar(select(func.count()).select_from(WorkflowJob)),
        "events": db.scalar(select(func.count()).select_from(Event)),
    }


def test_payer_control_pauses_every_invoice_in_group(client: TestClient, db: Session) -> None:
    tenant, admin = create_tenant_user(db, suffix="payer-control", role=Role.ADMIN)
    payer = Payer(rut="P-CONTROL-01", legal_name="Pagador controlado")
    db.add(payer)
    db.flush()
    invoices = []
    for folio in ("PAYER-001", "PAYER-002"):
        invoice = Invoice(
            client_id=tenant.id,
            payer_id=payer.id,
            folio=folio,
            issued_on=date(2026, 9, 1),
            due_on=date(2026, 9, 30),
            total_amount=500000,
        )
        db.add(invoice)
        invoices.append(invoice)
    db.add(Contract(client_id=tenant.id, version=1, rules=_rules(), active=True))
    db.commit()
    token = _token(client, admin.email)
    response = client.post(
        "/api/v1/workflows/controls",
        json={
            "client_id": str(tenant.id),
            "scope_type": "payer",
            "scope_id": str(payer.id),
            "action": "pause",
            "reason": "payer_request",
            "resume_at": "2026-10-20T12:00:00Z",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    result = run_scheduler_cycle(
        db,
        client_id=tenant.id,
        now=datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc),
    )

    assert result.jobs_created == 0
    states = list(
        db.scalars(
            select(WorkflowState)
            .where(WorkflowState.invoice_id.in_([invoice.id for invoice in invoices]))
            .order_by(WorkflowState.invoice_id)
        )
    )
    assert len(states) == 2
    assert all(state.status == "paused" for state in states)
    assert all(state.pause_reason == "manual:payer_request" for state in states)


def test_events_reconstruct_complete_workflow_decision(client: TestClient, db: Session) -> None:
    tenant, admin = create_tenant_user(db, suffix="decision-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "DECISION-001")
    db.add(Contract(client_id=tenant.id, version=3, rules=_rules(), active=True))
    db.commit()
    moment = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)

    scheduled = run_scheduler_cycle(
        db, client_id=tenant.id, now=moment, mode="manual", actor_id=admin.id
    )
    processed = process_due_jobs(db, now=moment)
    token = _token(client, admin.email)
    response = client.get(
        f"/api/v1/invoices/{invoice.id}/events?client_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert scheduled.jobs_created == 1
    assert processed == 1
    assert response.status_code == 200
    events = response.json()
    assert [event["event_type"] for event in events] == [
        "workflow.state_changed",
        "workflow.job_scheduled",
        "workflow.action_ready",
        "communication.blocked",
    ]
    assert events[0]["payload"]["contract_version"] == 3
    assert events[1]["payload"]["stage"] == "escalation"
    assert events[2]["payload"]["action_type"] == "escalate_case"
    assert events[2]["payload"]["contract_version"] == 3
    assert events[3]["payload"]["external_delivery"] is False
    assert events[3]["payload"]["safety_flags"] == [
        "missing_contact",
        "missing_sender_email",
        "missing_destination",
    ]
