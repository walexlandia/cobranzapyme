"""Checks that run without network access or a PostgreSQL driver."""

import ast
import importlib.util
import io
import os
import sys
import types
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from pydantic import BaseModel, ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.base import Base  # noqa: E402
from app import models  # noqa: E402,F401
from app.domain import InvoiceStatus  # noqa: E402
from app.schemas import (  # noqa: E402
    ContractRules,
    ClassificationPolicyUpdate,
    ExceptionReviewCommand,
    ExceptionResponseDraftCreate,
    DeliveryStatusUpdate,
    InboundMessageCreate,
    ManualResponseCreate,
    PayerProfileProposalChanges,
    PayerProfileView,
    PayerRequirements,
    PreventiveConfirmationCreate,
    MessageTemplateCreate,
)
from app.services.classification import (  # noqa: E402
    _classification_result,
    _extract_amounts,
    _extract_dates,
)
from app.services.communications import safety_flags, validate_template_text  # noqa: E402
from app.services.invoice_import import (  # noqa: E402
    parse_contact_file,
    parse_invoice_file,
    parse_sii_status_file,
)
from app.services.payability import checklist_status, requirement_specs  # noqa: E402
from app.services.payments import parse_bank_statement_file  # noqa: E402
from app.services.workflow_engine import determine_stage, next_allowed_at, stage_windows  # noqa: E402
from app.utils.rut import normalize_rut  # noqa: E402


def check_rut() -> None:
    assert normalize_rut("76.086.428-5") == "76086428-5"
    try:
        normalize_rut("76.086.428-4")
    except ValueError:
        pass
    else:
        raise AssertionError("An invalid RUT was accepted")


def check_csv_import() -> None:
    content = (
        "RUT receptor;Razón social;Folio;Fecha emisión;Fecha vencimiento;Monto total;OC\n"
        "76.086.428-5;Pagador Demo;F-100;01-10-2026;31-10-2026;$1.250.000;OC-88\n"
    ).encode()
    rows, issues = parse_invoice_file("facturas.csv", content)
    assert not issues, issues
    assert rows[0].total_amount == 1_250_000
    assert rows[0].payer_rut == "76086428-5"


def check_xlsx_import() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["RUT receptor", "Razón social", "Folio", "Fecha emisión", "Fecha vencimiento", "Monto total"])
    sheet.append(["76.086.428-5", "Pagador Demo", "F-200", "2026-10-01", "2026-10-31", 900000])
    payload = io.BytesIO()
    workbook.save(payload)
    rows, issues = parse_invoice_file("facturas.xlsx", payload.getvalue())
    assert not issues, issues
    assert rows[0].folio == "F-200"


def check_contact_import() -> None:
    content = (
        "RUT pagador;Razón social;Nombre contacto;Rol;Correo;Teléfono\n"
        "76.086.428-5;Pagador Demo;María Demo;Cuentas por pagar;maria@example.com;+56911111111\n"
    ).encode()
    rows, issues = parse_contact_file("contactos.csv", content)
    assert not issues, issues
    assert rows[0].role == "accounts_payable"
    assert str(rows[0].email) == "maria@example.com"


def check_sii_status_import() -> None:
    content = (
        "Tipo documento;Folio;Estado SII;Fecha consulta;Plazo reclamo;Detalle\n"
        "factura;F-100;Reclamada;2026-10-14;2026-10-15;OC inválida\n"
    ).encode()
    rows, issues = parse_sii_status_file("sii.csv", content)
    assert not issues, issues
    assert rows[0].sii_status == "claimed"
    assert rows[0].claim_deadline == date(2026, 10, 15)


def check_bank_statement_import() -> None:
    content = (
        "id movimiento,fecha,monto,descripcion,rut contraparte,moneda\n"
        "TX-DEMO-001,2026-10-15,1250000,Transferencia ficticia,76.086.428-5,CLP\n"
    ).encode()
    rows, issues = parse_bank_statement_file("cartola.csv", content)
    assert not issues, issues
    assert rows[0].external_id == "TX-DEMO-001"
    assert rows[0].counterparty_rut == "76086428-5"
    assert rows[0].amount == Decimal("1250000.00")


def check_payability_rules() -> None:
    invoice = models.Invoice(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        payer_id=uuid.uuid4(),
        folio="PAY-1",
        issued_on=date(2026, 10, 1),
        due_on=date(2026, 10, 31),
        total_amount=100000,
        status=InvoiceStatus.ISSUED,
    )
    requirements = PayerRequirements(
        requires_purchase_order=True,
        requires_hes=True,
    )
    specs = requirement_specs(invoice, requirements)
    blocking = [spec for spec in specs if spec["required"] and spec["blocks_payability"]]
    items = [
        models.PayabilityItem(
            client_id=invoice.client_id,
            invoice_id=invoice.id,
            item_type=spec["item_type"],
            label=spec["label"],
            status="fulfilled",
            required=spec["required"],
            blocks_payability=spec["blocks_payability"],
            responsible_role=spec["responsible_role"],
            evidence={},
        )
        for spec in blocking
    ]
    status, completed, total, missing = checklist_status(
        invoice, items, requirements=requirements, today=date(2026, 10, 20)
    )
    assert status == "payable"
    assert completed == total == len(blocking)
    assert not missing


def check_sii_deadline_alert() -> None:
    invoice = models.Invoice(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        payer_id=uuid.uuid4(),
        folio="SII-RISK-1",
        issued_on=date(2026, 1, 10),
        due_on=date(2026, 2, 9),
        total_amount=100000,
        status=InvoiceStatus.ISSUED,
    )
    requirements = PayerRequirements(risk_days_before_due=7)
    item = models.PayabilityItem(
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        item_type="sii_acceptance",
        label="Aceptación en SII",
        status="pending",
        required=True,
        blocks_payability=True,
        responsible_role="client",
        evidence={"sii_status": "pending", "claim_deadline": "2026-01-20"},
    )
    status, _, _, _ = checklist_status(
        invoice,
        [item],
        requirements=requirements,
        today=date(2026, 1, 25),
    )
    assert status == "at_risk"


def check_preventive_confirmation_contract() -> None:
    valid = PreventiveConfirmationCreate(
        approval_status="approved",
        approved_at=datetime(2026, 1, 25, 13, 0, tzinfo=timezone.utc),
        scheduled_payment_date=date(2026, 2, 5),
        reference="Confirmación CxP 1842",
    )
    assert valid.scheduled_payment_date == date(2026, 2, 5)
    invalid_payloads = [
        {
            "approval_status": "approved",
            "approved_at": datetime(2026, 1, 25, 13, 0, tzinfo=timezone.utc),
        },
        {
            "approval_status": "rejected",
            "approved_at": datetime(2026, 1, 25, 13, 0, tzinfo=timezone.utc),
            "scheduled_payment_date": date(2026, 2, 5),
        },
    ]
    for payload in invalid_payloads:
        try:
            PreventiveConfirmationCreate(**payload)
        except ValidationError:
            continue
        raise AssertionError(f"An invalid preventive confirmation was accepted: {payload}")


def check_global_payer_profile_contract() -> None:
    public_fields = set(PayerProfileView.model_fields)
    assert public_fields == {
        "id",
        "payer_id",
        "version",
        "updated_at",
        "operational_requirements",
        "supplier_portal_url",
        "supplier_portal_instructions",
        "corporate_channels",
        "payment_cycle",
    }
    forbidden = {
        "client_id",
        "invoice_id",
        "amount",
        "private_notes",
        "personal_contacts",
        "conversations",
    }
    assert public_fields.isdisjoint(forbidden)


def check_communication_safety_contract() -> None:
    validate_template_text(
        "Seguimiento · {client_name}",
        "Hola {recipient_name}, revisamos {invoice_summary}. {action_request}",
    )
    assert safety_flags(None, "Iniciaremos una demanda y embargo") == [
        "threat",
        "legal_pressure",
    ]
    try:
        validate_template_text(None, "Hola {unknown_field}, mensaje suficientemente largo")
    except ValueError:
        pass
    else:
        raise AssertionError("An unknown communication template field was accepted")
    payload = MessageTemplateCreate(
        client_id=uuid.uuid4(),
        template_key="payment_due",
        channel="email",
        stage="due",
        recipient_role="accounts_payable",
        tone="cordial",
        subject_template="Factura · {payer_name}",
        body_template="Hola {recipient_name}, {invoice_summary}",
    )
    assert payload.approved is False


def check_inbound_communication_contract() -> None:
    client_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    inbound = InboundMessageCreate(
        client_id=client_id,
        channel="email",
        provider_id="local-webhook-001",
        sender="cuentas.por.pagar@example.test",
        body="Factura recibida y programada para pago.",
        invoice_folios=["DEMO-001"],
        attachments=[{"original_name": "acuse.pdf"}],
    )
    manual = ManualResponseCreate(
        client_id=client_id,
        invoice_ids=[invoice_id],
        channel="phone",
        body="Confirmación registrada por teléfono.",
    )
    status = DeliveryStatusUpdate(client_id=client_id, status="read")
    assert inbound.attachments[0].kind == "reply_attachment"
    assert manual.invoice_ids == [invoice_id]
    assert status.status == "read"


def check_local_classification_rules() -> None:
    category, confidence, evidence = _classification_result(
        "Confirmamos que el pago quedó programado para el 24/10/2026 por $1.250.000."
    )
    assert category == "payment_scheduled"
    assert confidence >= 0.9
    assert evidence["ambiguous"] is False
    assert _extract_dates("Pagaremos el 24/10/2026 y no el 2026-10-25") == [
        "2026-10-24",
        "2026-10-25",
    ]
    assert _extract_amounts("Monto CLP 1.250.000") == [1250000]
    category, confidence, _ = _classification_result("Gracias por la información.")
    assert category == "other"
    assert confidence < 0.9
    assert _classification_result("El pago fue efectuado esta mañana.")[0] == "paid"
    assert _classification_result("La orden de compra está pendiente.")[0] == "missing_oc_hes"
    assert _classification_result("Los datos bancarios están incorrectos.")[0] == "supplier_data_issue"


def check_supervision_contract() -> None:
    client_id = uuid.uuid4()
    review = ExceptionReviewCommand(
        client_id=client_id,
        category="payment_scheduled",
        extracted_data={"payment_dates": ["2026-10-24"]},
        human_minutes="4.5",
    )
    assert review.checklist_updates == []
    assert review.workflow_stage is None
    assert ClassificationPolicyUpdate(
        client_id=client_id, mode="supervised"
    ).mode == "supervised"
    assert PayerProfileProposalChanges.model_validate(
        {"payment_cycle": "Todos los viernes"}
    ).model_dump(exclude_unset=True) == {"payment_cycle": "Todos los viernes"}
    try:
        PayerProfileProposalChanges.model_validate({"campo_inventado": "no permitido"})
    except ValidationError:
        pass
    else:
        raise AssertionError("Profile proposals must reject unknown fields")
    response = ExceptionResponseDraftCreate(
        client_id=client_id,
        channel="email",
        subject="Respuesta segura",
        body="Contenido preparado para revisión humana.",
    )
    assert response.channel == "email"


def check_openapi_contract() -> None:
    """Compile the HTTP contract without loading the incompatible global settings package."""

    shim = types.ModuleType("pydantic_settings")

    class OfflineBaseSettings(BaseModel):
        def __init__(self, **data: object) -> None:
            for name in type(self).model_fields:
                value = os.getenv(name.upper())
                if value is not None:
                    data.setdefault(name, value)
            super().__init__(**data)

    shim.BaseSettings = OfflineBaseSettings
    shim.SettingsConfigDict = dict
    previous_module = sys.modules.get("pydantic_settings")
    previous_url = os.environ.get("DATABASE_URL")
    try:
        sys.modules["pydantic_settings"] = shim
        os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
        from app.main import app

        schema = app.openapi()
        assert len(schema["paths"]) >= 29
        assert (
            "/api/v1/payability/invoices/{invoice_id}/preventive-confirmation"
            in schema["paths"]
        )
        assert "PreventiveConfirmationCreate" in schema["components"]["schemas"]
        assert "/api/v1/communications/messages" in schema["paths"]
        assert "/api/v1/communications/templates" in schema["paths"]
        assert "/api/v1/communications/inbound/simulate" in schema["paths"]
        assert "/api/v1/communications/manual-responses" in schema["paths"]
        assert (
            "/api/v1/communications/messages/{message_id}/delivery-status"
            in schema["paths"]
        )
        assert "/api/v1/exceptions" in schema["paths"]
        assert "/api/v1/exceptions/{exception_id}/review" in schema["paths"]
        assert "/api/v1/evaluation/sets" in schema["paths"]
        assert "/api/v1/evaluation/report" in schema["paths"]
        assert "/api/v1/evaluation/report.csv" in schema["paths"]
        assert "/api/v1/classification-policies" in schema["paths"]
        assert "/api/v1/payer-profile-proposals" in schema["paths"]
        assert (
            "/api/v1/communications/exception-responses/{exception_id}/draft"
            in schema["paths"]
        )
        assert "/api/v1/payments/manual" in schema["paths"]
        assert "/api/v1/payments/bank-statements" in schema["paths"]
        assert "/api/v1/payments/reconciliation-proposals" in schema["paths"]
        assert "/api/v1/payments/commission-report" in schema["paths"]
        assert "/api/v1/payments/commission-report.csv" in schema["paths"]
        assert "CommissionReportView" in schema["components"]["schemas"]
        assert "/api/v1/access-logs" in schema["paths"]
        assert "/api/v1/pilot/authorizations" in schema["paths"]
        assert "/api/v1/pilot/readiness" in schema["paths"]
    finally:
        if previous_module is None:
            sys.modules.pop("pydantic_settings", None)
        else:
            sys.modules["pydantic_settings"] = previous_module
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def check_schema_compiles_for_postgresql() -> None:
    expected = {
        "clients", "users", "contracts", "payers", "payer_profiles",
        "client_payer_relations", "contacts", "invoices", "payability_items",
        "documents", "messages", "payments", "bank_transactions",
        "exception_cases", "workflow_states", "workflow_controls", "workflow_jobs", "events",
        "payer_profile_revisions", "delay_causes",
        "message_templates", "communication_threads", "message_invoices",
        "message_documents",
        "message_classifications",
        "evaluation_sets", "evaluation_examples", "classification_policies",
        "payer_profile_proposals", "reconciliation_proposals", "reconciliation_items",
        "payment_attributions",
        "data_access_logs",
        "pilot_authorization_events",
    }
    assert set(Base.metadata.tables) == expected
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=dialect))
        assert "CREATE TABLE" in sql
    private_tables = expected - {
        "clients", "users", "payers", "payer_profiles", "payer_profile_revisions"
    }
    for table_name in private_tables:
        assert "client_id" in Base.metadata.tables[table_name].columns


def check_migration_chain() -> None:
    migration_dir = ROOT / "backend" / "migrations" / "versions"
    revisions: dict[str, tuple[str | None, Path]] = {}
    for path in sorted(migration_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assignments: dict[str, object] = {}
        functions = set()
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                value = node.value
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    assignments[target.id] = ast.literal_eval(value)
            elif isinstance(node, ast.FunctionDef):
                functions.add(node.name)
        revision = assignments.get("revision")
        down_revision = assignments.get("down_revision")
        assert isinstance(revision, str), f"Missing revision in {path.name}"
        assert revision not in revisions, f"Duplicate migration revision {revision}"
        assert down_revision is None or isinstance(down_revision, str)
        assert {"upgrade", "downgrade"}.issubset(functions), f"Incomplete migration {path.name}"
        revisions[revision] = (down_revision, path)
    assert revisions, "No migrations found"
    heads = set(revisions)
    for down_revision, path in revisions.values():
        if down_revision is not None:
            assert down_revision in revisions, f"Unknown parent {down_revision} in {path.name}"
            heads.discard(down_revision)
    assert heads == {"0012"}, f"Unexpected migration heads: {sorted(heads)}"
    current: str | None = "0012"
    visited = []
    while current is not None:
        assert current not in visited, f"Migration cycle at {current}"
        visited.append(current)
        current = revisions[current][0]
    assert len(visited) == len(revisions), "Disconnected migration branch"


def check_migrations_match_models() -> None:
    class OperationRecorder:
        def __init__(self) -> None:
            self.tables: dict[str, set[str]] = {}

        def create_table(self, name: str, *elements: object, **_: object) -> None:
            assert name not in self.tables, f"Migration creates table twice: {name}"
            self.tables[name] = {
                element.name
                for element in elements
                if hasattr(element, "name") and element.__class__.__name__ == "Column"
            }

        def add_column(self, table: str, column: object) -> None:
            assert table in self.tables, f"Migration adds column to unknown table: {table}"
            name = getattr(column, "name")
            assert name not in self.tables[table], f"Migration adds column twice: {table}.{name}"
            self.tables[table].add(name)

        def __getattr__(self, name: str):
            if name.startswith(("create_", "execute")):
                return lambda *args, **kwargs: None
            raise AttributeError(name)

    recorder = OperationRecorder()
    alembic_module = types.ModuleType("alembic")
    alembic_module.op = recorder
    previous = sys.modules.get("alembic")
    try:
        sys.modules["alembic"] = alembic_module
        migration_paths = sorted((ROOT / "backend" / "migrations" / "versions").glob("*.py"))
        for index, path in enumerate(migration_paths):
            spec = importlib.util.spec_from_file_location(f"offline_migration_{index}", path)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.upgrade()
    finally:
        if previous is None:
            sys.modules.pop("alembic", None)
        else:
            sys.modules["alembic"] = previous
    model_tables = {
        name: set(table.columns.keys()) for name, table in Base.metadata.tables.items()
    }
    assert set(recorder.tables) == set(model_tables), (
        f"Migration/model table mismatch: migrations={sorted(recorder.tables)} "
        f"models={sorted(model_tables)}"
    )
    mismatches = {
        table: {
            "missing_in_migrations": sorted(model_tables[table] - recorder.tables[table]),
            "missing_in_models": sorted(recorder.tables[table] - model_tables[table]),
        }
        for table in model_tables
        if recorder.tables[table] != model_tables[table]
    }
    assert not mismatches, f"Migration/model column mismatch: {mismatches}"


def check_phase6_operational_assets() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    secure = (ROOT / "compose.secure.yaml").read_text(encoding="utf-8")
    nginx = (ROOT / "infra" / "nginx" / "recupera.conf").read_text(encoding="utf-8")
    assert "sleep 86400" in compose
    assert "pg_dump --format=custom" in compose
    assert "DOCUMENT_ENCRYPTION_KEY" in secure and ":?" in secure
    assert "ports: !reset []" in secure
    assert "ssl_protocols TLSv1.2 TLSv1.3" in nginx
    assert (ROOT / "scripts" / "backup-postgres.ps1").is_file()
    assert (ROOT / "scripts" / "verify-backup-restore.ps1").is_file()
    assert (ROOT / "scripts" / "generate-local-tls.py").is_file()
    assert (ROOT / "docs" / "fase-6" / "checklist-g3.md").is_file()


def check_workflow_rules() -> None:
    class InvoiceStub:
        issued_on = date(2026, 10, 1)
        due_on = date(2026, 10, 31)
        status = InvoiceStatus.ISSUED

    rules = ContractRules(window_start="09:00", window_end="18:00")
    assert determine_stage(InvoiceStub(), date(2026, 10, 25), rules) == "preventive"
    saturday = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)
    local_schedule = next_allowed_at(saturday, rules).astimezone(ZoneInfo("America/Santiago"))
    assert local_schedule.isoformat().startswith("2026-10-19T09:00:00")


def check_complete_stage_windows() -> None:
    class InvoiceStub:
        issued_on = date(2026, 10, 1)
        due_on = date(2026, 10, 31)

    stages = [window.stage for window in stage_windows(InvoiceStub(), ContractRules())]
    assert stages == [
        "emission",
        "documental",
        "preventive",
        "due",
        "early_arrears",
        "escalation",
    ]


def main() -> None:
    checks = [
        check_rut,
        check_csv_import,
        check_xlsx_import,
        check_contact_import,
        check_sii_status_import,
        check_bank_statement_import,
        check_payability_rules,
        check_sii_deadline_alert,
        check_preventive_confirmation_contract,
        check_global_payer_profile_contract,
        check_communication_safety_contract,
        check_inbound_communication_contract,
        check_local_classification_rules,
        check_supervision_contract,
        check_openapi_contract,
        check_schema_compiles_for_postgresql,
        check_migration_chain,
        check_migrations_match_models,
        check_phase6_operational_assets,
        check_workflow_rules,
        check_complete_stage_windows,
    ]
    for check in checks:
        check()
        print(f"PASS {check.__name__}")
    print(f"PASS {len(checks)} offline checks")


if __name__ == "__main__":
    main()

