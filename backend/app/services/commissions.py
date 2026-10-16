import uuid
from calendar import monthrange
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType
from app.models import (
    Contract,
    Event,
    ExceptionCase,
    Invoice,
    Message,
    MessageInvoice,
    Payment,
    PaymentAttribution,
)


ATTRIBUTION_EVENT_PREFIXES = (
    "payability.",
    "workflow.",
    "message.",
    "communication.",
    "exception.",
)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _management_events(db: Session, payment: Payment) -> list[Event]:
    end_of_payment_day = datetime.combine(payment.paid_on, time.max, tzinfo=timezone.utc)
    return list(
        db.scalars(
            select(Event).where(
                Event.client_id == payment.client_id,
                Event.invoice_id == payment.invoice_id,
                Event.created_at <= end_of_payment_day,
                Event.event_type.not_like("payment.%"),
                Event.event_type.not_like("reconciliation.%"),
            )
        )
    )


def attribute_payment(db: Session, payment: Payment) -> PaymentAttribution:
    """Freeze the contractual attribution of one verified payment exactly once."""
    existing = db.scalar(
        select(PaymentAttribution).where(PaymentAttribution.payment_id == payment.id)
    )
    if existing is not None:
        return existing
    if not payment.verified:
        raise ValueError("Solo se pueden atribuir pagos verificados")
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == payment.invoice_id,
            Invoice.client_id == payment.client_id,
        )
    )
    if invoice is None:
        raise ValueError("La factura del pago no existe en el cliente")
    contract = db.scalar(
        select(Contract).where(
            Contract.client_id == payment.client_id,
            Contract.active.is_(True),
        )
    )
    events = _management_events(db, payment)
    evidence = [
        event
        for event in events
        if event.event_type.startswith(ATTRIBUTION_EVENT_PREFIXES)
    ]
    on_time = payment.paid_on <= invoice.due_on
    category = "not_attributable"
    percentage = Decimal("0")
    rule_name = "without_eligible_management"
    if contract is not None and evidence:
        commission = (contract.rules or {}).get("commission", {})
        if on_time:
            category = "preventive_on_time"
            percentage = Decimal(str(commission.get("preventive_percent", 0)))
            rule_name = "on_time_after_preventive_management"
        else:
            category = "arrears_recovery"
            percentage = Decimal(str(commission.get("recovery_percent", 0)))
            rule_name = "late_payment_after_recovery_management"
    percentage = percentage.quantize(Decimal("0.0001"))
    base_amount = _money(Decimal(payment.amount))
    commission_amount = _money(base_amount * percentage / Decimal("100"))
    attribution = PaymentAttribution(
        client_id=payment.client_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        contract_id=contract.id if contract else None,
        category=category,
        percentage=percentage,
        base_amount=base_amount,
        commission_amount=commission_amount,
        rationale={
            "rule": rule_name,
            "paid_on": payment.paid_on.isoformat(),
            "due_on": invoice.due_on.isoformat(),
            "on_time": on_time,
            "evidence_event_ids": [str(event.id) for event in evidence],
            "evidence_event_types": sorted({event.event_type for event in evidence}),
            "contract_version": contract.version if contract else None,
        },
        calculated_by="contract_rules_v1",
    )
    db.add(attribution)
    db.flush()
    record_event(
        db,
        client_id=payment.client_id,
        invoice_id=invoice.id,
        event_type="payment.attribution_calculated",
        actor_type=ActorType.SYSTEM,
        mode="automatic",
        payload={
            "payment_id": str(payment.id),
            "attribution_id": str(attribution.id),
            "contract_id": str(contract.id) if contract else None,
            "category": category,
            "percentage": str(percentage),
            "base_amount": str(base_amount),
            "commission_amount": str(commission_amount),
            "rule": rule_name,
        },
    )
    return attribution


def _period_bounds(period: str) -> tuple[date, date, datetime, datetime]:
    try:
        year_text, month_text = period.split("-", maxsplit=1)
        year, month = int(year_text), int(month_text)
        start = date(year, month, 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("El período debe tener formato AAAA-MM") from exc
    last_day = monthrange(year, month)[1]
    end = date(year, month, last_day)
    start_at = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(end, time.max, tzinfo=timezone.utc)
    return start, end, start_at, end_at


def build_commission_report(
    db: Session, *, client_id: uuid.UUID, period: str
) -> dict[str, Any]:
    start, end, start_at, end_at = _period_bounds(period)
    payments = list(
        db.scalars(
            select(Payment)
            .where(
                Payment.client_id == client_id,
                Payment.verified.is_(True),
                Payment.paid_on >= start,
                Payment.paid_on <= end,
            )
            .order_by(Payment.paid_on, Payment.created_at)
        )
    )
    payment_ids = [payment.id for payment in payments]
    attributions = (
        list(
            db.scalars(
                select(PaymentAttribution).where(
                    PaymentAttribution.client_id == client_id,
                    PaymentAttribution.payment_id.in_(payment_ids),
                )
            )
        )
        if payment_ids
        else []
    )
    attribution_by_payment = {item.payment_id: item for item in attributions}
    invoices = {
        invoice.id: invoice
        for invoice in db.scalars(
            select(Invoice).where(
                Invoice.client_id == client_id,
                Invoice.id.in_([payment.invoice_id for payment in payments]),
            )
        )
    } if payments else {}
    details = []
    for payment in payments:
        attribution = attribution_by_payment.get(payment.id)
        invoice = invoices.get(payment.invoice_id)
        details.append(
            {
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id,
                "folio": invoice.folio if invoice else None,
                "paid_on": payment.paid_on,
                "payment_amount": Decimal(payment.amount),
                "source": payment.source,
                "category": attribution.category if attribution else "pending_attribution",
                "percentage": attribution.percentage if attribution else Decimal("0"),
                "commission_amount": (
                    attribution.commission_amount if attribution else Decimal("0")
                ),
                "contract_id": attribution.contract_id if attribution else None,
                "rationale": attribution.rationale if attribution else {},
            }
        )
    verified_amount = sum((Decimal(payment.amount) for payment in payments), Decimal("0"))
    commission_amount = sum(
        (Decimal(item.commission_amount) for item in attributions), Decimal("0")
    )
    on_time_count = sum(
        1
        for payment in payments
        if invoices.get(payment.invoice_id) and payment.paid_on <= invoices[payment.invoice_id].due_on
    )
    human_minutes = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(ExceptionCase.human_minutes), 0)).where(
                ExceptionCase.client_id == client_id,
                ExceptionCase.created_at >= start_at,
                ExceptionCase.created_at <= end_at,
            )
        )
        or 0
    )
    allocated_costs = db.execute(
        select(
            func.coalesce(func.sum(MessageInvoice.allocated_llm_cost), 0),
            func.coalesce(func.sum(MessageInvoice.allocated_messaging_cost), 0),
        ).where(
            MessageInvoice.client_id == client_id,
            MessageInvoice.created_at >= start_at,
            MessageInvoice.created_at <= end_at,
        )
    ).one()
    mode_counts = dict(
        db.execute(
            select(Message.mode, func.count(Message.id))
            .where(
                Message.client_id == client_id,
                Message.direction == "outbound",
                Message.created_at >= start_at,
                Message.created_at <= end_at,
            )
            .group_by(Message.mode)
        ).all()
    )
    managed_invoices = int(
        db.scalar(
            select(func.count(func.distinct(Event.invoice_id))).where(
                Event.client_id == client_id,
                Event.invoice_id.is_not(None),
                Event.created_at >= start_at,
                Event.created_at <= end_at,
            )
        )
        or 0
    )
    total_messages = sum(mode_counts.values())
    return {
        "client_id": client_id,
        "period": period,
        "currency": "CLP",
        "totals": {
            "verified_payments": len(payments),
            "verified_amount": _money(verified_amount),
            "attributed_payments": len(attributions),
            "unattributed_payments": len(payments) - len(attributions),
            "commission_amount": _money(commission_amount),
        },
        "metrics": {
            "managed_invoices": managed_invoices,
            "on_time_payment_percent": (
                (Decimal(on_time_count) * 100 / Decimal(len(payments))).quantize(Decimal("0.01"))
                if payments
                else None
            ),
            "human_minutes": human_minutes.quantize(Decimal("0.01")),
            "outbound_messages": total_messages,
            "automatic_message_percent": (
                (Decimal(mode_counts.get("automatic", 0)) * 100 / Decimal(total_messages)).quantize(Decimal("0.01"))
                if total_messages
                else None
            ),
            "llm_cost_usd": Decimal(allocated_costs[0]).quantize(Decimal("0.000001")),
            "messaging_cost_usd": Decimal(allocated_costs[1]).quantize(Decimal("0.000001")),
            "cost_per_managed_invoice_usd": (
                ((Decimal(allocated_costs[0]) + Decimal(allocated_costs[1])) / managed_invoices).quantize(Decimal("0.000001"))
                if managed_invoices
                else None
            ),
            "note": "Los costos externos están expresados en USD y no se restan de la comisión CLP sin un tipo de cambio auditado.",
        },
        "details": details,
        "generated_at": datetime.now(timezone.utc),
    }
