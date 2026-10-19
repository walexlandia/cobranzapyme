from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Client,
    Contract,
    ExceptionCase,
    Invoice,
    Message,
    PayabilityItem,
    Payment,
    PilotLogEntry,
)


def build_demo_walkthrough(
    db: Session,
    *,
    client: Client,
    operation_date: date,
) -> dict[str, Any]:
    """Build a read-only, date-controlled demo checklist from persisted evidence."""
    end_at = datetime.combine(operation_date, time.max, tzinfo=timezone.utc)
    active_contract = db.scalar(
        select(Contract.id).where(
            Contract.client_id == client.id,
            Contract.active.is_(True),
        )
    )
    invoice_ids = list(
        db.scalars(
            select(Invoice.id).where(
                Invoice.client_id == client.id,
                Invoice.issued_on <= operation_date,
            )
        )
    )
    checklist_invoice_count = (
        int(
            db.scalar(
                select(func.count(func.distinct(PayabilityItem.invoice_id))).where(
                    PayabilityItem.client_id == client.id,
                    PayabilityItem.invoice_id.in_(invoice_ids),
                    PayabilityItem.created_at <= end_at,
                )
            )
            or 0
        )
        if invoice_ids
        else 0
    )
    message_count = int(
        db.scalar(
            select(func.count(Message.id)).where(
                Message.client_id == client.id,
                Message.created_at <= end_at,
            )
        )
        or 0
    )
    exception_count = int(
        db.scalar(
            select(func.count(ExceptionCase.id)).where(
                ExceptionCase.client_id == client.id,
                ExceptionCase.created_at <= end_at,
            )
        )
        or 0
    )
    payment_count = int(
        db.scalar(
            select(func.count(Payment.id)).where(
                Payment.client_id == client.id,
                Payment.verified.is_(True),
                Payment.paid_on <= operation_date,
            )
        )
        or 0
    )
    log_count = int(
        db.scalar(
            select(func.count(PilotLogEntry.id)).where(
                PilotLogEntry.client_id == client.id,
                PilotLogEntry.occurred_on <= operation_date,
            )
        )
        or 0
    )
    steps = [
        {
            "key": "onboarding",
            "label": "Cliente, contrato y cartera",
            "ready": active_contract is not None and bool(invoice_ids),
            "evidence": {
                "active_contract": active_contract is not None,
                "invoice_count": len(invoice_ids),
            },
            "target_view": "contract",
        },
        {
            "key": "payability",
            "label": "Checklist de pagabilidad",
            "ready": bool(invoice_ids) and checklist_invoice_count == len(invoice_ids),
            "evidence": {
                "invoices_with_checklist": checklist_invoice_count,
                "invoice_count": len(invoice_ids),
            },
            "target_view": "payability",
        },
        {
            "key": "communications",
            "label": "Comunicación trazable",
            "ready": message_count > 0,
            "evidence": {"message_count": message_count},
            "target_view": "communications",
        },
        {
            "key": "supervision",
            "label": "Excepción y revisión humana",
            "ready": exception_count > 0,
            "evidence": {"exception_count": exception_count},
            "target_view": "exceptions",
        },
        {
            "key": "payment",
            "label": "Pago verificado",
            "ready": payment_count > 0,
            "evidence": {"verified_payment_count": payment_count},
            "target_view": "payments",
        },
        {
            "key": "measurement",
            "label": "Métricas y aprendizaje",
            "ready": payment_count > 0 and log_count > 0,
            "evidence": {
                "verified_payment_count": payment_count,
                "pilot_log_count": log_count,
                "baseline_available": (
                    client.baseline_dso is not None
                    and client.baseline_on_time_percent is not None
                ),
            },
            "target_view": "metrics",
        },
    ]
    return {
        "client_id": client.id,
        "client_name": client.name,
        "operation_date": operation_date,
        "ready_steps": sum(step["ready"] for step in steps),
        "total_steps": len(steps),
        "steps": steps,
        "generated_at": datetime.now(timezone.utc),
    }
