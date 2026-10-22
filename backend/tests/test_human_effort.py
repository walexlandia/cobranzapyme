from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import (
    BankTransaction,
    ExceptionCase,
    PilotLogEntry,
    ReconciliationProposal,
)
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_pm1_diagnostic_ranks_cost_without_inventing_reconciliation_minutes(
    client: TestClient, db: Session
) -> None:
    tenant, client_user = create_tenant_user(db, suffix="pm1-client")
    _, admin = create_tenant_user(db, suffix="pm1-admin", role=Role.ADMIN)
    _, operator = create_tenant_user(db, suffix="pm1-operator", role=Role.OPERATOR)
    invoices = [create_invoice(db, tenant, f"PM1-{index}") for index in range(1, 4)]
    created_at = datetime(2026, 2, 3, 9, tzinfo=timezone.utc)

    exception_cases = [
        ExceptionCase(
            client_id=tenant.id,
            invoice_id=invoice.id,
            kind="payment_commitment",
            status="resolved",
            priority=10,
            detail={"fixture": True},
            human_minutes=minutes,
            human_minutes_measured=True,
            resolved_at=created_at + timedelta(hours=index + 1),
            resolution={
                "decision": "confirmed" if index < 2 else "corrected",
                "category": "payment_commitment",
            },
            created_at=created_at,
        )
        for index, (invoice, minutes) in enumerate(
            zip(invoices, [Decimal("10"), Decimal("10"), Decimal("0")], strict=True)
        )
    ]
    db.add_all(exception_cases)
    db.add_all(
        [
            PilotLogEntry(
                client_id=tenant.id,
                related_invoice_id=invoice.id,
                entry_type="manual_work",
                severity="info",
                title=f"Trabajo sintético {index}",
                detail="Texto que no debe exportarse",
                status="resolved",
                occurred_on=date(2026, 2, 3 + index),
                human_minutes=Decimal("12"),
                human_minutes_measured=True,
                labor_accounting="additional",
                created_by=admin.id,
                resolved_by=admin.id,
                resolved_at=created_at + timedelta(hours=index + 2),
                resolution_note="Nota que no debe exportarse",
                created_at=created_at,
            )
            for index, invoice in enumerate(invoices)
        ]
    )
    db.flush()
    db.add(
        PilotLogEntry(
            client_id=tenant.id,
            related_invoice_id=invoices[0].id,
            related_exception_id=exception_cases[0].id,
            entry_type="manual_work",
            severity="info",
            title="Trabajo ya incluido en excepción",
            detail="No debe sumarse dos veces",
            status="resolved",
            occurred_on=date(2026, 2, 6),
            human_minutes=Decimal("99"),
            human_minutes_measured=True,
            labor_accounting="included_in_exception",
            created_by=admin.id,
            resolved_by=admin.id,
            resolved_at=created_at + timedelta(hours=5),
            resolution_note="Contabilizado en excepción",
            created_at=created_at,
        )
    )
    transaction = BankTransaction(
        client_id=tenant.id,
        external_id="PM1-TX-1",
        occurred_on=date(2026, 2, 4),
        amount=Decimal("100000"),
        description="Descripción que no debe exportarse",
        status="matched",
        raw_data={"private": "not-exported"},
        created_at=created_at,
    )
    db.add(transaction)
    db.flush()
    db.add(
        ReconciliationProposal(
            client_id=tenant.id,
            bank_transaction_id=transaction.id,
            candidate_key="pm1-candidate",
            status="confirmed",
            score=Decimal("95"),
            score_breakdown={"amount": 50},
            reviewed_by=admin.id,
            reviewed_at=created_at + timedelta(hours=2),
            review_note="Nota privada",
            created_at=created_at,
        )
    )
    db.commit()

    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    operator_headers = {"Authorization": f"Bearer {_token(client, operator.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    query = "date_from=2026-02-01&date_to=2026-02-28&evidence_kind=synthetic"
    response = client.get(
        f"/api/v1/metrics/human-effort?{query}", headers=admin_headers
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "pm-1-v2"
    assert payload["baseline"]["total_human_minutes"] == "56.00"
    assert payload["baseline"]["minutes_per_managed_invoice"] == "18.67"
    assert payload["baseline"]["manual_action_percent"] == "83.33"
    assert payload["baseline"]["reopenings"] == 0
    assert payload["baseline"]["reopening_measurement_status"] == "not_applicable"
    assert payload["friction_ranking"][0]["key"] == "pilot_log:manual_work"
    assert payload["friction_ranking"][0]["total_human_minutes"] == "36.00"
    assert payload["friction_ranking"][0]["human_minutes_share_percent"] == "64.29"
    assert payload["reconciliation"]["average_decision_cycle_hours"] == "2.00"
    assert payload["reconciliation"]["human_minutes"] is None
    assert payload["reconciliation"]["labor_measurement_status"] == "unavailable"
    assert payload["selected_opportunity"]["friction_key"] == "pilot_log:manual_work"
    assert (
        payload["selected_opportunity"]["pm2_target"]["maximum_total_human_minutes"]
        == "28.80"
    )
    assert payload["pm_g1"]["status"] == "provisional_synthetic"
    assert payload["pm_g1"]["analytical_ready"] is True
    assert payload["pm_g1"]["pm2_authorized"] is False
    assert payload["pm_g1"]["selection_measurement_blockers"] == []
    assert payload["scope"]["pilot_log_entries"] == 4
    assert payload["scope"]["countable_pilot_log_entries"] == 3
    serialized = response.text
    assert tenant.name not in serialized
    assert tenant.rut not in serialized
    assert all(invoice.folio not in serialized for invoice in invoices)
    assert str(tenant.id) not in serialized
    assert "Texto que no debe exportarse" not in serialized
    assert "payment_commitment" not in serialized

    csv_response = client.get(
        f"/api/v1/metrics/human-effort.csv?{query}", headers=admin_headers
    )
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b"\xef\xbb\xbf")
    assert "pilot_log,manual_work" in csv_response.text
    assert tenant.name not in csv_response.text

    markdown_response = client.get(
        f"/api/v1/metrics/human-effort.md?{query}", headers=admin_headers
    )
    assert markdown_response.status_code == 200
    assert "Evidencia sintética" in markdown_response.text
    assert "no aprueba PM-G1" in markdown_response.text
    assert "pilot_log:manual_work" in markdown_response.text

    claimed_real = client.get(
        "/api/v1/metrics/human-effort?date_from=2026-02-01&date_to=2026-02-28"
        "&evidence_kind=authorized_pilot",
        headers=admin_headers,
    )
    assert claimed_real.status_code == 200
    assert claimed_real.json()["pm_g1"]["status"] == "authorization_incomplete"
    assert claimed_real.json()["pm_g1"]["pm2_authorized"] is False

    assert (
        client.get(
            f"/api/v1/metrics/human-effort?{query}", headers=operator_headers
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/metrics/human-effort?{query}", headers=client_headers
        ).status_code
        == 403
    )


def test_pm1_diagnostic_does_not_approve_unverified_real_evidence(
    client: TestClient, db: Session
) -> None:
    tenant, _ = create_tenant_user(db, suffix="pm1-unverified")
    _, admin = create_tenant_user(db, suffix="pm1-unverified-admin", role=Role.ADMIN)
    invoice = create_invoice(db, tenant, "PM1-UNVERIFIED")
    created_at = datetime(2026, 2, 3, 9, tzinfo=timezone.utc)
    db.add_all(
        [
            ExceptionCase(
                client_id=tenant.id,
                invoice_id=invoice.id,
                kind="supervised_review",
                status="resolved",
                priority=index,
                detail={"fixture": True},
                human_minutes=Decimal("10"),
                human_minutes_measured=True,
                resolved_at=created_at + timedelta(hours=1),
                resolution={"decision": "confirmed", "category": "other"},
                created_at=created_at,
            )
            for index in range(3)
        ]
    )
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    response = client.get(
        "/api/v1/metrics/human-effort?date_from=2026-02-01&date_to=2026-02-28"
        "&evidence_kind=authorized_pilot",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["pm_g1"]["status"] == "authorization_incomplete"
    assert response.json()["pm_g1"]["pm2_authorized"] is False
