#!/usr/bin/env python3

import json
from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ActorType, Role
from app.models import Contract, DelayCause, Event, PaymentAttribution
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_pm3_report_reconstructs_chains_and_declares_exclusions(
    client: TestClient, db: Session
) -> None:
    first, admin = create_tenant_user(db, suffix="pm3-a", role=Role.ADMIN)
    second, client_user = create_tenant_user(db, suffix="pm3-b")
    first.industry = "servicios_empresariales"
    first.baseline_dso = Decimal(50)
    first.baseline_on_time_percent = Decimal(40)
    second.industry = "construccion"
    second.baseline_dso = Decimal(55)
    second.baseline_on_time_percent = Decimal(35)
    for tenant in (first, second):
        db.add(
            Contract(
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
        )
    db.commit()
    invoices = [
        create_invoice(db, first, "PM3-PRIVATE-A1"),
        create_invoice(db, first, "PM3-PRIVATE-A2"),
        create_invoice(db, second, "PM3-PRIVATE-B1"),
        create_invoice(db, second, "PM3-PRIVATE-B2"),
        create_invoice(db, first, "PM3-EXCLUDED"),
    ]
    first_payer = invoices[0].payer_id
    second_payer = invoices[1].payer_id
    invoices[2].payer_id = first_payer
    invoices[3].payer_id = second_payer
    for index, invoice in enumerate(invoices[:4]):
        db.add_all(
            [
                Event(
                    client_id=invoice.client_id,
                    invoice_id=invoice.id,
                    event_type="workflow.action_ready",
                    actor_type=ActorType.SYSTEM,
                    mode="simulation",
                    payload={"synthetic": True},
                ),
                DelayCause(
                    client_id=invoice.client_id,
                    invoice_id=invoice.id,
                    category="purchase_order" if index % 2 == 0 else "missing_document",
                    source="manual",
                ),
            ]
        )
    db.commit()
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, client_user.email)}"}
    for index, invoice in enumerate(invoices):
        payment = client.post(
            "/api/v1/payments/manual",
            data={
                "client_id": str(invoice.client_id),
                "invoice_id": str(invoice.id),
                "amount": "100000",
                "paid_on": date.today().isoformat(),
                "reference": f"PM3-SYNTHETIC-{index}",
            },
            files={
                "evidence": (
                    f"pm3-{index}.txt",
                    BytesIO(f"evidencia sintética {index}".encode()),
                    "text/plain",
                )
            },
            headers=admin_headers,
        )
        assert payment.status_code == 200, payment.text

    query = (
        f"date_from={date.today().isoformat()}&date_to={date.today().isoformat()}"
        "&minimum_group_size=2&evidence_kind=synthetic"
    )
    response = client.get(
        f"/api/v1/optimizations/comparables-attribution/report?{query}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    report = response.json()
    assert report["population"]["verified_payments"] == 5
    assert report["population"]["included_payments"] == 4
    assert report["population"]["excluded_payments"] == 1
    assert report["population"]["traceability_coverage_percent"] == "80.00"
    assert report["traceability"] == {
        "chain_complete": True,
        "included_payment_count": 4,
        "unique_payment_count": 4,
        "duplicate_count": 0,
        "exclusions_reconciled": True,
    }
    assert report["interpretation"] == {
        "defensible_attribution": 4,
        "correlation_only": 1,
        "uncertain_or_ineligible": 0,
    }
    assert report["exclusions"][0]["reason"] == "management_evidence_missing"
    assert {row["dimension"] for row in report["cohorts"]} == {
        "amount_band",
        "cause",
        "client",
        "industry",
        "payer",
    }
    concentrations = {
        row["dimension"]: row["share_percent"]
        for row in report["concentrations"]
    }
    assert concentrations == {
        "client": "50.00",
        "payer": "50.00",
        "industry": "50.00",
        "amount_band": "100.00",
        "cause": "50.00",
    }
    assert report["pm_g3"]["status"] == "passed_synthetic"
    assert report["pm_g3"]["local_phase_complete"] is True
    assert report["pm_g3"]["pm4_authorized"] is False
    assert report["authorization_coverage"]["complete"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    for forbidden in (
        first.name,
        first.rut,
        second.name,
        second.rut,
        "PM3-PRIVATE-A1",
        str(invoices[0].id),
    ):
        assert forbidden not in serialized
    assert len(list(db.scalars(select(PaymentAttribution)))) == 5

    csv_response = client.get(
        f"/api/v1/optimizations/comparables-attribution/matrix.csv?{query}",
        headers=admin_headers,
    )
    markdown = client.get(
        f"/api/v1/optimizations/comparables-attribution/report.md?{query}",
        headers=admin_headers,
    )
    assert csv_response.status_code == 200
    assert "on_time_delta_points" in csv_response.text
    assert "PM3-PRIVATE" not in csv_response.text
    assert markdown.status_code == 200
    assert "passed_synthetic" in markdown.text
    assert client.get(
        f"/api/v1/optimizations/comparables-attribution/report?{query}",
        headers=client_headers,
    ).status_code == 403


def test_pm3_authorized_label_does_not_bypass_authorization_gate(
    client: TestClient, db: Session
) -> None:
    tenant, admin = create_tenant_user(db, suffix="pm3-auth", role=Role.ADMIN)
    tenant.industry = "ingenieria"
    tenant.baseline_dso = Decimal(45)
    tenant.baseline_on_time_percent = Decimal(50)
    db.commit()
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    today = date.today().isoformat()
    report = client.get(
        "/api/v1/optimizations/comparables-attribution/report"
        f"?date_from={today}&date_to={today}&evidence_kind=authorized_pilot",
        headers=headers,
    )
    assert report.status_code == 200
    assert report.json()["pm_g3"]["status"] == "needs_evidence"
    assert report.json()["pm_g3"]["pm4_authorized"] is False
    assert client.get(
        "/api/v1/optimizations/comparables-attribution/report"
        "?date_from=2026-10-29&date_to=2026-10-28",
        headers=headers,
    ).status_code == 422
