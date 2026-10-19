import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Client,
    DelayCause,
    Event,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    MessageInvoice,
    PayabilityItem,
    Payment,
    PaymentAttribution,
    ReconciliationProposal,
)


def _decimal(value: Decimal | int | float | str, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _percent(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return _decimal(Decimal(numerator) * 100 / Decimal(denominator))


def _mode_breakdown(automatic: int, manual: int) -> dict[str, Any]:
    total = automatic + manual
    return {
        "automatic": automatic,
        "manual": manual,
        "total": total,
        "automatic_percent": _percent(automatic, total),
    }


def _settlement_dates(
    invoices: list[Invoice], payments: list[Payment]
) -> dict[uuid.UUID, date]:
    by_invoice: dict[uuid.UUID, list[Payment]] = defaultdict(list)
    for payment in payments:
        by_invoice[payment.invoice_id].append(payment)
    settled: dict[uuid.UUID, date] = {}
    for invoice in invoices:
        running = Decimal("0")
        for payment in sorted(
            by_invoice[invoice.id],
            key=lambda item: (
                item.paid_on,
                item.created_at or datetime.min.replace(tzinfo=timezone.utc),
                item.id,
            ),
        ):
            running += Decimal(payment.amount)
            if running >= Decimal(invoice.total_amount):
                settled[invoice.id] = payment.paid_on
                break
    return settled


def build_pilot_metrics(
    db: Session,
    *,
    client: Client,
    date_from: date,
    date_to: date,
    human_hourly_cost_clp: Decimal,
    usd_clp_rate: Decimal,
) -> dict[str, Any]:
    if date_to < date_from:
        raise ValueError("date_to no puede ser anterior a date_from")
    if (date_to - date_from).days > 365:
        raise ValueError("El rango máximo es de 366 días")
    if human_hourly_cost_clp < 0 or usd_clp_rate <= 0:
        raise ValueError("Los supuestos económicos deben ser positivos")
    start_at = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    invoices = list(
        db.scalars(
            select(Invoice).where(
                Invoice.client_id == client.id,
                Invoice.issued_on <= date_to,
            )
        )
    )
    invoice_by_id = {invoice.id: invoice for invoice in invoices}
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.client_id == client.id,
                Payment.verified.is_(True),
                Payment.paid_on <= date_to,
            )
        )
    )
    period_payments = [
        payment for payment in payments if date_from <= payment.paid_on <= date_to
    ]
    settlement_dates = _settlement_dates(invoices, payments)
    settled_in_period = [
        invoice
        for invoice in invoices
        if date_from <= settlement_dates.get(invoice.id, date.min) <= date_to
    ]
    on_time = [
        invoice
        for invoice in settled_in_period
        if settlement_dates[invoice.id] <= invoice.due_on
    ]
    dso_values = [
        Decimal((settlement_dates[invoice.id] - invoice.issued_on).days)
        for invoice in settled_in_period
    ]
    managed_ids = set(
        db.scalars(
            select(Event.invoice_id).where(
                Event.client_id == client.id,
                Event.invoice_id.is_not(None),
                Event.created_at >= start_at,
                Event.created_at <= end_at,
            )
        )
    )
    managed_ids.update(
        invoice.id for invoice in invoices if date_from <= invoice.issued_on <= date_to
    )
    recovered_amount = sum(
        (
            Decimal(payment.amount)
            for payment in period_payments
            if payment.invoice_id in invoice_by_id
            and payment.paid_on > invoice_by_id[payment.invoice_id].due_on
        ),
        Decimal("0"),
    )
    exceptions = list(
        db.scalars(
            select(ExceptionCase).where(
                ExceptionCase.client_id == client.id,
                ExceptionCase.created_at >= start_at,
                ExceptionCase.created_at <= end_at,
            )
        )
    )
    human_minutes = sum(
        (Decimal(item.human_minutes or 0) for item in exceptions), Decimal("0")
    )
    message_links = list(
        db.scalars(
            select(MessageInvoice).where(
                MessageInvoice.client_id == client.id,
                MessageInvoice.created_at >= start_at,
                MessageInvoice.created_at <= end_at,
            )
        )
    )
    llm_cost_usd = sum(
        (Decimal(item.allocated_llm_cost) for item in message_links), Decimal("0")
    )
    messaging_cost_usd = sum(
        (Decimal(item.allocated_messaging_cost) for item in message_links), Decimal("0")
    )
    messages = list(
        db.scalars(
            select(Message).where(
                Message.client_id == client.id,
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
                MessageClassification.client_id == client.id,
                MessageClassification.created_at >= start_at,
                MessageClassification.created_at <= end_at,
            )
        )
    )
    proposals = list(
        db.scalars(
            select(ReconciliationProposal).where(
                ReconciliationProposal.client_id == client.id,
                ReconciliationProposal.created_at >= start_at,
                ReconciliationProposal.created_at <= end_at,
            )
        )
    )
    decisions = [
        proposal
        for proposal in proposals
        if proposal.status in {"confirmed", "rejected"} and proposal.reviewed_at is not None
    ]
    attributions = (
        list(
            db.scalars(
                select(PaymentAttribution).where(
                    PaymentAttribution.client_id == client.id,
                    PaymentAttribution.payment_id.in_([payment.id for payment in period_payments]),
                )
            )
        )
        if period_payments
        else []
    )
    commission_clp = sum(
        (Decimal(item.commission_amount) for item in attributions), Decimal("0")
    )
    technology_cost_usd = llm_cost_usd + messaging_cost_usd
    technology_cost_clp = technology_cost_usd * usd_clp_rate
    human_cost_clp = human_minutes * human_hourly_cost_clp / Decimal("60")
    total_cost_clp = technology_cost_clp + human_cost_clp
    margin_clp = commission_clp - total_cost_clp
    managed_count = len(managed_ids)

    causes: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"invoice_count": 0, "amount": Decimal("0")}
    )
    for cause in db.scalars(
        select(DelayCause).where(
            DelayCause.client_id == client.id,
            DelayCause.created_at >= start_at,
            DelayCause.created_at <= end_at,
        )
    ):
        invoice = invoice_by_id.get(cause.invoice_id)
        if invoice is None:
            continue
        causes[cause.category]["invoice_count"] += 1
        causes[cause.category]["amount"] += Decimal(invoice.total_amount)
    resolution_groups: dict[str, list[Decimal]] = defaultdict(list)
    for item in db.scalars(
        select(PayabilityItem).where(
            PayabilityItem.client_id == client.id,
            PayabilityItem.status.in_(["fulfilled", "not_applicable"]),
            PayabilityItem.updated_at >= start_at,
            PayabilityItem.updated_at <= end_at,
        )
    ):
        elapsed_seconds = max((item.updated_at - item.created_at).total_seconds(), 0)
        hours = Decimal(str(elapsed_seconds)) / Decimal("3600")
        resolution_groups[item.item_type].append(hours)

    trend = []
    week_start = date_from
    while week_start <= date_to:
        week_end = min(week_start + timedelta(days=6), date_to)
        week_settled = [
            invoice
            for invoice in invoices
            if week_start <= settlement_dates.get(invoice.id, date.min) <= week_end
        ]
        week_on_time = [
            invoice
            for invoice in week_settled
            if settlement_dates[invoice.id] <= invoice.due_on
        ]
        week_dso = [
            Decimal((settlement_dates[invoice.id] - invoice.issued_on).days)
            for invoice in week_settled
        ]
        trend.append(
            {
                "week_start": week_start,
                "week_end": week_end,
                "settled_invoices": len(week_settled),
                "on_time_percent": _percent(len(week_on_time), len(week_settled)),
                "average_dso": (
                    _decimal(sum(week_dso, Decimal("0")) / len(week_dso))
                    if week_dso
                    else None
                ),
                "verified_amount": _decimal(
                    sum(
                        (
                            Decimal(payment.amount)
                            for payment in period_payments
                            if week_start <= payment.paid_on <= week_end
                        ),
                        Decimal("0"),
                    )
                ),
            }
        )
        week_start += timedelta(days=7)

    return {
        "client_id": client.id,
        "client_name": client.name,
        "date_from": date_from,
        "date_to": date_to,
        "baseline": {
            "dso": client.baseline_dso,
            "on_time_percent": client.baseline_on_time_percent,
        },
        "outcomes": {
            "managed_invoices": managed_count,
            "settled_invoices": len(settled_in_period),
            "average_dso": (
                _decimal(sum(dso_values, Decimal("0")) / len(dso_values))
                if dso_values
                else None
            ),
            "on_time_percent": _percent(len(on_time), len(settled_in_period)),
            "verified_amount": _decimal(
                sum((Decimal(payment.amount) for payment in period_payments), Decimal("0"))
            ),
            "recovered_amount": _decimal(recovered_amount),
        },
        "operations": {
            "human_minutes": _decimal(human_minutes),
            "messages": _mode_breakdown(
                sum(message.mode == "automatic" for message in messages),
                sum(message.mode == "manual" for message in messages),
            ),
            "classifications": _mode_breakdown(
                sum(item.decision_source == "system" for item in classifications),
                sum(item.decision_source == "human" for item in classifications),
            ),
            "reconciliations": _mode_breakdown(len(proposals), len(decisions)),
        },
        "economics": {
            "commission_clp": _decimal(commission_clp),
            "llm_cost_usd": _decimal(llm_cost_usd, "0.000001"),
            "messaging_cost_usd": _decimal(messaging_cost_usd, "0.000001"),
            "technology_cost_clp": _decimal(technology_cost_clp),
            "human_cost_clp": _decimal(human_cost_clp),
            "total_cost_clp": _decimal(total_cost_clp),
            "cost_per_managed_invoice_clp": (
                _decimal(total_cost_clp / managed_count) if managed_count else None
            ),
            "margin_clp": _decimal(margin_clp),
        },
        "assumptions": {
            "human_hourly_cost_clp": _decimal(human_hourly_cost_clp),
            "usd_clp_rate": _decimal(usd_clp_rate),
            "note": "Supuestos editables para análisis local; no corresponden a una cotización externa.",
        },
        "delay_causes": [
            {
                "category": category,
                "invoice_count": values["invoice_count"],
                "amount": _decimal(values["amount"]),
            }
            for category, values in sorted(causes.items())
        ],
        "resolution_times": [
            {
                "item_type": item_type,
                "resolved_count": len(values),
                "average_hours": _decimal(sum(values, Decimal("0")) / len(values)),
            }
            for item_type, values in sorted(resolution_groups.items())
        ],
        "trend": trend,
        "generated_at": datetime.now(timezone.utc),
    }
