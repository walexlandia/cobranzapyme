import hashlib
import io
import json
import uuid
from datetime import date
from decimal import Decimal
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import Role
from app.models import Contract, Document, Invoice, Payment, PilotAuthorizationEvent
from tests.conftest import create_invoice, create_tenant_user


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_final_report_is_anonymized_reproducible_and_cannot_approve_synthetic_g4(
    client: TestClient, db: Session
) -> None:
    first, first_user = create_tenant_user(db, suffix="final-report-private-a")
    second, _ = create_tenant_user(db, suffix="final-report-private-b")
    _, admin = create_tenant_user(db, suffix="final-report-admin", role=Role.ADMIN)
    first.baseline_dso = Decimal("50")
    first.baseline_on_time_percent = Decimal("20")
    second.baseline_dso = Decimal("45")
    second.baseline_on_time_percent = Decimal("30")
    first_invoice = create_invoice(db, first, "PRIVATE-FOLIO-A")
    second_invoice = create_invoice(db, second, "PRIVATE-FOLIO-B")
    first_payer_name = first_invoice.payer.legal_name
    db.add_all(
        [
            Payment(
                client_id=first.id,
                invoice_id=first_invoice.id,
                amount=Decimal("100000"),
                paid_on=date(2026, 2, 5),
                verified=True,
                source="manual",
                idempotency_key="final-report-payment-a",
            ),
            Payment(
                client_id=second.id,
                invoice_id=second_invoice.id,
                amount=Decimal("100000"),
                paid_on=date(2026, 2, 6),
                verified=True,
                source="manual",
                idempotency_key="final-report-payment-b",
            ),
        ]
    )
    db.commit()
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    client_headers = {"Authorization": f"Bearer {_token(client, first_user.email)}"}
    query = (
        "date_from=2026-01-01&date_to=2026-02-28&minimum_group_size=1"
        "&evidence_kind=synthetic"
    )

    response = client.get(f"/api/v1/metrics/final-report?{query}", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload)
    assert payload["schema_version"] == "fase-8.2-v1"
    assert payload["g4"]["ready"] is False
    assert payload["g4"]["recommendation"] == "pending"
    assert payload["fingerprint_sha256"]
    assert len(payload["economics_scenarios"]) == 3
    assert payload["backlog_priorities"]
    assert any(row["dimension"] == "payer" for row in payload["segments"])
    assert first.name not in serialized
    assert first.rut not in serialized
    assert first_payer_name not in serialized
    assert "PRIVATE-FOLIO-A" not in serialized
    assert str(first.id) not in serialized
    repeated = client.get(f"/api/v1/metrics/final-report?{query}", headers=admin_headers)
    assert repeated.status_code == 200
    assert repeated.json()["fingerprint_sha256"] == payload["fingerprint_sha256"]

    exported = client.get(
        f"/api/v1/metrics/anonymized-dataset.csv?{query}", headers=admin_headers
    )
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "payer,PAGADOR-" in exported.text
    assert first.name not in exported.text
    assert first.rut not in exported.text

    document = client.get(f"/api/v1/metrics/final-report.md?{query}", headers=admin_headers)
    assert document.status_code == 200
    assert "Informe final V-10" in document.text
    assert "Pendiente de evidencia suficiente" in document.text
    assert first.name not in document.text
    assert client.get(
        f"/api/v1/metrics/final-report?{query}", headers=client_headers
    ).status_code == 403

    snapshot = client.post(
        "/api/v1/metrics/closures",
        headers=admin_headers,
        json={
            "date_from": "2026-01-01",
            "date_to": "2026-02-28",
            "minimum_group_size": 1,
            "evidence_kind": "synthetic",
        },
    )
    assert snapshot.status_code == 201
    assert snapshot.json()["status"] == "prepared"
    package_url = f'/api/v1/metrics/closures/{snapshot.json()["id"]}/package.zip'
    package = client.get(package_url, headers=admin_headers)
    repeated_package = client.get(package_url, headers=admin_headers)
    assert package.status_code == 200
    assert package.headers["content-type"] == "application/zip"
    assert package.content == repeated_package.content
    assert package.headers["x-package-sha256"] == hashlib.sha256(
        package.content
    ).hexdigest()
    with ZipFile(io.BytesIO(package.content)) as archive:
        names = set(archive.namelist())
        assert names == {
            "resumen-ejecutivo.md",
            "informe-final-v10.md",
            "dataset-anonimizado.csv",
            "unit-economics.csv",
            "backlog-priorizado.csv",
            "anexo-evidencia.md",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["draft"] is True
        assert manifest["report_fingerprint_sha256"] == snapshot.json()[
            "report_fingerprint"
        ]
        for entry in manifest["files"]:
            content = archive.read(entry["path"])
            assert entry["size_bytes"] == len(content)
            assert entry["sha256"] == hashlib.sha256(content).hexdigest()
        exported_text = "\n".join(
            archive.read(name).decode("utf-8-sig")
            for name in names
            if name.endswith((".md", ".csv"))
        )
    assert "BORRADOR — EVIDENCIA SINTÉTICA" in exported_text
    assert first.name not in exported_text
    assert first.rut not in exported_text
    assert first_payer_name not in exported_text
    assert "PRIVATE-FOLIO-A" not in exported_text
    assert str(first.id) not in exported_text
    assert client.get(package_url, headers=client_headers).status_code == 403
    blocked = client.post(
        f'/api/v1/metrics/closures/{snapshot.json()["id"]}/decision',
        headers=admin_headers,
        json={
            "decision": "iterate",
            "rationale": "Datos sintéticos: esta decisión debe permanecer bloqueada.",
        },
    )
    assert blocked.status_code == 409
    assert client.post(
        "/api/v1/metrics/closures",
        headers=client_headers,
        json={"date_from": "2026-01-01", "date_to": "2026-02-28"},
    ).status_code == 403


def test_authorized_closure_requires_independent_admin_and_is_immutable(
    client: TestClient, db: Session
) -> None:
    first, _ = create_tenant_user(db, suffix="closure-authorized-a")
    second, _ = create_tenant_user(db, suffix="closure-authorized-b")
    _, preparer = create_tenant_user(
        db, suffix="closure-preparer", role=Role.ADMIN
    )
    _, admin = create_tenant_user(db, suffix="closure-admin", role=Role.ADMIN)
    first.baseline_dso = Decimal("50")
    first.baseline_on_time_percent = Decimal("20")
    second.baseline_dso = Decimal("50")
    second.baseline_on_time_percent = Decimal("20")
    payments = []
    for index in range(10):
        tenant = first if index < 5 else second
        invoice = create_invoice(db, tenant, f"CLOSURE-{index:02d}")
        payments.append(
            Payment(
                client_id=tenant.id,
                invoice_id=invoice.id,
                amount=Decimal("100000"),
                paid_on=date(2026, 2, 5),
                verified=True,
                source="manual",
                idempotency_key=f"closure-authorized-payment-{index}",
            )
        )
    db.add_all(payments)
    db.flush()
    participant_ids = set(
        db.scalars(
            select(Invoice.client_id).where(
                Invoice.issued_on >= date(2026, 1, 1),
                Invoice.issued_on <= date(2026, 2, 28),
            )
        )
    )
    for index, client_id in enumerate(sorted(participant_ids, key=str)):
        contract = db.scalar(
            select(Contract).where(
                Contract.client_id == client_id,
                Contract.active.is_(True),
            )
        )
        if contract is None:
            next_version = int(
                db.scalar(
                    select(func.max(Contract.version)).where(
                        Contract.client_id == client_id
                    )
                )
                or 0
            ) + 1
            contract = Contract(
                client_id=client_id,
                version=next_version,
                rules={},
                active=True,
            )
            db.add(contract)
            db.flush()
        evidence = Document(
            id=uuid.uuid4(),
            client_id=client_id,
            kind="pilot_authorization",
            object_key=f"test/closure-authorization-{client_id}",
            original_name="authorization.txt",
            sha256=f"{index:064x}",
        )
        db.add(evidence)
        db.flush()
        db.add(
            PilotAuthorizationEvent(
                client_id=client_id,
                contract_id=contract.id,
                action="approved",
                channels=["email"],
                authorized_contact_name="Responsable de prueba",
                authorized_contact_email=f"authorized-{index}@example.test",
                valid_from=date(2026, 1, 1),
                valid_until=date(2026, 2, 28),
                evidence_document_id=evidence.id,
                performed_by=preparer.id,
                note="Autorización sintética para probar el flujo técnico.",
                idempotency_key=f"closure-authorization-{client_id}",
            )
        )
    db.commit()
    preparer_headers = {"Authorization": f"Bearer {_token(client, preparer.email)}"}
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    body = {
        "date_from": "2026-01-01",
        "date_to": "2026-02-28",
        "minimum_group_size": 2,
        "evidence_kind": "authorized_pilot",
    }

    prepared = client.post(
        "/api/v1/metrics/closures", headers=preparer_headers, json=body
    )

    assert prepared.status_code == 201
    snapshot = prepared.json()
    assert snapshot["report_data"]["g4"]["ready"] is True
    assert snapshot["report_data"]["authorization_coverage"]["complete"] is True
    assert snapshot["prepared_by"] == str(preparer.id)
    assert client.post(
        f'/api/v1/metrics/closures/{snapshot["id"]}/decision',
        headers=preparer_headers,
        json={
            "decision": "iterate",
            "rationale": "El operador no puede aprobar el cierre que preparó.",
        },
    ).status_code == 409
    first.baseline_dso = Decimal("51")
    db.commit()
    stale = client.post(
        f'/api/v1/metrics/closures/{snapshot["id"]}/decision',
        headers=admin_headers,
        json={
            "decision": "iterate",
            "rationale": "La evidencia cambió y exige preparar un snapshot actualizado.",
        },
    )
    assert stale.status_code == 409
    assert "evidencia cambió" in stale.json()["detail"]
    refreshed = client.post(
        "/api/v1/metrics/closures", headers=preparer_headers, json=body
    )
    assert refreshed.status_code == 201
    refreshed_snapshot = refreshed.json()
    assert refreshed_snapshot["report_fingerprint"] != snapshot["report_fingerprint"]
    snapshot = refreshed_snapshot
    decided = client.post(
        f'/api/v1/metrics/closures/{snapshot["id"]}/decision',
        headers=admin_headers,
        json={
            "decision": "iterate",
            "rationale": "Se aprueba una iteración acotada con revisión en treinta días.",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "decided"
    assert decided.json()["decision"] == "iterate"
    assert decided.json()["report_fingerprint"] == snapshot["report_fingerprint"]
    decided_package = client.get(
        f'/api/v1/metrics/closures/{snapshot["id"]}/package.zip',
        headers=admin_headers,
    )
    assert decided_package.status_code == 200
    with ZipFile(io.BytesIO(decided_package.content)) as archive:
        decided_manifest = json.loads(archive.read("manifest.json"))
        assert decided_manifest["draft"] is False
        assert decided_manifest["closure_status"] == "decided"
        assert decided_manifest["decision"] == "iterate"
        assert "Se aprueba una iteración acotada" not in "\n".join(
            archive.read(name).decode("utf-8-sig")
            for name in archive.namelist()
            if name.endswith((".md", ".csv", ".json"))
        )
    repeated = client.post(
        f'/api/v1/metrics/closures/{snapshot["id"]}/decision',
        headers=admin_headers,
        json={
            "decision": "scale",
            "rationale": "No debe ser posible reemplazar una decisión ya registrada.",
        },
    )
    assert repeated.status_code == 409
