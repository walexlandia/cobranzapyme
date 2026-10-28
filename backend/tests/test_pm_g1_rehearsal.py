#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.document_crypto import decrypt_document_content
from app.domain import Role
from app.models import Contact, Contract, Document, MessageTemplate, PilotLogEntry
from app.schemas import ContractRules
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _run_gate_cli(root: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "generate_pm1_diagnostic.py"),
            "--date-from",
            "2026-02-01",
            "--date-to",
            "2026-02-28",
            "--evidence-kind",
            "authorized_pilot",
            "--output-dir",
            str(output_dir),
            "--require-approved",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pm_g1_full_rehearsal_approves_then_blocks_after_revocation(
    client: TestClient, db: Session
) -> None:
    tenants = []
    contracts = []
    admin = None
    for index in range(3):
        tenant, user = create_tenant_user(
            db,
            suffix=f"pm-g1-rehearsal-{index}",
            role=Role.ADMIN if index == 0 else Role.CLIENT,
        )
        admin = user if index == 0 else admin
        invoice = create_invoice(db, tenant, f"PM-G1-{index + 1}")
        contract = Contract(
            client_id=tenant.id,
            version=1,
            rules=ContractRules(channels=["email"]).model_dump(mode="json"),
            active=True,
        )
        db.add(contract)
        db.flush()
        db.add_all(
            [
                Contact(
                    client_id=tenant.id,
                    payer_id=invoice.payer_id,
                    name=f"Contacto sintético {index + 1}",
                    role="accounts_payable",
                    email=f"contacto-{index + 1}@example.test",
                ),
                MessageTemplate(
                    client_id=tenant.id,
                    template_key="payment_due",
                    version=1,
                    channel="email",
                    stage="due",
                    recipient_role="accounts_payable",
                    tone="cordial",
                    subject_template="Factura {{ invoice.folio }}",
                    body_template="Mensaje sintético para {{ payer.legal_name }}.",
                    approved=True,
                    active=True,
                ),
            ]
        )
        for case_index in range(3):
            created_at = datetime(2026, 2, 3 + case_index, 9, tzinfo=UTC)
            db.add(
                PilotLogEntry(
                    client_id=tenant.id,
                    related_invoice_id=invoice.id,
                    entry_type="manual_work",
                    severity="info",
                    title=f"Medición sintética {index + 1}-{case_index + 1}",
                    detail="Ensayo local sin datos ni contactos reales.",
                    status="resolved",
                    occurred_on=created_at.date(),
                    human_minutes=Decimal(10),
                    human_minutes_measured=True,
                    labor_accounting="additional",
                    created_by=admin.id,
                    resolved_by=admin.id,
                    resolved_at=created_at + timedelta(minutes=10),
                    resolution_note="Caso sintético cerrado.",
                    created_at=created_at,
                )
            )
        tenants.append(tenant)
        contracts.append(contract)
    db.commit()
    assert admin is not None
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    query = (
        "date_from=2026-02-01&date_to=2026-02-28"
        "&evidence_kind=authorized_pilot"
    )

    before = client.get(f"/api/v1/metrics/human-effort?{query}", headers=headers)
    assert before.status_code == 200
    assert before.json()["pm_g1"]["status"] == "authorization_incomplete"

    authorization_ids = []
    evidence = b"mandato sintetico exclusivo para ensayo PM-G1"
    for index, (tenant, contract) in enumerate(zip(tenants, contracts, strict=True)):
        approved = client.post(
            "/api/v1/pilot/authorizations",
            data={
                "client_id": str(tenant.id),
                "contract_id": str(contract.id),
                "channels_json": '["email"]',
                "authorized_contact_name": f"Representante sintético {index + 1}",
                "authorized_contact_email": f"representante-{index + 1}@example.com",
                "valid_from": "2026-02-01",
                "valid_until": "2099-12-31",
                "note": "Ensayo local; no constituye autorización real.",
            },
            files={
                "evidence": (
                    f"mandato-sintetico-{index + 1}.txt",
                    BytesIO(evidence + str(index).encode()),
                    "text/plain",
                )
            },
            headers=headers,
        )
        assert approved.status_code == 201, approved.text
        authorization_ids.append(approved.json()["id"])
        readiness = client.get(
            f"/api/v1/pilot/readiness?client_id={tenant.id}", headers=headers
        )
        assert readiness.status_code == 200
        assert readiness.json()["ready"] is True
        document = db.get(
            Document, uuid.UUID(approved.json()["evidence_document_id"])
        )
        assert document is not None
        assert document.encryption_version == "aesgcm-v1"
        assert document.content != evidence
        assert decrypt_document_content(document) == evidence + str(index).encode()

    approved_report = client.get(
        f"/api/v1/metrics/human-effort?{query}", headers=headers
    )
    assert approved_report.status_code == 200
    assert approved_report.json()["pm_g1"]["status"] == "approved"
    assert approved_report.json()["pm_g1"]["pm2_authorized"] is True
    assert approved_report.json()["pm_g1"]["authorization_coverage"] == {
        "participating_clients": 3,
        "authorized_clients": 3,
        "complete": True,
    }

    rehearsal_root = os.environ.get("PM_G1_REHEARSAL_ROOT")
    if rehearsal_root:
        root = Path(rehearsal_root).resolve()
        approved_cli = _run_gate_cli(root, Path("/tmp/pm-g1-approved"))
        assert approved_cli.returncode == 0, approved_cli.stderr
        approved_summary = json.loads(approved_cli.stdout.strip().splitlines()[-1])
        assert approved_summary["approved"] is True
        assert approved_summary["pm_g1"] == "approved"
        assert not (root / "release" / "pm-g1-rehearsal").exists()

    revoked = client.post(
        f"/api/v1/pilot/authorizations/{authorization_ids[0]}/revoke",
        json={
            "client_id": str(tenants[0].id),
            "note": "Revocación sintética para verificar cierre del gate.",
        },
        headers=headers,
    )
    assert revoked.status_code == 201
    blocked_report = client.get(
        f"/api/v1/metrics/human-effort?{query}", headers=headers
    )
    assert blocked_report.status_code == 200
    assert blocked_report.json()["pm_g1"]["status"] == "authorization_incomplete"
    assert blocked_report.json()["pm_g1"]["pm2_authorized"] is False

    if rehearsal_root:
        blocked_cli = _run_gate_cli(root, Path("/tmp/pm-g1-revoked"))
        assert blocked_cli.returncode == 2, blocked_cli.stderr
        blocked_summary = json.loads(blocked_cli.stdout.strip().splitlines()[-1])
        assert blocked_summary["approved"] is False
        assert blocked_summary["pm_g1"] == "authorization_incomplete"
