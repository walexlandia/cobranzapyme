import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.audit import record_event
from app.domain import ActorType, Role
from app.models import Event, Invoice, User
from app.schemas import EventView, InvoiceStatusUpdate, InvoiceView
from app.security import CurrentUser, require_roles
from app.services.payability import annotate_invoice_payability


router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _authorized_client(user: CurrentUser, requested: uuid.UUID | None) -> uuid.UUID:
    if user.role == Role.CLIENT:
        if user.client_id is None:
            raise HTTPException(status_code=403, detail="Usuario cliente sin empresa")
        if requested is not None and requested != user.client_id:
            raise HTTPException(status_code=403, detail="No puede acceder a otra empresa")
        return user.client_id
    if requested is None:
        raise HTTPException(status_code=422, detail="client_id es obligatorio para operadores")
    return requested


@router.get("", response_model=list[InvoiceView])
def list_invoices(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[Invoice]:
    scoped_client = _authorized_client(user, client_id)
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.client_id == scoped_client)
            .order_by(Invoice.issued_on.desc(), Invoice.folio)
        )
    )
    annotate_invoice_payability(db, invoices)
    return invoices


@router.get("/{invoice_id}/events", response_model=list[EventView])
def list_invoice_events(
    invoice_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[Event]:
    scoped_client = _authorized_client(user, client_id)
    invoice_exists = db.scalar(
        select(Invoice.id).where(
            Invoice.id == invoice_id,
            Invoice.client_id == scoped_client,
        )
    )
    if invoice_exists is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return list(
        db.scalars(
            select(Event)
            .where(Event.client_id == scoped_client, Event.invoice_id == invoice_id)
            .order_by(Event.created_at, Event.id)
            .limit(limit)
        )
    )


@router.patch("/{invoice_id}/status", response_model=InvoiceView)
def update_invoice_status(
    invoice_id: uuid.UUID,
    payload: InvoiceStatusUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    invoice = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.client_id == payload.client_id)
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    previous = invoice.status
    invoice.status = payload.status
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="invoice.status_changed",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={"from": previous.value, "to": payload.status.value},
    )
    db.commit()
    db.refresh(invoice)
    return invoice

