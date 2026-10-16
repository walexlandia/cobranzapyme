import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import InvoiceStatus
from app.models import Client, Invoice, PayabilityItem, Payment, PayerProfile
from app.schemas import PayerRequirements
from app.services.payability import DEFAULT_REQUIREMENTS, checklist_status


COMPLETED_ITEM_STATUSES = {"fulfilled", "not_applicable"}


def _money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def build_client_portal_summary(
    db: Session,
    *,
    client: Client,
    as_of: date,
) -> dict:
    invoices = list(
        db.scalars(
            select(Invoice)
            .options(selectinload(Invoice.payer))
            .where(
                Invoice.client_id == client.id,
                Invoice.issued_on <= as_of,
                Invoice.status != InvoiceStatus.VOID,
            )
            .order_by(Invoice.due_on, Invoice.folio)
        )
    )
    invoice_ids = [invoice.id for invoice in invoices]
    items_by_invoice: dict[uuid.UUID, list[PayabilityItem]] = defaultdict(list)
    paid_by_invoice: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    if invoice_ids:
        for item in db.scalars(
            select(PayabilityItem).where(PayabilityItem.invoice_id.in_(invoice_ids))
        ):
            items_by_invoice[item.invoice_id].append(item)
        for payment in db.scalars(
            select(Payment).where(
                Payment.invoice_id.in_(invoice_ids),
                Payment.verified.is_(True),
                Payment.paid_on <= as_of,
            )
        ):
            paid_by_invoice[payment.invoice_id] += Decimal(payment.amount)

    profile_requirements: dict[uuid.UUID, PayerRequirements] = {}
    profiles = {
        profile.payer_id: profile
        for profile in db.scalars(
            select(PayerProfile).where(
                PayerProfile.payer_id.in_({invoice.payer_id for invoice in invoices})
            )
        )
    }
    details = []
    totals = {
        "invoice_count": len(invoices),
        "managed_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "payable_count": 0,
        "at_risk_count": 0,
        "paid_count": 0,
        "pending_client_count": 0,
        "dispute_count": 0,
    }
    for invoice in invoices:
        profile = profiles.get(invoice.payer_id)
        if invoice.payer_id not in profile_requirements:
            profile_requirements[invoice.payer_id] = PayerRequirements.model_validate(
                profile.operational_requirements if profile else DEFAULT_REQUIREMENTS
            )
        items = items_by_invoice[invoice.id]
        payability, completed, total, missing = checklist_status(
            invoice,
            items,
            requirements=profile_requirements[invoice.payer_id],
            today=as_of,
        )
        paid_amount = min(_money(paid_by_invoice[invoice.id]), _money(invoice.total_amount))
        outstanding_amount = max(_money(invoice.total_amount) - paid_amount, Decimal("0"))
        pending_client_items = [
            item.label
            for item in items
            if item.required
            and item.responsible_role == "client"
            and item.status not in COMPLETED_ITEM_STATUSES
        ]
        is_paid = invoice.status == InvoiceStatus.PAID or outstanding_amount == 0
        is_dispute = invoice.status in {InvoiceStatus.CLAIMED, InvoiceStatus.DISPUTED} or payability == "claimed"
        is_at_risk = payability in {"at_risk", "claimed"} and not is_paid
        totals["managed_amount"] += _money(invoice.total_amount)
        totals["paid_amount"] += paid_amount
        totals["outstanding_amount"] += outstanding_amount
        totals["payable_count"] += int(payability == "payable" and not is_paid)
        totals["at_risk_count"] += int(is_at_risk)
        totals["paid_count"] += int(is_paid)
        totals["pending_client_count"] += int(bool(pending_client_items) and not is_paid)
        totals["dispute_count"] += int(is_dispute and not is_paid)
        details.append(
            {
                "id": invoice.id,
                "folio": invoice.folio,
                "payer_name": invoice.payer_name,
                "issued_on": invoice.issued_on,
                "due_on": invoice.due_on,
                "currency": invoice.currency,
                "total_amount": _money(invoice.total_amount),
                "paid_amount": paid_amount,
                "outstanding_amount": outstanding_amount,
                "status": invoice.status.value,
                "payability_status": payability,
                "checklist_completed": completed,
                "checklist_total": total,
                "missing_items": missing,
                "pending_client_items": pending_client_items,
            }
        )
    for key in ("managed_amount", "paid_amount", "outstanding_amount"):
        totals[key] = _money(totals[key])
    return {
        "client_id": client.id,
        "client_name": client.name,
        "as_of": as_of,
        "totals": totals,
        "invoices": details,
    }


def build_weekly_report(
    db: Session,
    *,
    client: Client,
    week_ending: date,
) -> dict:
    period_start = week_ending - timedelta(days=6)
    summary = build_client_portal_summary(db, client=client, as_of=week_ending)
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.client_id == client.id,
                Payment.verified.is_(True),
                Payment.paid_on >= period_start,
                Payment.paid_on <= week_ending,
            )
        )
    )
    return {
        "client_id": client.id,
        "client_name": client.name,
        "period_start": period_start,
        "period_end": week_ending,
        "generated_at": datetime.now(timezone.utc),
        "payments_this_week_count": len(payments),
        "payments_this_week_amount": _money(
            sum((Decimal(payment.amount) for payment in payments), Decimal("0"))
        ),
        "summary": summary,
    }
