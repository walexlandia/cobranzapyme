import csv
import hashlib
import hmac
import io
import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BankTransaction,
    Client,
    Contract,
    DelayCause,
    Document,
    Event,
    Invoice,
    Payment,
    PaymentAttribution,
    PilotAuthorizationEvent,
)
from app.services.final_report import amount_band

REPORT_SCHEMA_VERSION = "pm-3-v1"
MINIMUM_INCLUDED_PAYMENTS = 3
MANAGEMENT_EVENT_PREFIXES = (
    "payability.",
    "workflow.",
    "message.",
    "communication.",
    "exception.",
    "optimization.",
)
EXCLUSION_LABELS = {
    "missing_client_baseline": "La pyme no tiene línea base completa.",
    "unsupported_currency": "La factura no está expresada en CLP.",
    "verification_metadata_missing": "El pago no conserva responsable y fecha de verificación.",
    "payment_evidence_missing": "El pago no conserva comprobante cifrado ni movimiento bancario.",
    "attribution_missing": "El pago verificado no tiene atribución congelada.",
    "attribution_mismatch": "La atribución no coincide con pago, factura, pyme o monto.",
    "contract_missing": "La atribución no conserva un contrato válido de la pyme.",
    "contract_rule_missing": "La atribución no conserva regla y versión contractual.",
    "management_evidence_missing": "No existe evidencia de gestión previa elegible.",
    "management_evidence_invalid": "La evidencia de gestión no pertenece a la cadena observada.",
}


def _decimal(value: Decimal | int | str, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _percent(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    if not denominator:
        return None
    return _decimal(Decimal(numerator) * 100 / Decimal(denominator))


def _alias(namespace: str, value: str, key: str) -> str:
    digest = hmac.new(
        key.encode("utf-8"),
        f"pm3:{namespace}:{value}".encode(),
        hashlib.sha256,
    ).hexdigest()[:10].upper()
    prefix = "PYME" if namespace == "client" else "PAGADOR"
    return f"{prefix}-{digest}"


def _cohort_rows(
    included: list[dict[str, Any]],
    *,
    minimum_group_size: int,
    anonymization_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in included:
        dimensions = {
            "client": _alias("client", case["client_key"], anonymization_key),
            "payer": _alias("payer", case["payer_key"], anonymization_key),
            "industry": case["industry"] or "unclassified",
            "amount_band": case["amount_band"],
            "cause": case["cause"] or "unclassified",
        }
        for dimension, segment in dimensions.items():
            groups[(dimension, segment)].append(case)

    published: list[dict[str, Any]] = []
    suppressed: dict[str, dict[str, Any]] = {}
    for (dimension, segment), rows in sorted(groups.items()):
        if len(rows) < minimum_group_size:
            summary = suppressed.setdefault(
                dimension,
                {"dimension": dimension, "groups": 0, "payment_count": 0},
            )
            summary["groups"] += 1
            summary["payment_count"] += len(rows)
            continue
        amount = sum((case["amount"] for case in rows), Decimal(0))
        on_time = sum(1 for case in rows if case["on_time"])
        baseline_on_time = sum(
            (case["baseline_on_time_percent"] for case in rows), Decimal(0)
        ) / len(rows)
        observed_on_time = Decimal(on_time) * 100 / len(rows)
        categories = Counter(case["attribution_category"] for case in rows)
        published.append(
            {
                "dimension": dimension,
                "segment": segment,
                "payment_count": len(rows),
                "invoice_count": len({case["invoice_key"] for case in rows}),
                "verified_amount_clp": f"{_decimal(amount):.2f}",
                "baseline_on_time_percent": f"{_decimal(baseline_on_time):.2f}",
                "observed_on_time_percent": f"{_decimal(observed_on_time):.2f}",
                "on_time_delta_points": f"{_decimal(observed_on_time - baseline_on_time):.2f}",
                "attribution_categories": dict(sorted(categories.items())),
            }
        )
    return published, list(suppressed.values())


def _concentrations(
    included: list[dict[str, Any]], *, anonymization_key: str
) -> list[dict[str, Any]]:
    total = sum((case["amount"] for case in included), Decimal(0))
    dimensions: dict[str, dict[str, Decimal]] = {
        "client": defaultdict(Decimal),
        "payer": defaultdict(Decimal),
        "industry": defaultdict(Decimal),
        "amount_band": defaultdict(Decimal),
        "cause": defaultdict(Decimal),
    }
    for case in included:
        values = {
            "client": _alias("client", case["client_key"], anonymization_key),
            "payer": _alias("payer", case["payer_key"], anonymization_key),
            "industry": case["industry"] or "unclassified",
            "amount_band": case["amount_band"],
            "cause": case["cause"] or "unclassified",
        }
        for dimension, segment in values.items():
            dimensions[dimension][segment] += case["amount"]
    results = []
    for dimension, segments in dimensions.items():
        if not segments:
            results.append(
                {"dimension": dimension, "top_segment": None, "share_percent": None}
            )
            continue
        top_segment, top_amount = max(segments.items(), key=lambda item: (item[1], item[0]))
        share = _percent(top_amount, total)
        results.append(
            {
                "dimension": dimension,
                "top_segment": top_segment,
                "share_percent": f"{share:.2f}" if share is not None else None,
            }
        )
    return results


def compile_comparables_report(
    cases: list[dict[str, Any]],
    *,
    date_from: date,
    date_to: date,
    minimum_group_size: int,
    evidence_kind: Literal["synthetic", "authorized_pilot"],
    anonymization_key: str,
    authorization_complete: bool = False,
) -> dict[str, Any]:
    included = [case for case in cases if case["exclusion_reason"] is None]
    excluded = [case for case in cases if case["exclusion_reason"] is not None]
    exclusion_counts = Counter(case["exclusion_reason"] for case in excluded)
    exclusion_amounts: dict[str, Decimal] = defaultdict(Decimal)
    for case in excluded:
        exclusion_amounts[case["exclusion_reason"]] += case["amount"]
    exclusions = [
        {
            "reason": reason,
            "description": EXCLUSION_LABELS[reason],
            "payment_count": count,
            "verified_amount_clp": f"{_decimal(exclusion_amounts[reason]):.2f}",
        }
        for reason, count in sorted(exclusion_counts.items())
    ]
    cohorts, suppressed = _cohort_rows(
        included,
        minimum_group_size=minimum_group_size,
        anonymization_key=anonymization_key,
    )
    concentrations = _concentrations(
        included, anonymization_key=anonymization_key
    )
    unique_payment_count = len({case["payment_key"] for case in included})
    duplicate_count = len(included) - unique_payment_count
    included_client_keys = {case["client_key"] for case in included}
    baseline_complete = all(
        case["baseline_dso"] is not None
        and case["baseline_on_time_percent"] is not None
        for case in included
    )
    chain_complete = bool(included) and all(case["chain_complete"] for case in included)
    exclusions_reconciled = len(excluded) == sum(item["payment_count"] for item in exclusions)
    sample_complete = len(included) >= MINIMUM_INCLUDED_PAYMENTS
    passed = (
        sample_complete
        and baseline_complete
        and chain_complete
        and duplicate_count == 0
        and exclusions_reconciled
        and bool(cohorts)
    )
    total_amount = sum((case["amount"] for case in cases), Decimal(0))
    included_amount = sum((case["amount"] for case in included), Decimal(0))
    traceability_coverage = _percent(len(included), len(cases))
    interpretation = {
        "defensible_attribution": len(included),
        "correlation_only": sum(
            exclusion_counts[reason]
            for reason in (
                "attribution_missing",
                "contract_missing",
                "contract_rule_missing",
                "management_evidence_missing",
                "management_evidence_invalid",
            )
        ),
        "uncertain_or_ineligible": len(excluded)
        - sum(
            exclusion_counts[reason]
            for reason in (
                "attribution_missing",
                "contract_missing",
                "contract_rule_missing",
                "management_evidence_missing",
                "management_evidence_invalid",
            )
        ),
    }
    approved = passed and evidence_kind == "authorized_pilot" and authorization_complete
    gate_status = (
        "approved"
        if approved
        else "passed_synthetic"
        if passed and evidence_kind == "synthetic"
        else "authorization_incomplete"
        if passed and evidence_kind == "authorized_pilot"
        else "needs_evidence"
    )
    stable = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "evidence_kind": evidence_kind,
        "minimum_group_size": minimum_group_size,
        "population": {
            "verified_payments": len(cases),
            "included_payments": len(included),
            "excluded_payments": len(excluded),
            "included_clients": len(included_client_keys),
            "verified_amount_clp": f"{_decimal(total_amount):.2f}",
            "included_amount_clp": f"{_decimal(included_amount):.2f}",
            "traceability_coverage_percent": (
                f"{traceability_coverage:.2f}"
                if traceability_coverage is not None
                else None
            ),
        },
        "baseline_coverage": {
            "included_clients": len(included_client_keys),
            "complete": baseline_complete,
        },
        "authorization_coverage": {"complete": authorization_complete},
        "traceability": {
            "chain_complete": chain_complete,
            "included_payment_count": len(included),
            "unique_payment_count": unique_payment_count,
            "duplicate_count": duplicate_count,
            "exclusions_reconciled": exclusions_reconciled,
        },
        "interpretation": interpretation,
        "cohorts": cohorts,
        "suppressed_groups": suppressed,
        "exclusions": exclusions,
        "concentrations": concentrations,
        "evidence_gaps": {
            "unclassified_cause_payments": sum(
                1 for case in included if not case["cause"]
            ),
            "missing_industry_payments": sum(
                1 for case in included if not case["industry"]
            ),
        },
        "pm_g3": {
            "status": gate_status,
            "local_phase_complete": passed,
            "pm4_authorized": approved,
            "sample_complete": sample_complete,
            "reason": (
                "Todos los resultados incluidos reconstruyen pago, evidencia, gestión y regla contractual; las exclusiones están declaradas."
                if passed
                else "La muestra todavía presenta brechas de comparabilidad, trazabilidad o privacidad."
            ),
        },
        "assumptions": {
            "unit_of_analysis": "verified_payment",
            "cohort": "Pagos verificados en el período y sus facturas asociadas.",
            "attribution_rule": "Sólo se incluye una cadena completa y congelada; una asociación temporal aislada se declara correlación.",
            "double_count_policy": "Cada payment_id puede aparecer una sola vez; una factura con pagos parciales conserva pagos separados sin duplicar montos.",
        },
        "privacy": {
            "aggregate_only": True,
            "aliases": "HMAC-SHA256",
            "excluded_fields": [
                "client names",
                "RUT",
                "invoice folios",
                "payment identifiers",
                "event identifiers",
                "free-text notes",
            ],
        },
    }
    fingerprint = hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return {**stable, "fingerprint_sha256": fingerprint}


def build_comparables_attribution_report(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    minimum_group_size: int = 2,
    evidence_kind: Literal["synthetic", "authorized_pilot"] = "synthetic",
) -> dict[str, Any]:
    from app.config import settings

    if date_to < date_from:
        raise ValueError("date_to no puede ser anterior a date_from")
    if (date_to - date_from).days > 365:
        raise ValueError("El rango máximo es de 366 días")
    if not 1 <= minimum_group_size <= 50:
        raise ValueError("minimum_group_size debe estar entre 1 y 50")
    clients = {
        client.id: client
        for client in db.scalars(select(Client).where(Client.active.is_(True)))
    }
    if not clients:
        return compile_comparables_report(
            [],
            date_from=date_from,
            date_to=date_to,
            minimum_group_size=minimum_group_size,
            evidence_kind=evidence_kind,
            anonymization_key=settings.report_anonymization_key,
            authorization_complete=False,
        )
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.client_id.in_(clients),
                Payment.verified.is_(True),
                Payment.paid_on >= date_from,
                Payment.paid_on <= date_to,
            )
        )
    )
    payment_ids = [payment.id for payment in payments]
    invoice_ids = {payment.invoice_id for payment in payments}
    invoices = {
        invoice.id: invoice
        for invoice in db.scalars(select(Invoice).where(Invoice.id.in_(invoice_ids)))
    } if invoice_ids else {}
    attributions = {
        attribution.payment_id: attribution
        for attribution in db.scalars(
            select(PaymentAttribution).where(
                PaymentAttribution.payment_id.in_(payment_ids)
            )
        )
    } if payment_ids else {}
    contract_ids = {
        attribution.contract_id
        for attribution in attributions.values()
        if attribution.contract_id is not None
    }
    contracts = {
        contract.id: contract
        for contract in db.scalars(select(Contract).where(Contract.id.in_(contract_ids)))
    } if contract_ids else {}
    document_ids = {
        payment.evidence_document_id
        for payment in payments
        if payment.evidence_document_id is not None
    }
    documents = {
        document.id: document
        for document in db.scalars(select(Document).where(Document.id.in_(document_ids)))
    } if document_ids else {}
    transaction_ids = {
        payment.bank_transaction_id
        for payment in payments
        if payment.bank_transaction_id is not None
    }
    transactions = {
        transaction.id: transaction
        for transaction in db.scalars(
            select(BankTransaction).where(BankTransaction.id.in_(transaction_ids))
        )
    } if transaction_ids else {}
    events = {
        event.id: event
        for event in db.scalars(select(Event).where(Event.invoice_id.in_(invoice_ids)))
    } if invoice_ids else {}
    causes = {
        cause.invoice_id: cause.category
        for cause in db.scalars(select(DelayCause).where(DelayCause.invoice_id.in_(invoice_ids)))
    } if invoice_ids else {}

    cases: list[dict[str, Any]] = []
    for payment in payments:
        invoice = invoices.get(payment.invoice_id)
        client = clients.get(payment.client_id)
        attribution = attributions.get(payment.id)
        exclusion_reason: str | None = None
        if invoice is None or client is None:
            exclusion_reason = "attribution_mismatch"
        elif client.baseline_dso is None or client.baseline_on_time_percent is None:
            exclusion_reason = "missing_client_baseline"
        elif invoice.currency != "CLP":
            exclusion_reason = "unsupported_currency"
        elif payment.verified_by is None or payment.verified_at is None:
            exclusion_reason = "verification_metadata_missing"
        else:
            document = documents.get(payment.evidence_document_id)
            transaction = transactions.get(payment.bank_transaction_id)
            valid_document = (
                document is not None
                and document.client_id == payment.client_id
                and document.invoice_id == payment.invoice_id
                and document.encryption_version == "aesgcm-v1"
            )
            valid_transaction = (
                transaction is not None
                and transaction.client_id == payment.client_id
            )
            if not valid_document and not valid_transaction:
                exclusion_reason = "payment_evidence_missing"
        if exclusion_reason is None and attribution is None:
            exclusion_reason = "attribution_missing"
        contract = contracts.get(attribution.contract_id) if attribution else None
        rationale = attribution.rationale if attribution else {}
        if exclusion_reason is None and attribution is not None:
            if (
                attribution.client_id != payment.client_id
                or attribution.invoice_id != payment.invoice_id
                or Decimal(attribution.base_amount) != Decimal(payment.amount)
            ):
                exclusion_reason = "attribution_mismatch"
            elif contract is None or contract.client_id != payment.client_id:
                exclusion_reason = "contract_missing"
            elif (
                rationale.get("contract_version") != contract.version
                or not rationale.get("rule")
            ):
                exclusion_reason = "contract_rule_missing"
            else:
                raw_event_ids = rationale.get("evidence_event_ids") or []
                if not raw_event_ids:
                    exclusion_reason = "management_evidence_missing"
                else:
                    event_ids: list[uuid.UUID] = []
                    try:
                        event_ids = [uuid.UUID(value) for value in raw_event_ids]
                    except (TypeError, ValueError):
                        exclusion_reason = "management_evidence_invalid"
                    payment_day_end = datetime.combine(
                        payment.paid_on, time.max, tzinfo=timezone.utc  # noqa: UP017 -- Python 3.10 tools
                    )
                    referenced = [events.get(event_id) for event_id in event_ids]
                    if exclusion_reason is None and (
                        any(event is None for event in referenced)
                        or any(
                            event.client_id != payment.client_id
                            or event.invoice_id != payment.invoice_id
                            or event.created_at > payment_day_end
                            or not event.event_type.startswith(MANAGEMENT_EVENT_PREFIXES)
                            for event in referenced
                            if event is not None
                        )
                    ):
                        exclusion_reason = "management_evidence_invalid"
        cases.append(
            {
                "payment_key": str(payment.id),
                "invoice_key": str(payment.invoice_id),
                "client_key": str(payment.client_id),
                "payer_key": str(invoice.payer_id) if invoice else "missing",
                "industry": client.industry if client else None,
                "baseline_dso": client.baseline_dso if client else None,
                "baseline_on_time_percent": (
                    Decimal(client.baseline_on_time_percent)
                    if client and client.baseline_on_time_percent is not None
                    else None
                ),
                "amount": Decimal(payment.amount),
                "amount_band": (
                    amount_band(Decimal(invoice.total_amount)) if invoice else "unknown"
                ),
                "cause": causes.get(payment.invoice_id),
                "on_time": bool(invoice and payment.paid_on <= invoice.due_on),
                "attribution_category": (
                    attribution.category if attribution else "missing"
                ),
                "chain_complete": exclusion_reason is None,
                "exclusion_reason": exclusion_reason,
            }
        )
    included_client_ids = {
        uuid.UUID(case["client_key"])
        for case in cases
        if case["exclusion_reason"] is None
    }
    authorization_complete = False
    if included_client_ids:
        authorization_events = list(
            db.scalars(
                select(PilotAuthorizationEvent)
                .where(PilotAuthorizationEvent.client_id.in_(included_client_ids))
                .order_by(
                    PilotAuthorizationEvent.created_at,
                    PilotAuthorizationEvent.id,
                )
            )
        )
        latest: dict[uuid.UUID, PilotAuthorizationEvent] = {}
        for event in authorization_events:
            latest[event.client_id] = event
        active_contracts = {
            contract.client_id: contract.id
            for contract in db.scalars(
                select(Contract).where(
                    Contract.client_id.in_(included_client_ids),
                    Contract.active.is_(True),
                )
            )
        }
        authorization_complete = all(
            (event := latest.get(client_id)) is not None
            and event.action == "approved"
            and event.evidence_document_id is not None
            and event.contract_id == active_contracts.get(client_id)
            and event.valid_from <= date_from
            and (event.valid_until is None or event.valid_until >= date_to)
            for client_id in included_client_ids
        )
    return compile_comparables_report(
        cases,
        date_from=date_from,
        date_to=date_to,
        minimum_group_size=minimum_group_size,
        evidence_kind=evidence_kind,
        anonymization_key=settings.report_anonymization_key,
        authorization_complete=authorization_complete,
    )


def comparables_matrix_csv(report: dict[str, Any]) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "schema_version",
            "dimension",
            "segment",
            "payment_count",
            "invoice_count",
            "verified_amount_clp",
            "baseline_on_time_percent",
            "observed_on_time_percent",
            "on_time_delta_points",
        ]
    )
    for row in report["cohorts"]:
        writer.writerow(
            [
                report["schema_version"],
                row["dimension"],
                row["segment"],
                row["payment_count"],
                row["invoice_count"],
                row["verified_amount_clp"],
                row["baseline_on_time_percent"],
                row["observed_on_time_percent"],
                row["on_time_delta_points"],
            ]
        )
    return stream.getvalue().encode("utf-8-sig")


def comparables_markdown(report: dict[str, Any]) -> bytes:
    lines = [
        "# PM-3 — Comparables y atribución defendible",
        "",
        f"Período: {report['date_from']} a {report['date_to']}",
        f"Tipo de evidencia: {report['evidence_kind']}",
        f"Huella SHA-256: `{report['fingerprint_sha256']}`",
        "",
        "> Una cadena temporal incompleta se declara correlación o incertidumbre; no se presenta como atribución.",
        "",
        "## Cobertura",
        "",
        f"- Pagos verificados: {report['population']['verified_payments']}.",
        f"- Pagos incluidos: {report['population']['included_payments']}.",
        f"- Pagos excluidos: {report['population']['excluded_payments']}.",
        f"- Cobertura trazable: {report['population']['traceability_coverage_percent'] or 'sin muestra'}%.",
        f"- Duplicados: {report['traceability']['duplicate_count']}.",
        "",
        "## Matriz de comparables",
        "",
        "| Dimensión | Segmento | Pagos | Monto | Base oportuno | Observado | Δ puntos |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["cohorts"]:
        lines.append(
            f"| {row['dimension']} | {row['segment']} | {row['payment_count']} | "
            f"{row['verified_amount_clp']} | {row['baseline_on_time_percent']}% | "
            f"{row['observed_on_time_percent']}% | {row['on_time_delta_points']} |"
        )
    lines.extend(["", "## Exclusiones", ""])
    if report["exclusions"]:
        for item in report["exclusions"]:
            lines.append(
                f"- `{item['reason']}`: {item['payment_count']} pagos; "
                f"CLP {item['verified_amount_clp']}. {item['description']}"
            )
    else:
        lines.append("- Sin exclusiones.")
    lines.extend(
        [
            "",
            "## Puerta PM-G3",
            "",
            f"Estado: **{report['pm_g3']['status']}**.",
            "",
            report["pm_g3"]["reason"],
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")
