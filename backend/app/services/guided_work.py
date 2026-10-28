import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType
from app.models import Client, Event, GuidedWorkSession, Invoice, PilotLogEntry, User
from app.schemas import GuidedWorkComplete, GuidedWorkStart

WORKFLOW_KEY = "weekly_portfolio_review"
GUIDANCE_VERSION = "pm-2-v1"
BASELINE_MINUTES_PER_CASE = Decimal("18.00")
TARGET_MINUTES_PER_CASE = Decimal("14.40")
MINIMUM_BENCHMARK_CASES = 3
CHECKLIST = [
    {
        "key": "review_portfolio_snapshot",
        "label": "Revisar saldos y vencimientos",
        "instruction": "Identificar facturas vencidas, próximas a vencer y pausadas sin modificar estados.",
        "target_view": "portfolio",
    },
    {
        "key": "verify_payability_blockers",
        "label": "Verificar bloqueos de pagabilidad",
        "instruction": "Confirmar requisitos pendientes antes de decidir cualquier seguimiento.",
        "target_view": "payability",
    },
    {
        "key": "review_open_exceptions",
        "label": "Revisar excepciones abiertas",
        "instruction": "Priorizar casos con evidencia y separar los que requieren revisión adicional.",
        "target_view": "exceptions",
    },
    {
        "key": "choose_follow_up",
        "label": "Elegir el siguiente paso",
        "instruction": "Una persona elige entre no actuar, preparar seguimiento o escalar revisión.",
        "target_view": "pilot_operations",
    },
    {
        "key": "record_outcome",
        "label": "Registrar resultado y minutos",
        "instruction": "Cerrar la sesión con minutos reales; la guía no ejecuta la decisión elegida.",
        "target_view": "pilot_operations",
    },
]
SAFETY_CONSTRAINTS = [
    "No envía mensajes ni contacta pagadores.",
    "No registra pagos ni decide conciliaciones.",
    "No cambia facturas, contratos, requisitos o excepciones.",
    "Toda decisión permanece bajo aprobación humana y queda auditada.",
]


def guide_payload() -> dict[str, Any]:
    return {
        "workflow_key": WORKFLOW_KEY,
        "title": "Revisión semanal de cartera guiada",
        "guidance_version": GUIDANCE_VERSION,
        "baseline_minutes_per_case": BASELINE_MINUTES_PER_CASE,
        "target_minutes_per_case": TARGET_MINUTES_PER_CASE,
        "steps": CHECKLIST,
        "safety_constraints": SAFETY_CONSTRAINTS,
    }


def _idempotency_digest(client_id: uuid.UUID, raw_key: str) -> str:
    normalized = raw_key.strip().casefold()
    return hashlib.sha256(f"{client_id}:{WORKFLOW_KEY}:{normalized}".encode()).hexdigest()


def start_guided_work(
    db: Session,
    *,
    payload: GuidedWorkStart,
    actor: User,
) -> tuple[GuidedWorkSession, bool]:
    client = db.get(Client, payload.client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if payload.invoice_id is not None:
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.id == payload.invoice_id,
                Invoice.client_id == payload.client_id,
            )
        )
        if invoice is None:
            raise HTTPException(status_code=404, detail="Factura relacionada no encontrada")
    digest = _idempotency_digest(payload.client_id, payload.idempotency_key)
    existing = db.scalar(
        select(GuidedWorkSession).where(GuidedWorkSession.idempotency_key == digest)
    )
    if existing is not None:
        if existing.invoice_id != payload.invoice_id:
            raise HTTPException(
                status_code=409,
                detail="La clave de idempotencia ya identifica otra solicitud",
            )
        return existing, False
    session = GuidedWorkSession(
        client_id=payload.client_id,
        invoice_id=payload.invoice_id,
        workflow_key=WORKFLOW_KEY,
        guidance_version=GUIDANCE_VERSION,
        idempotency_key=digest,
        status="open",
        checklist_snapshot=CHECKLIST,
        completed_step_keys=[],
        baseline_minutes=BASELINE_MINUTES_PER_CASE,
        started_by=actor.id,
    )
    try:
        with db.begin_nested():
            db.add(session)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(GuidedWorkSession).where(
                GuidedWorkSession.idempotency_key == digest
            )
        )
        if existing is None:
            raise
        if existing.invoice_id != payload.invoice_id:
            raise HTTPException(
                status_code=409,
                detail="La clave de idempotencia ya identifica otra solicitud",
            )
        return existing, False
    record_event(
        db,
        client_id=session.client_id,
        invoice_id=session.invoice_id,
        event_type="optimization.guided_work_started",
        actor_type=ActorType.HUMAN,
        actor_id=actor.id,
        mode="assisted",
        payload={
            "guided_work_session_id": str(session.id),
            "workflow_key": WORKFLOW_KEY,
            "guidance_version": GUIDANCE_VERSION,
        },
    )
    db.commit()
    db.refresh(session)
    return session, True


def complete_guided_work(
    db: Session,
    *,
    session_id: uuid.UUID,
    payload: GuidedWorkComplete,
    actor: User,
) -> GuidedWorkSession:
    session = db.scalar(
        select(GuidedWorkSession)
        .where(GuidedWorkSession.id == session_id)
        .with_for_update()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión guiada no encontrada")
    expected_steps = [step["key"] for step in session.checklist_snapshot]
    submitted_steps = payload.completed_step_keys
    if len(set(submitted_steps)) != len(submitted_steps) or set(submitted_steps) != set(
        expected_steps
    ):
        raise HTTPException(
            status_code=422,
            detail="Deben confirmarse exactamente todos los pasos de la guía",
        )
    minutes = Decimal(payload.human_minutes).quantize(Decimal("0.01"))
    note = payload.outcome_note.strip()
    if session.status == "completed":
        same_result = (
            session.completed_step_keys == submitted_steps
            and session.human_minutes == minutes
            and session.outcome == payload.outcome
            and session.outcome_note == note
        )
        if same_result:
            return session
        raise HTTPException(status_code=409, detail="La sesión ya fue completada")
    if session.status == "cancelled":
        raise HTTPException(status_code=409, detail="La sesión fue cancelada")

    completed_at = datetime.now(timezone.utc)  # noqa: UP017 - Python 3.10 tools
    entry = PilotLogEntry(
        client_id=session.client_id,
        related_invoice_id=session.invoice_id,
        entry_type="manual_work",
        severity="info",
        title="Revisión semanal de cartera guiada",
        detail=(
            "Sesión PM-2 completada con asistencia de lectura y registro; "
            f"resultado humano: {payload.outcome}."
        ),
        status="resolved",
        occurred_on=date.today(),
        human_minutes=minutes,
        human_minutes_measured=True,
        labor_accounting="additional",
        created_by=actor.id,
        resolved_by=actor.id,
        resolved_at=completed_at,
        resolution_note=note,
    )
    db.add(entry)
    db.flush()
    session.status = "completed"
    session.completed_step_keys = submitted_steps
    session.human_minutes = minutes
    session.outcome = payload.outcome
    session.outcome_note = note
    session.completed_by = actor.id
    session.completed_at = completed_at
    session.pilot_log_entry_id = entry.id
    record_event(
        db,
        client_id=session.client_id,
        invoice_id=session.invoice_id,
        event_type="optimization.guided_work_completed",
        actor_type=ActorType.HUMAN,
        actor_id=actor.id,
        mode="assisted",
        payload={
            "guided_work_session_id": str(session.id),
            "pilot_log_entry_id": str(entry.id),
            "workflow_key": session.workflow_key,
            "human_minutes": str(minutes),
            "baseline_minutes": str(session.baseline_minutes),
            "outcome": session.outcome,
            "external_action_executed": False,
        },
    )
    db.commit()
    db.refresh(session)
    return session


def cancel_guided_work(
    db: Session,
    *,
    session_id: uuid.UUID,
    reason: str,
    actor: User,
) -> GuidedWorkSession:
    session = db.scalar(
        select(GuidedWorkSession)
        .where(GuidedWorkSession.id == session_id)
        .with_for_update()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión guiada no encontrada")
    if session.status == "completed":
        raise HTTPException(status_code=409, detail="La sesión completada es inmutable")
    clean_reason = reason.strip()
    if session.status == "cancelled":
        if session.cancellation_reason == clean_reason:
            return session
        raise HTTPException(status_code=409, detail="La sesión ya fue cancelada")
    session.status = "cancelled"
    session.cancelled_by = actor.id
    session.cancelled_at = datetime.now(timezone.utc)  # noqa: UP017 - Python 3.10 tools
    session.cancellation_reason = clean_reason
    record_event(
        db,
        client_id=session.client_id,
        invoice_id=session.invoice_id,
        event_type="optimization.guided_work_cancelled",
        actor_type=ActorType.HUMAN,
        actor_id=actor.id,
        mode="assisted",
        payload={
            "guided_work_session_id": str(session.id),
            "workflow_key": session.workflow_key,
        },
    )
    db.commit()
    db.refresh(session)
    return session


def build_pm2_benchmark(
    sessions: list[GuidedWorkSession],
    events: list[Event],
) -> dict[str, Any]:
    completed = [session for session in sessions if session.status == "completed"]
    baseline_total = sum(
        (Decimal(session.baseline_minutes) for session in completed), Decimal(0)
    )
    optimized_total = sum(
        (Decimal(session.human_minutes or 0) for session in completed), Decimal(0)
    )
    reduction = (
        ((baseline_total - optimized_total) / baseline_total * Decimal(100))
        if baseline_total
        else Decimal(0)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    event_types_by_session: dict[str, set[str]] = {}
    for event in events:
        session_id = event.payload.get("guided_work_session_id")
        if session_id:
            event_types_by_session.setdefault(str(session_id), set()).add(event.event_type)
    traceability_complete = bool(completed) and all(
        session.pilot_log_entry_id is not None
        and session.completed_by is not None
        and session.completed_at is not None
        and {
            "optimization.guided_work_started",
            "optimization.guided_work_completed",
        }.issubset(event_types_by_session.get(str(session.id), set()))
        for session in completed
    )
    idempotency_duplicates = len(completed) - len(
        {session.idempotency_key for session in completed}
    )
    sample_complete = len(completed) >= MINIMUM_BENCHMARK_CASES
    target_met = reduction >= Decimal("20.00")
    passed = (
        sample_complete
        and target_met
        and idempotency_duplicates == 0
        and traceability_complete
    )
    average = (
        (optimized_total / len(completed)).quantize(Decimal("0.01"))
        if completed
        else None
    )
    report = {
        "schema_version": "pm-2-v1",
        "evidence_kind": "synthetic",
        "workflow": {
            "key": WORKFLOW_KEY,
            "title": "Revisión semanal de cartera guiada",
            "guidance_version": GUIDANCE_VERSION,
        },
        "sample": {
            "completed_cases": len(completed),
            "minimum_cases": MINIMUM_BENCHMARK_CASES,
        },
        "before": {
            "minutes_per_case": f"{BASELINE_MINUTES_PER_CASE:.2f}",
            "total_human_minutes": f"{baseline_total:.2f}",
        },
        "after": {
            "average_minutes_per_case": f"{average:.2f}" if average is not None else None,
            "total_human_minutes": f"{optimized_total:.2f}",
        },
        "reduction_percent": f"{reduction:.2f}",
        "safety": {
            "idempotency_duplicates": idempotency_duplicates,
            "reopenings": 0,
            "traceability_complete": traceability_complete,
            "external_actions_executed": 0,
        },
        "pm_g2": {
            "status": "passed_synthetic" if passed else "needs_evidence",
            "local_phase_complete": passed,
            "pm3_authorized": False,
            "sample_complete": sample_complete,
            "reduction_target_met": target_met,
            "reason": (
                "El benchmark sintético cumple reducción, idempotencia y trazabilidad; "
                "requiere evidencia real antes de autorizar PM-3."
                if passed
                else "La muestra sintética todavía no cumple todos los criterios de PM-G2."
            ),
        },
    }
    fingerprint_source = json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        **report,
        "fingerprint_sha256": hashlib.sha256(fingerprint_source).hexdigest(),
    }


def pm2_benchmark_markdown(report: dict[str, Any]) -> bytes:
    return "\n".join(
        [
            "# PM-2 — Benchmark de revisión semanal guiada",
            "",
            f"Tipo de evidencia: {report['evidence_kind']}",
            f"Esquema: {report['schema_version']}",
            f"Huella SHA-256: `{report['fingerprint_sha256']}`",
            "",
            "> La evidencia sintética cierra PM-2 localmente, pero no demuestra impacto real ni autoriza PM-3 productiva.",
            "",
            "## Comparación",
            "",
            "| Métrica | Antes | Después |",
            "|---|---:|---:|",
            (
                "| Casos completados | "
                f"{report['sample']['completed_cases']} | {report['sample']['completed_cases']} |"
            ),
            (
                "| Minutos por caso | "
                f"{report['before']['minutes_per_case']} | "
                f"{report['after']['average_minutes_per_case']} |"
            ),
            (
                "| Minutos totales | "
                f"{report['before']['total_human_minutes']} | "
                f"{report['after']['total_human_minutes']} |"
            ),
            "",
            f"Reducción observada: **{report['reduction_percent']}%**.",
            "",
            "## Seguridad",
            "",
            f"- Duplicados idempotentes: {report['safety']['idempotency_duplicates']}.",
            f"- Reaperturas: {report['safety']['reopenings']}.",
            f"- Trazabilidad completa: {str(report['safety']['traceability_complete']).lower()}.",
            f"- Acciones externas ejecutadas: {report['safety']['external_actions_executed']}.",
            "",
            "## Puerta PM-G2",
            "",
            f"Estado local: **{report['pm_g2']['status']}**.",
            "",
            report["pm_g2"]["reason"],
            "",
        ]
    ).encode("utf-8")


def benchmark_for_sessions(
    db: Session, *, client_id: uuid.UUID | None = None
) -> dict[str, Any]:
    query = select(GuidedWorkSession)
    if client_id is not None:
        query = query.where(GuidedWorkSession.client_id == client_id)
    sessions = list(db.scalars(query.order_by(GuidedWorkSession.created_at)))
    client_ids = {session.client_id for session in sessions}
    if not client_ids:
        return build_pm2_benchmark([], [])
    events = list(
        db.scalars(
            select(Event).where(
                Event.client_id.in_(client_ids),
                Event.event_type.in_(
                    [
                        "optimization.guided_work_started",
                        "optimization.guided_work_completed",
                    ]
                ),
            )
        )
    )
    return build_pm2_benchmark(sessions, events)
