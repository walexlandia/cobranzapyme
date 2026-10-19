import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import Event, ExceptionCase, PilotLogEntry
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_operator_records_resolves_and_filters_pilot_log(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="pilot-log", role=Role.ADMIN)
    _, client_user = create_tenant_user(db, suffix="pilot-log-client")
    invoice = create_invoice(db, tenant, "PILOT-LOG-001")
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    payload = {
        "client_id": str(tenant.id),
        "related_invoice_id": str(invoice.id),
        "entry_type": "incident",
        "severity": "warning",
        "title": "Mensaje detenido por revisión",
        "detail": "Incidencia sintética sin entrega externa.",
        "occurred_on": "2026-10-19",
        "human_minutes": "12.5",
    }

    created = client.post("/api/v1/pilot/log", json=payload, headers=admin_headers)

    assert created.status_code == 201
    assert created.json()["status"] == "open"
    assert created.json()["human_minutes"] == "12.50"
    entry_id = created.json()["id"]
    assert client.post("/api/v1/pilot/log", json=payload, headers=client_headers).status_code == 403
    open_entries = client.get(
        f"/api/v1/pilot/log?client_id={tenant.id}&status=open",
        headers=admin_headers,
    )
    assert open_entries.status_code == 200
    assert [entry["id"] for entry in open_entries.json()] == [entry_id]
    resolved = client.post(
        f"/api/v1/pilot/log/{entry_id}/resolve",
        json={
            "client_id": str(tenant.id),
            "resolution_note": "Se verificó que no hubo mensaje duplicado.",
        },
        headers=admin_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None
    assert client.post(
        f"/api/v1/pilot/log/{entry_id}/resolve",
        json={"client_id": str(tenant.id), "resolution_note": "Repetido"},
        headers=admin_headers,
    ).status_code == 409
    db_entry = db.get(PilotLogEntry, uuid.UUID(entry_id))
    assert db_entry is not None and db_entry.status == "resolved"
    events = list(
        db.scalars(
            select(Event).where(
                Event.client_id == tenant.id,
                Event.event_type.in_(["pilot.log_recorded", "pilot.log_resolved"]),
            )
        )
    )
    assert {event.event_type for event in events} == {
        "pilot.log_recorded",
        "pilot.log_resolved",
    }
    metrics = client.get(
        f"/api/v1/metrics/pilot?client_id={tenant.id}"
        "&date_from=2026-10-01&date_to=2026-10-31",
        headers=admin_headers,
    )
    assert metrics.status_code == 200
    assert metrics.json()["operations"]["logged_human_minutes"] == "12.50"
    assert metrics.json()["operations"]["human_minutes"] == "12.50"
    walkthrough = client.get(
        f"/api/v1/pilot/demo-walkthrough?client_id={tenant.id}&operation_date=2026-10-19",
        headers=admin_headers,
    )
    assert walkthrough.status_code == 200
    assert walkthrough.json()["operation_date"] == "2026-10-19"
    assert walkthrough.json()["total_steps"] == 6
    assert {step["target_view"] for step in walkthrough.json()["steps"]} == {
        "contract",
        "payability",
        "communications",
        "exceptions",
        "payments",
        "metrics",
    }


def test_client_responds_once_to_own_escalated_exception(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="client-escalation")
    _, other_user = create_tenant_user(db, suffix="client-escalation-other")
    invoice = create_invoice(db, tenant, "CLIENT-ESC-001")
    escalated_at = datetime(2026, 10, 19, 14, tzinfo=timezone.utc)
    case = ExceptionCase(
        client_id=tenant.id,
        invoice_id=invoice.id,
        kind="document_request",
        status="open",
        priority=100,
        detail={
            "client_escalation": {
                "note": "Confirmar si la orden de compra es correcta.",
                "created_at": escalated_at.isoformat(),
                "external_delivery": False,
            }
        },
        human_minutes=Decimal("0"),
        resolution={},
    )
    db.add(case)
    db.commit()
    own_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    other_headers = {"Authorization": f"Bearer {_token(client, other_user.email)}"}

    listed = client.get("/api/v1/client-portal/escalated-exceptions", headers=own_headers)

    assert listed.status_code == 200
    assert listed.json()[0]["invoice_folio"] == "CLIENT-ESC-001"
    assert client.get(
        "/api/v1/client-portal/escalated-exceptions", headers=other_headers
    ).json() == []
    response = client.post(
        f"/api/v1/client-portal/escalated-exceptions/{case.id}/response",
        json={
            "response_type": "information_provided",
            "message": "La OC correcta es OC-2026-1842.",
        },
        headers=own_headers,
    )
    assert response.status_code == 200
    assert response.json()["response"]["response_type"] == "information_provided"
    repeated = client.post(
        f"/api/v1/client-portal/escalated-exceptions/{case.id}/response",
        json={"response_type": "approved", "message": "Confirmado."},
        headers=own_headers,
    )
    assert repeated.status_code == 409
    assert client.post(
        f"/api/v1/client-portal/escalated-exceptions/{case.id}/response",
        json={"response_type": "approved", "message": "Intento ajeno."},
        headers=other_headers,
    ).status_code == 404
    assert db.scalar(
        select(Event).where(
            Event.client_id == tenant.id,
            Event.event_type == "exception.client_responded",
        )
    ) is not None
