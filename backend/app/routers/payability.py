import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import DelayCause, Invoice, PayabilityItem, PayerProfile, User
from app.routers.invoices import _authorized_client
from app.schemas import (
    DelayCauseSummary,
    DelayCauseUpdate,
    DelayCauseView,
    PayabilityChecklistView,
    PayabilityItemUpdate,
    PayabilityItemView,
    PortalEvidenceCreate,
    PreventiveConfirmationCreate,
    PayerRequirements,
)
from app.security import CurrentUser, require_roles
from app.services.payability import (
    DEFAULT_REQUIREMENTS,
    checklist_status,
    ensure_checklist,
)


router = APIRouter(prefix="/api/v1/payability", tags=["payability"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _invoice_access(
    db: Session,
    user: CurrentUser,
    invoice_id: uuid.UUID,
    client_id: uuid.UUID | None,
) -> Invoice:
    scoped_client = _authorized_client(user, client_id)
    invoice = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.client_id == scoped_client)
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


def _checklist(db: Session, invoice: Invoice) -> PayabilityChecklistView:
    items = list(
        db.scalars(
            select(PayabilityItem)
            .where(PayabilityItem.invoice_id == invoice.id)
            .order_by(PayabilityItem.blocks_payability.desc(), PayabilityItem.label)
        )
    )
    profile = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == invoice.payer_id))
    requirements = PayerRequirements.model_validate(
        profile.operational_requirements if profile else DEFAULT_REQUIREMENTS
    )
    status, completed, total, missing = checklist_status(
        invoice, items, requirements=requirements
    )
    return PayabilityChecklistView(
        invoice_id=invoice.id,
        folio=invoice.folio,
        payer_id=invoice.payer_id,
        payer_name=invoice.payer_name,
        status=status,
        completed=completed,
        total=total,
        missing_items=missing,
        items=[PayabilityItemView.model_validate(item) for item in items],
    )


@router.get("/invoices/{invoice_id}", response_model=PayabilityChecklistView)
def get_checklist(
    invoice_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> PayabilityChecklistView:
    return _checklist(db, _invoice_access(db, user, invoice_id, client_id))


@router.post("/invoices/{invoice_id}/initialize", response_model=PayabilityChecklistView)
def initialize_checklist(
    invoice_id: uuid.UUID,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> PayabilityChecklistView:
    invoice = _invoice_access(db, user, invoice_id, client_id)
    ensure_checklist(db, invoice, actor_type=ActorType.HUMAN, actor_id=user.id)
    db.commit()
    return _checklist(db, invoice)


@router.patch("/items/{item_id}", response_model=PayabilityItemView)
def update_item(
    item_id: uuid.UUID,
    payload: PayabilityItemUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PayabilityItem:
    item = db.get(PayabilityItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Requisito no encontrado")
    previous = {"status": item.status, "evidence": item.evidence}
    item.status = payload.status
    item.evidence = payload.evidence
    record_event(
        db,
        client_id=item.client_id,
        invoice_id=item.invoice_id,
        event_type="payability.item_changed",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "item_id": str(item.id),
            "item_type": item.item_type,
            "from": previous,
            "to": {"status": item.status, "evidence": item.evidence},
        },
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/invoices/{invoice_id}/portal", response_model=PayabilityItemView)
def register_portal_evidence(
    invoice_id: uuid.UUID,
    payload: PortalEvidenceCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> PayabilityItem:
    invoice = _invoice_access(db, user, invoice_id, client_id)
    ensure_checklist(db, invoice, actor_type=ActorType.HUMAN, actor_id=user.id)
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.invoice_id == invoice.id,
            PayabilityItem.item_type == "supplier_portal",
        )
    )
    assert item is not None
    previous = {"status": item.status, "evidence": item.evidence}
    item.status = "fulfilled"
    item.evidence = {
        "entry_number": payload.entry_number,
        "uploaded_at": payload.uploaded_at.isoformat(),
        "evidence_reference": payload.evidence_reference,
    }
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="payability.portal_registered",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={"item_id": str(item.id), "from": previous, "to": item.evidence},
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/invoices/{invoice_id}/preventive-confirmation", response_model=PayabilityChecklistView)
def register_preventive_confirmation(
    invoice_id: uuid.UUID,
    payload: PreventiveConfirmationCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> PayabilityChecklistView:
    invoice = _invoice_access(db, user, invoice_id, client_id)
    ensure_checklist(db, invoice, actor_type=ActorType.HUMAN, actor_id=user.id)
    items = {
        item.item_type: item
        for item in db.scalars(
            select(PayabilityItem).where(
                PayabilityItem.invoice_id == invoice.id,
                PayabilityItem.item_type.in_({"payment_approval", "payment_scheduled"}),
            )
        )
    }
    evidence = {
        "approval_status": payload.approval_status,
        "approved_at": payload.approved_at.isoformat(),
        "scheduled_payment_date": (
            payload.scheduled_payment_date.isoformat()
            if payload.scheduled_payment_date
            else None
        ),
        "reference": payload.reference,
    }
    changes = {
        "payment_approval": "fulfilled" if payload.approval_status == "approved" else "blocked",
        "payment_scheduled": "fulfilled" if payload.scheduled_payment_date else "pending",
    }
    for item_type, status in changes.items():
        item = items[item_type]
        previous = {"status": item.status, "evidence": item.evidence}
        item.status = status
        item.evidence = evidence
        record_event(
            db,
            client_id=invoice.client_id,
            invoice_id=invoice.id,
            event_type="payability.preventive_confirmation_changed",
            actor_type=ActorType.HUMAN,
            actor_id=user.id,
            payload={
                "item_id": str(item.id),
                "item_type": item.item_type,
                "from": previous,
                "to": {"status": item.status, "evidence": evidence},
            },
        )
    db.commit()
    return _checklist(db, invoice)


@router.put("/invoices/{invoice_id}/delay-cause", response_model=DelayCauseView)
def set_delay_cause(
    invoice_id: uuid.UUID,
    payload: DelayCauseUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> DelayCause:
    invoice = _invoice_access(db, user, invoice_id, client_id)
    cause = db.scalar(select(DelayCause).where(DelayCause.invoice_id == invoice.id))
    previous = None
    if cause is None:
        cause = DelayCause(client_id=invoice.client_id, invoice_id=invoice.id)
        db.add(cause)
    else:
        previous = {"category": cause.category, "detail": cause.detail}
    cause.category = payload.category
    cause.detail = payload.detail
    cause.source = "manual"
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="delay_cause.changed",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "from": previous,
            "to": {"category": cause.category, "detail": cause.detail},
        },
    )
    db.commit()
    db.refresh(cause)
    return cause


@router.get("/delay-causes", response_model=list[DelayCauseSummary])
def delay_cause_summary(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[DelayCauseSummary]:
    scoped_client = _authorized_client(user, client_id)
    rows = db.execute(
        select(
            DelayCause.category,
            func.count(DelayCause.id),
            func.coalesce(func.sum(Invoice.total_amount), 0),
        )
        .join(Invoice, Invoice.id == DelayCause.invoice_id)
        .where(DelayCause.client_id == scoped_client)
        .group_by(DelayCause.category)
        .order_by(func.sum(Invoice.total_amount).desc())
    ).all()
    return [
        DelayCauseSummary(
            category=category,
            invoice_count=count,
            total_amount=Decimal(amount),
        )
        for category, count, amount in rows
    ]
