import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import (
    Client,
    Contact,
    Document,
    ExceptionCase,
    Invoice,
    Message,
    MessageDocument,
    MessageInvoice,
    MessageTemplate,
    User,
    WorkflowJob,
)
from app.schemas import (
    CommunicationContactView,
    CommunicationMessageView,
    ContactOptOutCommand,
    DeliveryStatusUpdate,
    ExceptionResponseDraftCreate,
    ExceptionResponseSuggestion,
    InboundMessageCreate,
    ManualResponseCreate,
    MessageTemplateCreate,
    MessageTemplateView,
)
from app.security import require_roles
from app.services.communications import (
    create_template_version,
    prepare_exception_response,
    prepare_job_message,
    register_inbound_message,
    register_manual_response,
    simulate_delivery,
    suggest_exception_response,
    update_delivery_status,
)


router = APIRouter(prefix="/api/v1/communications", tags=["communications"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _message_view(db: Session, message: Message) -> CommunicationMessageView:
    invoice_rows = db.execute(
        select(Invoice.id, Invoice.folio)
        .join(MessageInvoice, MessageInvoice.invoice_id == Invoice.id)
        .where(MessageInvoice.message_id == message.id)
        .order_by(Invoice.due_on, Invoice.folio)
    ).all()
    attachment_names = list(
        db.scalars(
            select(Document.original_name)
            .join(MessageDocument, MessageDocument.document_id == Document.id)
            .where(MessageDocument.message_id == message.id)
            .order_by(Document.original_name)
        )
    )
    contact = db.get(Contact, message.contact_id) if message.contact_id else None
    return CommunicationMessageView(
        id=message.id,
        client_id=message.client_id,
        invoice_id=message.invoice_id,
        payer_id=message.payer_id,
        contact_id=message.contact_id,
        thread_id=message.thread_id,
        template_id=message.template_id,
        workflow_job_id=message.workflow_job_id,
        channel=message.channel,
        direction=message.direction,
        mode=message.mode,
        subject=message.subject,
        body=message.body,
        status=message.status,
        provider_id=message.provider_id,
        provider_payload=message.provider_payload,
        safety_status=message.safety_status,
        safety_flags=message.safety_flags,
        llm_cost=message.llm_cost,
        messaging_cost=message.messaging_cost,
        cost_currency=message.cost_currency,
        sent_at=message.sent_at,
        received_at=message.received_at,
        created_at=message.created_at,
        invoice_ids=[row.id for row in invoice_rows],
        invoice_folios=[row.folio for row in invoice_rows],
        attachment_names=attachment_names,
        contact_name=contact.name if contact else None,
        destination=(message.provider_payload or {}).get("destination"),
    )


@router.get("/templates", response_model=list[MessageTemplateView])
def list_templates(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    active_only: bool = True,
) -> list[MessageTemplate]:
    query = select(MessageTemplate).where(MessageTemplate.client_id == client_id)
    if active_only:
        query = query.where(MessageTemplate.active.is_(True))
    return list(
        db.scalars(
            query.order_by(
                MessageTemplate.template_key,
                MessageTemplate.channel,
                MessageTemplate.version.desc(),
            )
        )
    )


@router.post("/templates", response_model=MessageTemplateView)
def create_template(
    payload: MessageTemplateCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> MessageTemplate:
    if db.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    try:
        template = create_template_version(db, payload, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(template)
    return template


@router.get("/contacts", response_model=list[CommunicationContactView])
def list_contacts(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> list[Contact]:
    return list(
        db.scalars(
            select(Contact)
            .where(Contact.client_id == client_id)
            .order_by(Contact.name)
        )
    )


@router.post("/contacts/{contact_id}/opt-out", response_model=CommunicationContactView)
def change_opt_out(
    contact_id: uuid.UUID,
    payload: ContactOptOutCommand,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Contact:
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.client_id == payload.client_id,
        )
    )
    if contact is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    field = "opted_out_email" if payload.channel == "email" else "opted_out_whatsapp"
    previous = getattr(contact, field)
    setattr(contact, field, payload.opted_out)
    record_event(
        db,
        client_id=payload.client_id,
        event_type="communication.opt_out_changed",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "contact_id": str(contact.id),
            "channel": payload.channel,
            "from": previous,
            "to": payload.opted_out,
            "reason": payload.reason,
        },
    )
    if payload.opted_out:
        message_channels = (
            ["email"] if payload.channel == "email" else ["whatsapp_assisted", "whatsapp"]
        )
        drafts = list(
            db.scalars(
                select(Message).where(
                    Message.client_id == payload.client_id,
                    Message.contact_id == contact.id,
                    Message.channel.in_(message_channels),
                    Message.status.in_({"draft", "assisted_ready"}),
                )
            )
        )
        for message in drafts:
            message.status = "blocked"
            message.safety_status = "blocked"
            message.safety_flags = list(
                dict.fromkeys([*(message.safety_flags or []), f"{payload.channel}_opt_out"])
            )
            invoice_ids = list(
                db.scalars(
                    select(MessageInvoice.invoice_id).where(
                        MessageInvoice.message_id == message.id
                    )
                )
            )
            for invoice_id in invoice_ids:
                record_event(
                    db,
                    client_id=payload.client_id,
                    invoice_id=invoice_id,
                    event_type="communication.blocked",
                    actor_type=ActorType.HUMAN,
                    actor_id=user.id,
                    payload={
                        "message_id": str(message.id),
                        "channel": message.channel,
                        "reason": f"{payload.channel}_opt_out",
                    },
                )
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/jobs/{job_id}/prepare", response_model=CommunicationMessageView)
def prepare_job(
    job_id: uuid.UUID,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> CommunicationMessageView:
    job = db.scalar(
        select(WorkflowJob).where(
            WorkflowJob.id == job_id,
            WorkflowJob.client_id == client_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    try:
        message = prepare_job_message(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)


@router.get("/messages", response_model=list[CommunicationMessageView])
def list_messages(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[str | None, Query(max_length=30)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CommunicationMessageView]:
    query = select(Message).where(Message.client_id == client_id)
    if status:
        query = query.where(Message.status == status)
    messages = list(db.scalars(query.order_by(Message.created_at.desc()).limit(limit)))
    return [_message_view(db, message) for message in messages]


@router.get(
    "/exception-responses/{exception_id}/suggestion",
    response_model=ExceptionResponseSuggestion,
)
def get_exception_response_suggestion(
    exception_id: uuid.UUID,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> dict:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == exception_id,
            ExceptionCase.client_id == client_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    try:
        return suggest_exception_response(db, case)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/exception-responses/{exception_id}/draft",
    response_model=CommunicationMessageView,
)
def create_exception_response_draft(
    exception_id: uuid.UUID,
    payload: ExceptionResponseDraftCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> CommunicationMessageView:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == exception_id,
            ExceptionCase.client_id == payload.client_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    if case.status != "open":
        raise HTTPException(status_code=409, detail="La excepción ya está resuelta")
    try:
        message = prepare_exception_response(db, case, payload, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)


@router.post("/messages/{message_id}/simulate", response_model=CommunicationMessageView)
def simulate_message(
    message_id: uuid.UUID,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> CommunicationMessageView:
    message = db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.client_id == client_id,
        )
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    try:
        simulate_delivery(db, message, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)


@router.post("/inbound/simulate", response_model=CommunicationMessageView)
def simulate_inbound_webhook(
    payload: InboundMessageCreate,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> CommunicationMessageView:
    try:
        message = register_inbound_message(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)


@router.post("/manual-responses", response_model=CommunicationMessageView)
def create_manual_response(
    payload: ManualResponseCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> CommunicationMessageView:
    try:
        message = register_manual_response(db, payload, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)


@router.post(
    "/messages/{message_id}/delivery-status",
    response_model=CommunicationMessageView,
)
def change_delivery_status(
    message_id: uuid.UUID,
    payload: DeliveryStatusUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> CommunicationMessageView:
    message = db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.client_id == payload.client_id,
        )
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    try:
        update_delivery_status(db, message, payload, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(message)
    return _message_view(db, message)
