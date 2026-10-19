import csv
import hashlib
import hmac
import io
import json
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, DelayCause, Invoice, Payment
from app.services.pilot_metrics import build_pilot_metrics


DOCUMENTARY_CAUSES = {
    "sii_acceptance",
    "purchase_order",
    "hes_conformity",
    "delivery_note",
    "supplier_portal",
    "missing_document",
    "document_error",
}
REPORT_SCHEMA_VERSION = "fase-8.1-v1"


def _decimal(value: Decimal | int | float | str, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def anonymized_alias(
    namespace: str, identifier: uuid.UUID | str, key: str | None = None
) -> str:
    if key is None:
        from app.config import settings

        key = settings.report_anonymization_key
    digest = hmac.new(
        key.encode("utf-8"),
        f"{namespace}:{identifier}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:10].upper()
    prefix = "PYME" if namespace == "client" else "PAGADOR"
    return f"{prefix}-{digest}"


def amount_band(amount: Decimal) -> str:
    if amount < Decimal("500000"):
        return "menos_de_500k"
    if amount < Decimal("2000000"):
        return "500k_a_2m"
    if amount < Decimal("10000000"):
        return "2m_a_10m"
    return "10m_o_mas"


def _sum_decimal(items: list[dict[str, Any]], path: tuple[str, ...]) -> Decimal:
    total = Decimal("0")
    for item in items:
        value: Any = item
        for key in path:
            value = value[key]
        total += Decimal(value or 0)
    return total


def _weighted_metric(
    items: list[dict[str, Any]], metric: str, weight: str
) -> Decimal | None:
    eligible = [
        item
        for item in items
        if item["outcomes"].get(metric) is not None and item["outcomes"].get(weight, 0)
    ]
    denominator = sum(item["outcomes"][weight] for item in eligible)
    if not denominator:
        return None
    numerator = sum(
        Decimal(item["outcomes"][metric]) * item["outcomes"][weight]
        for item in eligible
    )
    return _decimal(numerator / denominator)


def _comparison(report: dict[str, Any], alias: str) -> dict[str, Any]:
    baseline_dso = report["baseline"].get("dso")
    current_dso = report["outcomes"].get("average_dso")
    baseline_on_time = report["baseline"].get("on_time_percent")
    current_on_time = report["outcomes"].get("on_time_percent")
    dso_delta = (
        _decimal(Decimal(current_dso) - Decimal(baseline_dso))
        if current_dso is not None and baseline_dso is not None
        else None
    )
    on_time_delta = (
        _decimal(Decimal(current_on_time) - Decimal(baseline_on_time))
        if current_on_time is not None and baseline_on_time is not None
        else None
    )
    positive_signals = sum(
        (
            dso_delta is not None and dso_delta < 0,
            on_time_delta is not None and on_time_delta > 0,
        )
    )
    negative_signals = sum(
        (
            dso_delta is not None and dso_delta > 0,
            on_time_delta is not None and on_time_delta < 0,
        )
    )
    if dso_delta is None and on_time_delta is None:
        result = "insufficient_data"
    elif positive_signals and not negative_signals:
        result = "improved"
    elif negative_signals and not positive_signals:
        result = "declined"
    else:
        result = "mixed"
    return {
        "client_alias": alias,
        "baseline_dso": baseline_dso,
        "current_dso": current_dso,
        "dso_delta_days": dso_delta,
        "baseline_on_time_percent": baseline_on_time,
        "current_on_time_percent": current_on_time,
        "on_time_delta_points": on_time_delta,
        "managed_invoices": report["outcomes"]["managed_invoices"],
        "settled_invoices": report["outcomes"]["settled_invoices"],
        "human_minutes": report["operations"]["human_minutes"],
        "margin_clp": report["economics"]["margin_clp"],
        "result": result,
    }


def _segment_rows(
    *,
    clients: list[Client],
    invoices: list[Invoice],
    payments: list[Payment],
    causes: dict[uuid.UUID, str],
    date_from: date,
    date_to: date,
    minimum_group_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payments_by_invoice: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for payment in payments:
        payments_by_invoice[payment.invoice_id].append(payment)
    client_aliases = {item.id: anonymized_alias("client", item.id) for item in clients}
    groups: dict[tuple[str, str], dict[str, Any]] = {}

    def add(dimension: str, segment: str, invoice: Invoice) -> None:
        key = (dimension, segment)
        row = groups.setdefault(
            key,
            {
                "dimension": dimension,
                "segment": segment,
                "invoice_count": 0,
                "nominal_amount_clp": Decimal("0"),
                "verified_amount_clp": Decimal("0"),
                "settled_invoices": 0,
                "on_time_invoices": 0,
                "settlement_days_total": Decimal("0"),
            },
        )
        row["invoice_count"] += 1
        row["nominal_amount_clp"] += Decimal(invoice.total_amount)
        invoice_payments = sorted(
            payments_by_invoice.get(invoice.id, []), key=lambda item: (item.paid_on, item.id)
        )
        row["verified_amount_clp"] += sum(
            (
                Decimal(item.amount)
                for item in invoice_payments
                if date_from <= item.paid_on <= date_to
            ),
            Decimal("0"),
        )
        running = Decimal("0")
        for payment in invoice_payments:
            running += Decimal(payment.amount)
            if running >= Decimal(invoice.total_amount):
                row["settled_invoices"] += 1
                row["settlement_days_total"] += Decimal(
                    max((payment.paid_on - invoice.issued_on).days, 0)
                )
                if payment.paid_on <= invoice.due_on:
                    row["on_time_invoices"] += 1
                break

    for invoice in invoices:
        add("client", client_aliases[invoice.client_id], invoice)
        add("payer", anonymized_alias("payer", invoice.payer_id), invoice)
        add("cause", causes.get(invoice.id, "unclassified"), invoice)
        add("amount_band", amount_band(Decimal(invoice.total_amount)), invoice)

    published: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for row in sorted(groups.values(), key=lambda item: (item["dimension"], item["segment"])):
        count = row["invoice_count"]
        settled = row["settled_invoices"]
        normalized = {
            "dimension": row["dimension"],
            "segment": row["segment"],
            "invoice_count": count,
            "nominal_amount_clp": _decimal(row["nominal_amount_clp"]),
            "verified_amount_clp": _decimal(row["verified_amount_clp"]),
            "settled_invoices": settled,
            "on_time_percent": (
                _decimal(Decimal(row["on_time_invoices"]) * 100 / settled)
                if settled
                else None
            ),
            "average_settlement_days": (
                _decimal(row["settlement_days_total"] / settled) if settled else None
            ),
        }
        if count >= minimum_group_size:
            published.append(normalized)
        else:
            suppressed.append(
                {
                    "dimension": row["dimension"],
                    "groups": 1,
                    "invoice_count": count,
                }
            )
    suppressed_summary: dict[str, dict[str, Any]] = {}
    for row in suppressed:
        summary = suppressed_summary.setdefault(
            row["dimension"], {"dimension": row["dimension"], "groups": 0, "invoice_count": 0}
        )
        summary["groups"] += row["groups"]
        summary["invoice_count"] += row["invoice_count"]
    return published, list(suppressed_summary.values())


def _hypotheses(
    comparisons: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    margin_clp: Decimal,
) -> list[dict[str, str]]:
    comparable = [item for item in comparisons if item["result"] != "insufficient_data"]
    improved = [item for item in comparable if item["result"] == "improved"]
    if not comparable:
        outcome_state = "uncertain"
    elif len(improved) > len(comparable) / 2:
        outcome_state = "confirmed"
    elif not improved:
        outcome_state = "rejected"
    else:
        outcome_state = "uncertain"

    cause_rows = [item for item in segments if item["dimension"] == "cause"]
    cause_total = sum(item["invoice_count"] for item in cause_rows)
    documentary = sum(
        item["invoice_count"] for item in cause_rows if item["segment"] in DOCUMENTARY_CAUSES
    )
    documentary_share = Decimal(documentary) * 100 / cause_total if cause_total else None
    if documentary_share is None or cause_total < 10:
        documentary_state = "uncertain"
    elif documentary_share >= 30:
        documentary_state = "confirmed"
    elif documentary_share < 15:
        documentary_state = "rejected"
    else:
        documentary_state = "uncertain"

    economics_state = (
        "confirmed" if margin_clp > 0 else "rejected" if margin_clp < 0 else "uncertain"
    )
    return [
        {
            "key": "outcome_improvement",
            "statement": "La gestión mejora DSO o pago oportuno frente a la línea base.",
            "state": outcome_state,
            "evidence": (
                f"{len(improved)} de {len(comparable)} clientes comparables "
                "mejoran sin señal contraria."
            ),
        },
        {
            "key": "documentary_relevance",
            "statement": "Los bloqueos documentales explican una parte relevante del atraso.",
            "state": documentary_state,
            "evidence": (
                f"{_decimal(documentary_share)}% de {cause_total} facturas agrupadas por causa."
                if documentary_share is not None
                else "No hay muestra de causas suficiente."
            ),
        },
        {
            "key": "positive_unit_economics",
            "statement": (
                "Existe una ruta observada a margen positivo incluyendo costo humano "
                "y tecnología."
            ),
            "state": economics_state,
            "evidence": f"Margen agregado estimado: CLP {_decimal(margin_clp)}.",
        },
    ]


def evaluate_g4(
    *,
    evidence_kind: Literal["synthetic", "authorized_pilot"],
    period_days: int,
    client_count: int,
    settled_invoices: int,
    hypotheses: list[dict[str, str]],
    payer_concentration_percent: Decimal | None,
) -> dict[str, Any]:
    readiness_checks = [
        {
            "key": "authorized_evidence",
            "passed": evidence_kind == "authorized_pilot",
            "required": True,
        },
        {"key": "minimum_period", "passed": period_days >= 42, "required": True},
        {"key": "minimum_clients", "passed": client_count >= 2, "required": True},
        {"key": "minimum_settlements", "passed": settled_invoices >= 10, "required": True},
    ]
    ready = all(item["passed"] for item in readiness_checks)
    states = {item["key"]: item["state"] for item in hypotheses}
    concentrated = payer_concentration_percent is not None and payer_concentration_percent >= 60
    if not ready:
        recommendation = "pending"
        reason = "La evidencia aún no cumple los mínimos para una decisión G4 verificable."
    elif (
        states["outcome_improvement"] == "confirmed"
        and states["documentary_relevance"] == "confirmed"
        and states["positive_unit_economics"] == "confirmed"
        and not concentrated
    ):
        recommendation = "scale"
        reason = (
            "Resultado, hipótesis documental y economía son favorables sin "
            "concentración crítica."
        )
    elif states["outcome_improvement"] == "confirmed":
        recommendation = "iterate"
        reason = (
            "Existe resultado, pero la concentración, la economía o la operación "
            "requieren ajuste."
        )
    elif (
        states["outcome_improvement"] == "rejected"
        and states["positive_unit_economics"] == "rejected"
    ):
        recommendation = "stop"
        reason = "No se observa mejora ni economía viable en la evidencia disponible."
    elif states["documentary_relevance"] == "rejected":
        recommendation = "pivot"
        reason = "La hipótesis documental no explica suficiente valor en la muestra."
    else:
        recommendation = "iterate"
        reason = "La evidencia es mixta; corresponde una iteración acotada antes de escalar."

    labels = {
        "scale": "Escalar",
        "iterate": "Iterar segmento u operación",
        "pivot": "Pivotar producto",
        "stop": "Detener",
    }
    matrix = [
        {
            "option": key,
            "label": label,
            "status": (
                "recommended"
                if recommendation == key
                else "pending" if not ready else "not_recommended"
            ),
        }
        for key, label in labels.items()
    ]
    return {
        "ready": ready,
        "recommendation": recommendation,
        "reason": reason,
        "readiness_checks": readiness_checks,
        "matrix": matrix,
    }


def build_final_report(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    human_hourly_cost_clp: Decimal,
    usd_clp_rate: Decimal,
    minimum_group_size: int,
    evidence_kind: Literal["synthetic", "authorized_pilot"],
) -> dict[str, Any]:
    if date_to < date_from:
        raise ValueError("date_to no puede ser anterior a date_from")
    if (date_to - date_from).days > 365:
        raise ValueError("El rango máximo es de 366 días")
    if not 1 <= minimum_group_size <= 50:
        raise ValueError("minimum_group_size debe estar entre 1 y 50")
    clients = list(db.scalars(select(Client).where(Client.active.is_(True)).order_by(Client.id)))
    reports = [
        build_pilot_metrics(
            db,
            client=client,
            date_from=date_from,
            date_to=date_to,
            human_hourly_cost_clp=human_hourly_cost_clp,
            usd_clp_rate=usd_clp_rate,
        )
        for client in clients
    ]
    analysis_comparisons = [
        _comparison(report, anonymized_alias("client", client.id))
        for client, report in zip(clients, reports, strict=True)
    ]
    comparisons = [
        item
        for item in analysis_comparisons
        if item["managed_invoices"] >= minimum_group_size
    ]
    client_ids = [item.id for item in clients]
    invoices = (
        list(
            db.scalars(
                select(Invoice).where(
                    Invoice.client_id.in_(client_ids),
                    Invoice.issued_on >= date_from,
                    Invoice.issued_on <= date_to,
                )
            )
        )
        if client_ids
        else []
    )
    invoice_ids = [item.id for item in invoices]
    payments = (
        list(
            db.scalars(
                select(Payment).where(
                    Payment.invoice_id.in_(invoice_ids),
                    Payment.verified.is_(True),
                    Payment.paid_on <= date_to,
                )
            )
        )
        if invoice_ids
        else []
    )
    causes = (
        {
            item.invoice_id: item.category
            for item in db.scalars(
                select(DelayCause).where(DelayCause.invoice_id.in_(invoice_ids))
            )
        }
        if invoice_ids
        else {}
    )
    segments, suppressed = _segment_rows(
        clients=clients,
        invoices=invoices,
        payments=payments,
        causes=causes,
        date_from=date_from,
        date_to=date_to,
        minimum_group_size=minimum_group_size,
    )
    analysis_segments, _ = _segment_rows(
        clients=clients,
        invoices=invoices,
        payments=payments,
        causes=causes,
        date_from=date_from,
        date_to=date_to,
        minimum_group_size=1,
    )
    suppressed_comparisons = len(analysis_comparisons) - len(comparisons)
    if suppressed_comparisons:
        suppressed.append(
            {
                "dimension": "client_comparison",
                "groups": suppressed_comparisons,
                "invoice_count": sum(
                    item["managed_invoices"]
                    for item in analysis_comparisons
                    if item["managed_invoices"] < minimum_group_size
                ),
            }
        )
    settled_invoices = sum(item["outcomes"]["settled_invoices"] for item in reports)
    portfolio = {
        "client_count": len(clients),
        "managed_invoices": sum(item["outcomes"]["managed_invoices"] for item in reports),
        "settled_invoices": settled_invoices,
        "average_dso": _weighted_metric(reports, "average_dso", "settled_invoices"),
        "on_time_percent": _weighted_metric(reports, "on_time_percent", "settled_invoices"),
        "verified_amount_clp": _decimal(_sum_decimal(reports, ("outcomes", "verified_amount"))),
        "recovered_amount_clp": _decimal(_sum_decimal(reports, ("outcomes", "recovered_amount"))),
        "human_minutes": _decimal(_sum_decimal(reports, ("operations", "human_minutes"))),
        "commission_clp": _decimal(_sum_decimal(reports, ("economics", "commission_clp"))),
        "total_cost_clp": _decimal(_sum_decimal(reports, ("economics", "total_cost_clp"))),
        "margin_clp": _decimal(_sum_decimal(reports, ("economics", "margin_clp"))),
    }
    payer_rows = [item for item in analysis_segments if item["dimension"] == "payer"]
    total_nominal = sum((Decimal(item["nominal_amount_clp"]) for item in payer_rows), Decimal("0"))
    top_payer = max(
        (Decimal(item["nominal_amount_clp"]) for item in payer_rows),
        default=Decimal("0"),
    )
    payer_concentration = _decimal(top_payer * 100 / total_nominal) if total_nominal else None
    hypotheses = _hypotheses(
        analysis_comparisons, analysis_segments, Decimal(portfolio["margin_clp"])
    )
    g4 = evaluate_g4(
        evidence_kind=evidence_kind,
        period_days=(date_to - date_from).days + 1,
        client_count=len(clients),
        settled_invoices=settled_invoices,
        hypotheses=hypotheses,
        payer_concentration_percent=payer_concentration,
    )
    stable_payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "evidence_kind": evidence_kind,
        "minimum_group_size": minimum_group_size,
        "portfolio": portfolio,
        "client_comparisons": comparisons,
        "segments": segments,
        "hypotheses": hypotheses,
        "g4": g4,
    }
    fingerprint = hashlib.sha256(
        json.dumps(stable_payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **stable_payload,
        "period_days": (date_to - date_from).days + 1,
        "payer_concentration_percent": payer_concentration,
        "suppressed_groups": suppressed,
        "privacy": {
            "method": "HMAC-SHA256 aliases + aggregated dimensions",
            "minimum_group_size": minimum_group_size,
            "excluded_fields": ["names", "rut", "invoice_folio", "internal_ids", "contacts"],
        },
        "assumptions": {
            "human_hourly_cost_clp": _decimal(human_hourly_cost_clp),
            "usd_clp_rate": _decimal(usd_clp_rate),
            "cohort": (
                "Facturas emitidas en el período para segmentación; pagos "
                "verificados para resultados."
            ),
        },
        "fingerprint_sha256": fingerprint,
        "generated_at": datetime.now(timezone.utc),
    }


def anonymized_dataset_csv(report: dict[str, Any]) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "schema_version",
            "date_from",
            "date_to",
            "dimension",
            "segment",
            "invoice_count",
            "nominal_amount_clp",
            "verified_amount_clp",
            "settled_invoices",
            "on_time_percent",
            "average_settlement_days",
        ]
    )
    for row in report["segments"]:
        writer.writerow(
            [
                report["schema_version"],
                report["date_from"],
                report["date_to"],
                row["dimension"],
                row["segment"],
                row["invoice_count"],
                row["nominal_amount_clp"],
                row["verified_amount_clp"],
                row["settled_invoices"],
                row["on_time_percent"] if row["on_time_percent"] is not None else "",
                row["average_settlement_days"]
                if row["average_settlement_days"] is not None
                else "",
            ]
        )
    return stream.getvalue().encode("utf-8-sig")


def final_report_markdown(report: dict[str, Any]) -> bytes:
    recommendation_labels = {
        "pending": "Pendiente de evidencia suficiente",
        "scale": "Escalar",
        "iterate": "Iterar segmento u operación",
        "pivot": "Pivotar producto",
        "stop": "Detener",
    }
    lines = [
        "# Informe final V-10 — Piloto Recupera",
        "",
        f"Período: {report['date_from']} a {report['date_to']} ({report['period_days']} días)",
        f"Tipo de evidencia: {report['evidence_kind']}",
        f"Versión del esquema: {report['schema_version']}",
        f"Huella reproducible SHA-256: `{report['fingerprint_sha256']}`",
        "",
        (
            "> Los datos de demostración son sintéticos y no habilitan una decisión G4 real."
            if report["evidence_kind"] == "synthetic"
            else (
                "> Evidencia declarada como piloto autorizado; requiere revisión "
                "humana antes de decidir."
            )
        ),
        "",
        "## Resumen agregado",
        "",
        f"- Pymes: {report['portfolio']['client_count']}",
        f"- Facturas gestionadas: {report['portfolio']['managed_invoices']}",
        f"- Facturas saldadas: {report['portfolio']['settled_invoices']}",
        f"- DSO promedio: {report['portfolio']['average_dso'] or 'sin muestra'} días",
        f"- Pago oportuno: {report['portfolio']['on_time_percent'] or 'sin muestra'}%",
        f"- Margen estimado: CLP {report['portfolio']['margin_clp']}",
        "",
        "## Comparación contra línea base",
        "",
        (
            "| Pyme | DSO base | DSO actual | Δ días | Pago base | Pago actual "
            "| Δ puntos | Resultado |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report["client_comparisons"]:
        values = [
            item["client_alias"],
            item["baseline_dso"],
            item["current_dso"],
            item["dso_delta_days"],
            item["baseline_on_time_percent"],
            item["current_on_time_percent"],
            item["on_time_delta_points"],
            item["result"],
        ]
        cells = " | ".join("—" if value is None else str(value) for value in values)
        lines.append(f"| {cells} |")
    lines.extend(["", "## Hipótesis", ""])
    for item in report["hypotheses"]:
        lines.append(f"- **{item['state']}** — {item['statement']} {item['evidence']}")
    lines.extend(
        [
            "",
            "## Puerta G4",
            "",
            f"Recomendación: **{recommendation_labels[report['g4']['recommendation']]}**.",
            "",
            report["g4"]["reason"],
            "",
            "### Controles de suficiencia",
            "",
        ]
    )
    for check in report["g4"]["readiness_checks"]:
        lines.append(f"- {'Cumple' if check['passed'] else 'Pendiente'}: `{check['key']}`")
    lines.extend(
        [
            "",
            "## Privacidad y reproducibilidad",
            "",
            f"El dataset usa {report['privacy']['method']} y exige al menos "
            f"{report['privacy']['minimum_group_size']} facturas por grupo publicado.",
            "No contiene nombres, RUT, folios, contactos ni identificadores internos.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8-sig")
