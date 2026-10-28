#!/usr/bin/env python3

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import Event, GuidedWorkSession, Message, Payment, PilotLogEntry
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _headers(client: TestClient, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(client, email)}"}


def _guide(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get(
        "/api/v1/optimizations/weekly-portfolio-review/guide",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_guided_review_is_human_supervised_idempotent_and_auditable(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="pm2-guide", role=Role.ADMIN)
    _, client_user = create_tenant_user(db, suffix="pm2-guide-client")
    invoice = create_invoice(db, tenant, "PM2-GUIDE-001")
    other_invoice = create_invoice(db, tenant, "PM2-GUIDE-002")
    admin_headers = _headers(client, admin.email)
    client_headers = _headers(client, client_user.email)

    assert client.get(
        "/api/v1/optimizations/weekly-portfolio-review/guide",
        headers=client_headers,
    ).status_code == 403
    guide = _guide(client, admin_headers)
    assert guide["baseline_minutes_per_case"] == "18.00"
    assert guide["target_minutes_per_case"] == "14.40"
    assert len(guide["steps"]) == 5
    assert all("No " in constraint for constraint in guide["safety_constraints"][:3])

    start_payload = {
        "client_id": str(tenant.id),
        "invoice_id": str(invoice.id),
        "idempotency_key": "revision-semanal-2026-44",
    }
    started = client.post(
        "/api/v1/optimizations/weekly-portfolio-review/sessions",
        json=start_payload,
        headers=admin_headers,
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    assert started.json()["status"] == "open"
    replay = client.post(
        "/api/v1/optimizations/weekly-portfolio-review/sessions",
        json=start_payload,
        headers=admin_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == session_id
    conflicting_replay = client.post(
        "/api/v1/optimizations/weekly-portfolio-review/sessions",
        json={**start_payload, "invoice_id": str(other_invoice.id)},
        headers=admin_headers,
    )
    assert conflicting_replay.status_code == 409

    step_keys = [step["key"] for step in guide["steps"]]
    incomplete = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/complete",
        json={
            "completed_step_keys": step_keys[:-1],
            "human_minutes": "12",
            "outcome": "prepare_follow_up",
            "outcome_note": "Preparar borrador para revisión humana.",
        },
        headers=admin_headers,
    )
    assert incomplete.status_code == 422
    completion_payload = {
        "completed_step_keys": step_keys,
        "human_minutes": "12",
        "outcome": "prepare_follow_up",
        "outcome_note": "Preparar borrador para revisión humana.",
    }
    completed = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/complete",
        json=completion_payload,
        headers=admin_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["human_minutes"] == "12.00"
    assert completed.json()["pilot_log_entry_id"] is not None
    completion_replay = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/complete",
        json=completion_payload,
        headers=admin_headers,
    )
    assert completion_replay.status_code == 200
    changed_replay = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/complete",
        json={**completion_payload, "human_minutes": "11"},
        headers=admin_headers,
    )
    assert changed_replay.status_code == 409
    assert client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/cancel",
        json={"reason": "No corresponde cancelar una sesión completada."},
        headers=admin_headers,
    ).status_code == 409

    assert db.scalar(select(func.count(PilotLogEntry.id))) == 1
    assert db.scalar(select(func.count(GuidedWorkSession.id))) == 1
    assert db.scalar(select(func.count(Message.id))) == 0
    assert db.scalar(select(func.count(Payment.id))) == 0
    events = list(
        db.scalars(
            select(Event).where(
                Event.event_type.in_(
                    [
                        "optimization.guided_work_started",
                        "optimization.guided_work_completed",
                    ]
                )
            )
        )
    )
    assert [event.event_type for event in events] == [
        "optimization.guided_work_started",
        "optimization.guided_work_completed",
    ]
    assert events[-1].payload["external_action_executed"] is False


def test_open_guided_review_can_be_cancelled_without_manual_work(
    client: TestClient, db: Session
) -> None:
    tenant, operator = create_tenant_user(db, suffix="pm2-cancel", role=Role.OPERATOR)
    headers = _headers(client, operator.email)
    started = client.post(
        "/api/v1/optimizations/weekly-portfolio-review/sessions",
        json={
            "client_id": str(tenant.id),
            "idempotency_key": "cancelable-weekly-review",
        },
        headers=headers,
    )
    session_id = started.json()["id"]
    cancelled = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/cancel",
        json={"reason": "La revisión se abrió para la pyme equivocada."},
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    replay = client.post(
        f"/api/v1/optimizations/weekly-portfolio-review/sessions/{session_id}/cancel",
        json={"reason": "La revisión se abrió para la pyme equivocada."},
        headers=headers,
    )
    assert replay.status_code == 200
    assert db.scalar(select(func.count(PilotLogEntry.id))) == 0


def test_pm_g2_synthetic_benchmark_reduces_time_without_duplicates(
    client: TestClient, db: Session
) -> None:
    tenants = []
    admin = None
    for index in range(3):
        tenant, user = create_tenant_user(
            db,
            suffix=f"pm2-benchmark-{index}",
            role=Role.ADMIN if index == 0 else Role.CLIENT,
        )
        tenants.append(tenant)
        admin = user if index == 0 else admin
    assert admin is not None
    headers = _headers(client, admin.email)
    guide = _guide(client, headers)
    step_keys = [step["key"] for step in guide["steps"]]
    for index, (tenant, minutes) in enumerate(
        zip(tenants, [Decimal(12), Decimal(13), Decimal(11)], strict=True)
    ):
        started = client.post(
            "/api/v1/optimizations/weekly-portfolio-review/sessions",
            json={
                "client_id": str(tenant.id),
                "idempotency_key": f"benchmark-week-{index}",
            },
            headers=headers,
        )
        assert started.status_code == 201
        completed = client.post(
            "/api/v1/optimizations/weekly-portfolio-review/sessions/"
            f"{started.json()['id']}/complete",
            json={
                "completed_step_keys": step_keys,
                "human_minutes": str(minutes),
                "outcome": "no_action",
                "outcome_note": "Revisión sintética completada sin acción externa.",
            },
            headers=headers,
        )
        assert completed.status_code == 200

    benchmark = client.get(
        "/api/v1/optimizations/weekly-portfolio-review/benchmark",
        headers=headers,
    )
    assert benchmark.status_code == 200
    payload = benchmark.json()
    assert payload["sample"]["completed_cases"] == 3
    assert payload["before"]["total_human_minutes"] == "54.00"
    assert payload["after"]["total_human_minutes"] == "36.00"
    assert payload["after"]["average_minutes_per_case"] == "12.00"
    assert payload["reduction_percent"] == "33.33"
    assert payload["safety"] == {
        "idempotency_duplicates": 0,
        "reopenings": 0,
        "traceability_complete": True,
        "external_actions_executed": 0,
    }
    assert payload["pm_g2"]["status"] == "passed_synthetic"
    assert payload["pm_g2"]["local_phase_complete"] is True
    assert payload["pm_g2"]["pm3_authorized"] is False
