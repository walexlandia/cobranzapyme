import csv
import hashlib
import io
import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Client,
    Contract,
    Event,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    PilotAuthorizationEvent,
    PilotLogEntry,
    ReconciliationProposal,
)

REPORT_SCHEMA_VERSION = "pm-1-v2"
MIN_CASES_FOR_SELECTION = 3
MIN_MEASUREMENT_COVERAGE_PERCENT = Decimal("80")
MIN_MATERIAL_SHARE_PERCENT = Decimal("20")
PM2_REDUCTION_TARGET_PERCENT = Decimal("20")
KNOWN_EXCEPTION_KINDS = {
    "correlation_review",
    "low_confidence",
    "mandatory_review",
    "supervised_review",
}
KNOWN_EXCEPTION_DECISIONS = {"confirmed", "corrected", "not_recorded"}
KNOWN_EXCEPTION_RESULTS = {
    "paid",
    "payment_scheduled",
    "missing_oc_hes",
    "supplier_data_issue",
    "invoice_disputed",
    "payment_promise",
    "dispute",
    "document_request",
    "wrong_contact",
    "other",
    "open",
    "resolved",
}


def _decimal(value: Decimal | int | float | str, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _percent(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    if not denominator:
        return None
    return _decimal(Decimal(numerator) * Decimal("100") / Decimal(denominator))


def _hours_between(start: datetime, end: datetime) -> Decimal:
    seconds = max((end - start).total_seconds(), 0)
    return _decimal(Decimal(str(seconds)) / Decimal("3600"))


def _average(values: list[Decimal]) -> Decimal | None:
    return _decimal(sum(values, Decimal("0")) / len(values)) if values else None


def _median(values: list[Decimal]) -> Decimal | None:
    return _decimal(Decimal(median(values))) if values else None


def _display(value: Any, fallback: str = "—") -> Any:
    return fallback if value is None else value


def _safe_category(value: str, allowed: set[str]) -> str:
    return value if value in allowed else "other"


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"No se puede serializar {type(value)!r}")


def human_effort_report_json(report: dict[str, Any], *, indent: int | None = 2) -> str:
    return json.dumps(
        report,
        default=_json_default,
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )


def _workstream_row(
    *,
    key: str,
    source: str,
    category: str,
    cases: list[ExceptionCase] | list[PilotLogEntry],
    date_to_at: datetime,
    all_minutes: Decimal,
) -> dict[str, Any]:
    measured_minutes = [
        Decimal(item.human_minutes or 0)
        for item in cases
        if item.human_minutes_measured
    ]
    total_minutes = sum(measured_minutes, Decimal("0"))
    client_counts = Counter(item.client_id for item in cases)
    invoice_ids = {
        item.invoice_id if source == "exception" else item.related_invoice_id
        for item in cases
        if (item.invoice_id if source == "exception" else item.related_invoice_id)
        is not None
    }
    durations: list[Decimal] = []
    open_ages: list[Decimal] = []
    status_counts = Counter(item.status for item in cases)
    if source == "exception":
        for item in cases:
            if item.resolved_at is not None:
                durations.append(_hours_between(item.created_at, item.resolved_at))
            elif item.status == "open":
                open_ages.append(_hours_between(item.created_at, date_to_at))
    else:
        for item in cases:
            if item.resolved_at is not None:
                durations.append(_hours_between(item.created_at, item.resolved_at))
            elif item.status == "open":
                open_ages.append(_hours_between(item.created_at, date_to_at))
    return {
        "key": key,
        "source": source,
        "category": category,
        "case_count": len(cases),
        "measured_case_count": len(measured_minutes),
        "measurement_coverage_percent": _percent(len(measured_minutes), len(cases)),
        "total_human_minutes": _decimal(total_minutes),
        "average_minutes_per_case": _decimal(total_minutes / len(cases))
        if cases
        else None,
        "median_minutes_per_measured_case": _median(measured_minutes),
        "human_minutes_share_percent": _percent(total_minutes, all_minutes),
        "open_cases": status_counts.get("open", 0),
        "resolved_cases": status_counts.get("resolved", 0),
        "average_resolution_hours": _average(durations),
        "oldest_open_hours": max(open_ages) if open_ages else None,
        "distinct_invoices": len(invoice_ids),
        "repeat_cases_on_same_invoice": sum(
            count - 1
            for invoice_id, count in Counter(
                item.invoice_id if source == "exception" else item.related_invoice_id
                for item in cases
            ).items()
            if invoice_id is not None and count > 1
        ),
        "client_concentration_percent": _percent(
            max(client_counts.values()), len(cases)
        ),
        "selection_eligible": (
            len(cases) >= MIN_CASES_FOR_SELECTION
            and _percent(len(measured_minutes), len(cases)) is not None
            and _percent(len(measured_minutes), len(cases))
            >= MIN_MEASUREMENT_COVERAGE_PERCENT
            and total_minutes > 0
        ),
    }


def build_human_effort_diagnostic(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    evidence_kind: Literal["synthetic", "authorized_pilot"] = "synthetic",
) -> dict[str, Any]:
    if date_to < date_from:
        raise ValueError("date_to no puede ser anterior a date_from")
    if (date_to - date_from).days > 365:
        raise ValueError("El rango máximo es de 366 días")
    if evidence_kind not in {"synthetic", "authorized_pilot"}:
        raise ValueError("Tipo de evidencia inválido")

    start_at = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    active_client_ids = list(
        db.scalars(select(Client.id).where(Client.active.is_(True)))
    )

    exceptions: list[ExceptionCase] = []
    log_entries: list[PilotLogEntry] = []
    proposals: list[ReconciliationProposal] = []
    managed_invoice_ids: set[uuid.UUID] = set()
    messages: list[Message] = []
    classifications: list[MessageClassification] = []
    if active_client_ids:
        exceptions = list(
            db.scalars(
                select(ExceptionCase).where(
                    ExceptionCase.client_id.in_(active_client_ids),
                    ExceptionCase.created_at >= start_at,
                    ExceptionCase.created_at <= end_at,
                )
            )
        )
        log_entries = list(
            db.scalars(
                select(PilotLogEntry).where(
                    PilotLogEntry.client_id.in_(active_client_ids),
                    PilotLogEntry.occurred_on >= date_from,
                    PilotLogEntry.occurred_on <= date_to,
                )
            )
        )
        proposals = list(
            db.scalars(
                select(ReconciliationProposal).where(
                    ReconciliationProposal.client_id.in_(active_client_ids),
                    ReconciliationProposal.created_at >= start_at,
                    ReconciliationProposal.created_at <= end_at,
                )
            )
        )
        managed_invoice_ids.update(
            db.scalars(
                select(Invoice.id).where(
                    Invoice.client_id.in_(active_client_ids),
                    Invoice.issued_on >= date_from,
                    Invoice.issued_on <= date_to,
                )
            )
        )
        managed_invoice_ids.update(
            invoice_id
            for invoice_id in db.scalars(
                select(Event.invoice_id).where(
                    Event.client_id.in_(active_client_ids),
                    Event.invoice_id.is_not(None),
                    Event.created_at >= start_at,
                    Event.created_at <= end_at,
                )
            )
            if invoice_id is not None
        )
        messages = list(
            db.scalars(
                select(Message).where(
                    Message.client_id.in_(active_client_ids),
                    Message.direction == "outbound",
                    Message.created_at >= start_at,
                    Message.created_at <= end_at,
                    Message.mode.in_(["automatic", "manual"]),
                )
            )
        )
        classifications = list(
            db.scalars(
                select(MessageClassification).where(
                    MessageClassification.client_id.in_(active_client_ids),
                    MessageClassification.created_at >= start_at,
                    MessageClassification.created_at <= end_at,
                )
            )
        )

    managed_invoice_ids.update(
        item.invoice_id for item in exceptions if item.invoice_id is not None
    )
    managed_invoice_ids.update(
        item.related_invoice_id
        for item in log_entries
        if item.related_invoice_id is not None
    )

    measured_exceptions = [item for item in exceptions if item.human_minutes_measured]
    countable_log_entries = [
        item
        for item in log_entries
        if item.human_minutes_measured and item.labor_accounting == "additional"
    ]
    exception_minutes = sum(
        (Decimal(item.human_minutes or 0) for item in measured_exceptions), Decimal("0")
    )
    log_minutes = sum(
        (Decimal(item.human_minutes or 0) for item in countable_log_entries), Decimal("0")
    )
    decided_proposals = [
        item
        for item in proposals
        if item.status in {"confirmed", "rejected"} and item.reviewed_at is not None
    ]
    measured_proposals = [
        item for item in decided_proposals if item.human_minutes is not None
    ]
    reconciliation_minutes = sum(
        (Decimal(item.human_minutes or 0) for item in measured_proposals), Decimal("0")
    )
    total_minutes = exception_minutes + log_minutes + reconciliation_minutes

    exception_groups: dict[str, list[ExceptionCase]] = defaultdict(list)
    for item in exceptions:
        exception_groups[_safe_category(item.kind, KNOWN_EXCEPTION_KINDS)].append(item)
    log_groups: dict[str, list[PilotLogEntry]] = defaultdict(list)
    for item in countable_log_entries:
        log_groups[item.entry_type].append(item)

    ranking = [
        _workstream_row(
            key=f"exception:{category}",
            source="exception",
            category=category,
            cases=cases,
            date_to_at=end_at,
            all_minutes=total_minutes,
        )
        for category, cases in exception_groups.items()
    ]
    ranking.extend(
        _workstream_row(
            key=f"pilot_log:{category}",
            source="pilot_log",
            category=category,
            cases=cases,
            date_to_at=end_at,
            all_minutes=total_minutes,
        )
        for category, cases in log_groups.items()
    )
    reconciliation_cycles = [
        _hours_between(item.created_at, item.reviewed_at)
        for item in decided_proposals
        if item.reviewed_at is not None
    ]
    if proposals:
        proposal_client_counts = Counter(item.client_id for item in proposals)
        pending_ages = [
            _hours_between(item.created_at, end_at)
            for item in proposals
            if item.status == "pending"
        ]
        reconciliation_coverage = _percent(
            len(measured_proposals), len(decided_proposals)
        )
        ranking.append(
            {
                "key": "reconciliation:review",
                "source": "reconciliation",
                "category": "review",
                "case_count": len(proposals),
                "measured_case_count": len(measured_proposals),
                "measurement_coverage_percent": reconciliation_coverage,
                "total_human_minutes": _decimal(reconciliation_minutes),
                "average_minutes_per_case": (
                    _decimal(reconciliation_minutes / len(measured_proposals))
                    if measured_proposals
                    else None
                ),
                "median_minutes_per_measured_case": _median(
                    [Decimal(item.human_minutes or 0) for item in measured_proposals]
                ),
                "human_minutes_share_percent": _percent(
                    reconciliation_minutes, total_minutes
                ),
                "open_cases": sum(item.status == "pending" for item in proposals),
                "resolved_cases": len(decided_proposals),
                "average_resolution_hours": _average(reconciliation_cycles),
                "oldest_open_hours": max(pending_ages) if pending_ages else None,
                "distinct_invoices": None,
                "repeat_cases_on_same_invoice": None,
                "client_concentration_percent": _percent(
                    max(proposal_client_counts.values()), len(proposals)
                ),
                "selection_eligible": (
                    len(decided_proposals) >= MIN_CASES_FOR_SELECTION
                    and reconciliation_coverage is not None
                    and reconciliation_coverage >= MIN_MEASUREMENT_COVERAGE_PERCENT
                    and reconciliation_minutes > 0
                ),
            }
        )
    ranking.sort(
        key=lambda item: (
            -Decimal(item["total_human_minutes"]),
            -item["case_count"],
            item["key"],
        )
    )
    for rank, item in enumerate(ranking, start=1):
        item["rank"] = rank

    reconciliation_status = Counter(item.status for item in proposals)

    automatic_actions = (
        sum(item.mode == "automatic" for item in messages)
        + sum(item.decision_source == "system" for item in classifications)
        + len(proposals)
    )
    manual_actions = (
        sum(item.mode == "manual" for item in messages)
        + sum(item.decision_source == "human" for item in classifications)
        + len(decided_proposals)
        + len(log_entries)
    )

    decision_counts = Counter(
        _safe_category(
            str((item.resolution or {}).get("decision") or "not_recorded"),
            KNOWN_EXCEPTION_DECISIONS,
        )
        for item in exceptions
    )
    result_counts = Counter(
        _safe_category(
            str((item.resolution or {}).get("category") or item.status),
            KNOWN_EXCEPTION_RESULTS,
        )
        for item in exceptions
    )
    severity_counts = Counter(item.severity for item in log_entries)
    log_status_counts = Counter(item.status for item in log_entries)

    selected = next(
        (
            item
            for item in ranking
            if item["selection_eligible"]
            and Decimal(item["human_minutes_share_percent"] or 0)
            >= MIN_MATERIAL_SHARE_PERCENT
        ),
        None,
    )
    selected_client_ids: set[uuid.UUID] = set()
    if selected is not None:
        if selected["source"] == "exception":
            selected_client_ids = {
                item.client_id for item in exception_groups[selected["category"]]
            }
        elif selected["source"] == "pilot_log":
            selected_client_ids = {
                item.client_id for item in log_groups[selected["category"]]
            }
        else:
            selected_client_ids = {item.client_id for item in measured_proposals}
    active_contracts = (
        {
            item.client_id: item.id
            for item in db.scalars(
                select(Contract).where(
                    Contract.client_id.in_(selected_client_ids),
                    Contract.active.is_(True),
                )
            )
        }
        if selected_client_ids
        else {}
    )
    latest_authorization: dict[uuid.UUID, PilotAuthorizationEvent] = {}
    if selected_client_ids:
        for event in db.scalars(
            select(PilotAuthorizationEvent)
            .where(PilotAuthorizationEvent.client_id.in_(selected_client_ids))
            .order_by(PilotAuthorizationEvent.created_at, PilotAuthorizationEvent.id)
        ):
            latest_authorization[event.client_id] = event
    authorized_client_ids = {
        client_id
        for client_id in selected_client_ids
        if (authorization := latest_authorization.get(client_id)) is not None
        and authorization.action == "approved"
        and authorization.evidence_document_id is not None
        and authorization.contract_id == active_contracts.get(client_id)
        and authorization.valid_from <= date_from
        and (authorization.valid_until is None or authorization.valid_until >= date_to)
    }
    authorization_complete = bool(selected_client_ids) and (
        authorized_client_ids == selected_client_ids
    )
    analytical_ready = selected is not None
    selection_measurement_blockers: list[str] = []
    if (
        selected is not None
        and Decimal(selected["measurement_coverage_percent"] or 0) < Decimal("100")
    ):
        selection_measurement_blockers.append("incomplete_selected_measurement")
    if not analytical_ready:
        gate_status = "needs_measurement"
        gate_reason = (
            "Ningún flujo reúne volumen, cobertura y participación material suficientes; "
            "se debe mejorar la medición antes de diseñar PM-2."
        )
    elif evidence_kind == "synthetic":
        gate_status = "provisional_synthetic"
        gate_reason = (
            "La medición distingue una oportunidad, pero la evidencia sintética no aprueba "
            "PM-G1 ni autoriza cambios operativos de PM-2."
        )
    elif selection_measurement_blockers:
        gate_status = "measurement_gaps"
        gate_reason = (
            "La oportunidad parece material, pero todavía contiene casos sin medición "
            "confirmada. Se debe completar la muestra antes de PM-2."
        )
    elif not authorization_complete:
        gate_status = "authorization_incomplete"
        gate_reason = (
            "La oportunidad es material, pero la evidencia declarada no tiene autorización "
            "vigente y comprobante para todos los clientes que la sustentan."
        )
    else:
        gate_status = "approved"
        gate_reason = (
            "La evidencia autorizada distingue un flujo material con cobertura suficiente; "
            "PM-2 puede limitarse a esta oportunidad."
        )

    opportunity = None
    if selected is not None:
        baseline_minutes = Decimal(selected["total_human_minutes"])
        baseline_average = Decimal(selected["average_minutes_per_case"] or 0)
        opportunity = {
            "friction_key": selected["key"],
            "rank": selected["rank"],
            "problem": (
                f"El flujo {selected['key']} concentra "
                f"{selected['human_minutes_share_percent']}% de los minutos medidos."
            ),
            "baseline": {
                "case_count": selected["case_count"],
                "total_human_minutes": selected["total_human_minutes"],
                "average_minutes_per_case": selected["average_minutes_per_case"],
                "measurement_coverage_percent": selected[
                    "measurement_coverage_percent"
                ],
            },
            "pm2_target": {
                "reduction_percent": PM2_REDUCTION_TARGET_PERCENT,
                "maximum_total_human_minutes": _decimal(
                    baseline_minutes
                    * (Decimal("1") - PM2_REDUCTION_TARGET_PERCENT / 100)
                ),
                "maximum_average_minutes_per_case": _decimal(
                    baseline_average
                    * (Decimal("1") - PM2_REDUCTION_TARGET_PERCENT / 100)
                ),
                "guardrails": [
                    "cero acciones duplicadas",
                    "trazabilidad completa",
                    "sin aumentar errores ni reaperturas",
                ],
            },
        }

    if not decided_proposals:
        reconciliation_measurement_status = "not_applicable"
    elif measured_proposals and len(measured_proposals) == len(decided_proposals):
        reconciliation_measurement_status = "available"
    elif measured_proposals:
        reconciliation_measurement_status = "partial"
    else:
        reconciliation_measurement_status = "unavailable"
    measurement_gaps: list[dict[str, str]] = []
    unmeasured_exception_count = len(exceptions) - len(measured_exceptions)
    unmeasured_log_count = sum(not item.human_minutes_measured for item in log_entries)
    unclassified_log_count = sum(
        item.labor_accounting is None for item in log_entries if item.human_minutes_measured
    )
    if unmeasured_exception_count or unmeasured_log_count:
        measurement_gaps.append(
            {
                "key": "unmeasured_human_minutes",
                "impact": (
                    f"Hay {unmeasured_exception_count} excepciones y {unmeasured_log_count} "
                    "registros de bitácora heredados sin confirmación de medición."
                ),
                "required_measurement": (
                    "Excluirlos de la línea base o completar una medición verificable."
                ),
            }
        )
    if unclassified_log_count:
        measurement_gaps.append(
            {
                "key": "unclassified_labor_accounting",
                "impact": (
                    f"Hay {unclassified_log_count} registros medidos sin clasificación "
                    "de contabilización."
                ),
                "required_measurement": (
                    "Marcar cada registro como trabajo adicional o incluido en una excepción."
                ),
            }
        )
    if reconciliation_measurement_status in {"partial", "unavailable"}:
        measurement_gaps.append(
            {
                "key": "reconciliation_labor_minutes",
                "impact": (
                    "La muestra todavía no permite comparar completamente el costo humano "
                    "de conciliación con otros flujos."
                ),
                "required_measurement": (
                    "Registrar minutos de revisión al decidir cada propuesta nueva."
                ),
            },
        )

    stable_payload: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "date_from": date_from,
        "date_to": date_to,
        "period_days": (date_to - date_from).days + 1,
        "evidence_kind": evidence_kind,
        "scope": {
            "active_clients": len(active_client_ids),
            "managed_invoices": len(managed_invoice_ids),
            "exception_cases": len(exceptions),
            "pilot_log_entries": len(log_entries),
            "countable_pilot_log_entries": len(countable_log_entries),
            "reconciliation_proposals": len(proposals),
        },
        "baseline": {
            "total_human_minutes": _decimal(total_minutes),
            "minutes_per_managed_invoice": (
                _decimal(total_minutes / len(managed_invoice_ids))
                if managed_invoice_ids
                else None
            ),
            "exception_human_minutes": _decimal(exception_minutes),
            "pilot_log_human_minutes": _decimal(log_minutes),
            "reconciliation_human_minutes": _decimal(reconciliation_minutes),
            "manual_action_count": manual_actions,
            "automatic_action_count": automatic_actions,
            "manual_action_percent": _percent(
                manual_actions, manual_actions + automatic_actions
            ),
            "manual_action_scope": (
                "Mensajes manuales, clasificaciones humanas, decisiones de conciliación "
                "y entradas de bitácora frente a sus equivalentes automáticos observados."
            ),
            "reopenings": 0,
            "reopening_measurement_status": "not_applicable",
            "reopening_policy": (
                "Los casos resueltos son inmutables; una recurrencia crea un caso nuevo."
            ),
        },
        "breakdowns": {
            "exception_decisions": dict(sorted(decision_counts.items())),
            "exception_results": dict(sorted(result_counts.items())),
            "pilot_log_status": dict(sorted(log_status_counts.items())),
            "pilot_log_severity": dict(sorted(severity_counts.items())),
        },
        "friction_ranking": ranking,
        "reconciliation": {
            "proposal_count": len(proposals),
            "decision_count": len(decided_proposals),
            "status_counts": dict(sorted(reconciliation_status.items())),
            "average_decision_cycle_hours": _average(reconciliation_cycles),
            "median_decision_cycle_hours": _median(reconciliation_cycles),
            "measured_decision_count": len(measured_proposals),
            "measurement_coverage_percent": _percent(
                len(measured_proposals), len(decided_proposals)
            ),
            "human_minutes": (
                _decimal(reconciliation_minutes) if measured_proposals else None
            ),
            "labor_measurement_status": reconciliation_measurement_status,
            "note": (
                "El ciclo entre creación y revisión mide espera más trabajo; no se interpreta "
                "como minutos humanos."
            ),
        },
        "measurement_gaps": measurement_gaps,
        "selected_opportunity": opportunity,
        "pm_g1": {
            "status": gate_status,
            "analytical_ready": analytical_ready,
            "pm2_authorized": gate_status == "approved",
            "reason": gate_reason,
            "thresholds": {
                "minimum_cases": MIN_CASES_FOR_SELECTION,
                "minimum_measurement_coverage_percent": MIN_MEASUREMENT_COVERAGE_PERCENT,
                "minimum_human_minutes_share_percent": MIN_MATERIAL_SHARE_PERCENT,
            },
            "authorization_coverage": {
                "participating_clients": len(selected_client_ids),
                "authorized_clients": len(authorized_client_ids),
                "complete": authorization_complete,
            },
            "selection_measurement_blockers": selection_measurement_blockers,
            "measurement_complete": not measurement_gaps,
        },
        "privacy": {
            "aggregate_only": True,
            "excluded_fields": [
                "client identifiers",
                "names",
                "RUT",
                "invoice folios",
                "message bodies",
                "free-text notes",
            ],
        },
    }
    fingerprint_source = human_effort_report_json(stable_payload, indent=None).encode(
        "utf-8"
    )
    return {
        **stable_payload,
        "fingerprint_sha256": hashlib.sha256(fingerprint_source).hexdigest(),
    }


def human_effort_dataset_csv(report: dict[str, Any]) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "schema_version",
            "date_from",
            "date_to",
            "rank",
            "source",
            "category",
            "case_count",
            "measured_case_count",
            "measurement_coverage_percent",
            "total_human_minutes",
            "average_minutes_per_case",
            "human_minutes_share_percent",
            "open_cases",
            "resolved_cases",
            "average_resolution_hours",
            "oldest_open_hours",
            "distinct_invoices",
            "repeat_cases_on_same_invoice",
            "client_concentration_percent",
            "selection_eligible",
        ]
    )
    for row in report["friction_ranking"]:
        writer.writerow(
            [
                report["schema_version"],
                report["date_from"],
                report["date_to"],
                row["rank"],
                row["source"],
                row["category"],
                row["case_count"],
                row["measured_case_count"],
                _display(row["measurement_coverage_percent"], ""),
                row["total_human_minutes"],
                _display(row["average_minutes_per_case"], ""),
                _display(row["human_minutes_share_percent"], ""),
                row["open_cases"],
                row["resolved_cases"],
                _display(row["average_resolution_hours"], ""),
                _display(row["oldest_open_hours"], ""),
                row["distinct_invoices"],
                row["repeat_cases_on_same_invoice"],
                _display(row["client_concentration_percent"], ""),
                row["selection_eligible"],
            ]
        )
    return stream.getvalue().encode("utf-8-sig")


def human_effort_markdown(report: dict[str, Any]) -> bytes:
    lines = [
        "# PM-1 — Diagnóstico del costo humano",
        "",
        f"Período: {report['date_from']} a {report['date_to']} ({report['period_days']} días)",
        f"Tipo de evidencia: {report['evidence_kind']}",
        f"Esquema: {report['schema_version']}",
        f"Huella reproducible SHA-256: `{report['fingerprint_sha256']}`",
        "",
        (
            "> Evidencia sintética: permite verificar el instrumento, pero no aprueba PM-G1."
            if report["evidence_kind"] == "synthetic"
            else "> Evidencia declarada como piloto autorizado; requiere revisión humana del gate."
        ),
        "",
        "## Línea base",
        "",
        f"- Minutos humanos medidos: {report['baseline']['total_human_minutes']}",
        f"- Minutos por factura gestionada: {_display(report['baseline']['minutes_per_managed_invoice'], 'sin denominador')}",
        f"- Minutos en excepciones: {report['baseline']['exception_human_minutes']}",
        f"- Minutos en bitácora: {report['baseline']['pilot_log_human_minutes']}",
        f"- Minutos en conciliación: {report['baseline']['reconciliation_human_minutes']}",
        f"- Porcentaje de acciones manuales observadas: {_display(report['baseline']['manual_action_percent'], 'sin muestra')}%",
        (
            f"- Reaperturas: {report['baseline']['reopenings']} "
            f"({report['baseline']['reopening_measurement_status']}; "
            "los casos resueltos son inmutables)."
        ),
        "",
        "## Ranking de fricciones",
        "",
        "| # | Flujo | Casos | Cobertura | Minutos | Participación | Abiertos | Elegible |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in report["friction_ranking"]:
        lines.append(
            f"| {item['rank']} | `{item['key']}` | {item['case_count']} | "
            f"{_display(item['measurement_coverage_percent'])}% | {item['total_human_minutes']} | "
            f"{_display(item['human_minutes_share_percent'])}% | {item['open_cases']} | "
            f"{'sí' if item['selection_eligible'] else 'no'} |"
        )
    if not report["friction_ranking"]:
        lines.append("| — | Sin datos | 0 | — | 0 | — | 0 | no |")

    lines.extend(
        [
            "",
            "## Conciliación",
            "",
            f"- Propuestas: {report['reconciliation']['proposal_count']}",
            f"- Decisiones: {report['reconciliation']['decision_count']}",
            f"- Ciclo medio de decisión: {_display(report['reconciliation']['average_decision_cycle_hours'], 'sin muestra')} horas",
            (
                "- Minutos humanos medidos: "
                f"{_display(report['reconciliation']['human_minutes'], 'sin muestra')}. "
                "El tiempo de ciclo no se usa como sustituto."
            ),
            "",
            "## Oportunidad y puerta PM-G1",
            "",
            f"Estado: **{report['pm_g1']['status']}**.",
            "",
            report["pm_g1"]["reason"],
        ]
    )
    opportunity = report["selected_opportunity"]
    if opportunity is not None:
        lines.extend(
            [
                "",
                f"Oportunidad única: `{opportunity['friction_key']}`.",
                "",
                opportunity["problem"],
                (
                    f"Objetivo PM-2 condicionado: reducir {opportunity['pm2_target']['reduction_percent']}% "
                    f"hasta un máximo de {opportunity['pm2_target']['maximum_total_human_minutes']} "
                    "minutos totales en una muestra comparable."
                ),
            ]
        )
    lines.extend(["", "## Brechas de medición", ""])
    if report["measurement_gaps"]:
        for gap in report["measurement_gaps"]:
            lines.append(f"- `{gap['key']}`: {gap['impact']} {gap['required_measurement']}")
    else:
        lines.append("- Sin brechas internas en la muestra analizada.")
    lines.extend(
        [
            "",
            "## Privacidad",
            "",
            "El reporte y el CSV son agregados. No contienen nombres, RUT, folios, UUID, mensajes ni notas libres.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")
