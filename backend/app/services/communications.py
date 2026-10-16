import hashlib
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from string import Formatter
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType
from app.models import (
    Client,
    CommunicationThread,
    Contact,
    Contract,
    Document,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    MessageDocument,
    MessageInvoice,
    MessageTemplate,
    WorkflowJob,
)
from app.schemas import (
    ContractRules,
    DeliveryStatusUpdate,
    ExceptionResponseDraftCreate,
    InboundMessageCreate,
    ManualResponseCreate,
    MessageTemplateCreate,
)
from app.services.classification import classify_message


ALLOWED_TEMPLATE_FIELDS = {
    "recipient_name",
    "client_name",
    "sender_name",
    "payer_name",
    "invoice_summary",
    "action_request",
    "missing_items_section",
    "bank_details_section",
}

FORBIDDEN_PATTERNS = {
    "threat": re.compile(r"\b(amenaz|embarg|bolet[ií]n comercial)\w*", re.IGNORECASE),
    "legal_pressure": re.compile(r"\b(demanda|acci[oó]n judicial|querella)\w*", re.IGNORECASE),
    "unauthorized_promise": re.compile(
        r"\b(garantizamos|aseguramos el pago|condonaremos|perdonaremos)\b", re.IGNORECASE
    ),
}

PAYMENT_ACTIONS = {
    "confirm_payment_schedule",
    "request_payment_confirmation",
    "follow_up_overdue",
    "escalate_collection",
    "payment_due",
    "early_arrears_contact",
    "escalate_case",
}

ACTION_REQUESTS = {
    "verify_intake": "Agradecemos confirmar la recepción y correcta contabilización de las facturas indicadas.",
    "confirm_invoice_receipt": "Agradecemos confirmar la recepción y correcta contabilización de las facturas indicadas.",
    "resolve_payability": "Agradecemos indicar si existe algún requisito pendiente para que estas facturas queden pagables.",
    "request_client_document": "Se requiere completar la documentación indicada para continuar el proceso de pago.",
    "request_missing_requirement": "Agradecemos apoyar con el requisito pendiente indicado para continuar el proceso de pago.",
    "confirm_payment_schedule": "Agradecemos confirmar si las facturas están aprobadas y la fecha programada de pago.",
    "request_payment_confirmation": "Agradecemos confirmar el estado y la fecha estimada de pago de las facturas.",
    "follow_up_overdue": "Las facturas indicadas figuran vencidas; agradeceremos informar su estado y fecha prevista de pago.",
    "escalate_collection": "Solicitamos una actualización formal del estado de las facturas y del responsable de resolución.",
    "payment_due": "Agradecemos confirmar el estado y la fecha estimada de pago de las facturas.",
    "early_arrears_contact": "Las facturas indicadas figuran vencidas; agradeceremos informar su estado y fecha prevista de pago.",
    "escalate_case": "Solicitamos una actualización formal del estado de las facturas y del responsable de resolución.",
}

DEFAULT_SUBJECT = "Seguimiento de facturas · {client_name} · {payer_name}"
DEFAULT_BODY = """Hola {recipient_name}:

Escribimos en representación de {client_name} respecto de {invoice_summary}.

{action_request}{missing_items_section}{bank_details_section}

Si esta información ya fue resuelta, agradeceremos indicarlo para actualizar el registro.

Saludos,
{sender_name}"""

FALLBACK_BODY = """Hola {recipient_name}:

Escribimos en representación de {client_name} para solicitar una actualización sobre {invoice_summary}.

Por favor, responde indicando el estado actual o el contacto correcto para continuar.

Saludos,
{sender_name}"""


def validate_template_text(subject: str | None, body: str) -> None:
    for label, value in (("asunto", subject or ""), ("cuerpo", body)):
        try:
            fields = {
                field_name
                for _, field_name, _, _ in Formatter().parse(value)
                if field_name is not None
            }
        except ValueError as exc:
            raise ValueError(f"Formato inválido en {label}: {exc}") from exc
        unknown = fields - ALLOWED_TEMPLATE_FIELDS
        if unknown:
            raise ValueError(
                f"Campos no permitidos en {label}: {', '.join(sorted(unknown))}"
            )


def safety_flags(subject: str | None, body: str) -> list[str]:
    content = f"{subject or ''}\n{body}"
    return [code for code, pattern in FORBIDDEN_PATTERNS.items() if pattern.search(content)]


def create_template_version(
    db: Session,
    payload: MessageTemplateCreate,
    *,
    actor_id: uuid.UUID | None,
    actor_type: ActorType = ActorType.HUMAN,
) -> MessageTemplate:
    validate_template_text(payload.subject_template, payload.body_template)
    active_templates = list(
        db.scalars(
            select(MessageTemplate).where(
                MessageTemplate.client_id == payload.client_id,
                MessageTemplate.template_key == payload.template_key,
                MessageTemplate.channel == payload.channel,
                MessageTemplate.active.is_(True),
            )
        )
    )
    for current in active_templates:
        current.active = False
    if active_templates:
        db.flush()
    version = int(
        db.scalar(
            select(func.coalesce(func.max(MessageTemplate.version), 0)).where(
                MessageTemplate.client_id == payload.client_id,
                MessageTemplate.template_key == payload.template_key,
                MessageTemplate.channel == payload.channel,
            )
        )
        or 0
    ) + 1
    template = MessageTemplate(
        client_id=payload.client_id,
        template_key=payload.template_key,
        version=version,
        channel=payload.channel,
        stage=payload.stage,
        recipient_role=payload.recipient_role,
        tone=payload.tone,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
        approved=payload.approved,
        active=True,
    )
    db.add(template)
    db.flush()
    record_event(
        db,
        client_id=payload.client_id,
        event_type="communication.template_version_created",
        actor_type=actor_type,
        actor_id=actor_id,
        payload={
            "template_id": str(template.id),
            "template_key": template.template_key,
            "channel": template.channel,
            "version": template.version,
            "approved": template.approved,
        },
    )
    return template


def _default_template(
    db: Session,
    *,
    client_id: uuid.UUID,
    job: WorkflowJob,
    channel: str,
) -> MessageTemplate:
    template = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.client_id == client_id,
            MessageTemplate.template_key == job.action_type,
            MessageTemplate.channel == channel,
            MessageTemplate.active.is_(True),
        )
    )
    if template is not None:
        return template
    payload = MessageTemplateCreate(
        client_id=client_id,
        template_key=job.action_type,
        channel=channel,
        stage=job.stage,
        recipient_role=job.payload.get("recipient_role", "accounts_payable"),
        tone="cordial",
        subject_template=DEFAULT_SUBJECT if channel == "email" else None,
        body_template=DEFAULT_BODY,
        approved=False,
    )
    return create_template_version(
        db, payload, actor_id=None, actor_type=ActorType.SYSTEM
    )


def _format_amount(invoice: Invoice) -> str:
    amount = f"{int(invoice.total_amount):,}".replace(",", ".")
    return f"{invoice.currency} ${amount}"


def _invoice_summary(invoices: list[Invoice]) -> str:
    entries = [
        f"factura {invoice.folio}, vencimiento {invoice.due_on.isoformat()}, {_format_amount(invoice)}"
        for invoice in invoices
    ]
    return "; ".join(entries)


def _bank_details(details: dict) -> str:
    labels = {
        "bank": "Banco",
        "account_type": "Tipo de cuenta",
        "account_number": "Número de cuenta",
        "account_holder": "Titular",
        "rut": "RUT",
        "email": "Correo de confirmación",
    }
    rows = [f"{label}: {details[key]}" for key, label in labels.items() if details.get(key)]
    return "\n".join(rows)


def _select_channel(
    rules: ContractRules, contact: Contact | None
) -> tuple[str, str | None, list[str]]:
    flags: list[str] = []
    if contact is None:
        return rules.channels[0], None, ["missing_contact"]
    for channel in rules.channels:
        if channel == "email":
            if contact.opted_out_email:
                flags.append("email_opt_out")
            elif contact.email:
                return channel, contact.email, flags
            else:
                flags.append("missing_email")
        elif channel == "whatsapp_assisted":
            if contact.opted_out_whatsapp:
                flags.append("whatsapp_opt_out")
            elif contact.phone:
                return channel, contact.phone, flags
            else:
                flags.append("missing_phone")
    return rules.channels[0], None, flags or ["no_eligible_channel"]


def _get_or_create_thread(
    db: Session,
    *,
    client_id: uuid.UUID,
    payer_id: uuid.UUID,
    contact_id: uuid.UUID,
    channel: str,
) -> CommunicationThread:
    thread = db.scalar(
        select(CommunicationThread).where(
            CommunicationThread.client_id == client_id,
            CommunicationThread.payer_id == payer_id,
            CommunicationThread.contact_id == contact_id,
            CommunicationThread.channel == channel,
            CommunicationThread.status == "open",
        )
    )
    if thread is None:
        thread = CommunicationThread(
            client_id=client_id,
            payer_id=payer_id,
            contact_id=contact_id,
            channel=channel,
            status="open",
        )
        db.add(thread)
        db.flush()
    return thread


def prepare_job_message(db: Session, job: WorkflowJob) -> Message:
    idempotency_key = f"workflow:{job.id}:outbound:v1"
    existing = db.scalar(
        select(Message).where(Message.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    client = db.get(Client, job.client_id)
    contract = db.get(Contract, job.contract_id)
    if client is None or contract is None:
        raise ValueError("El trabajo no tiene cliente o contrato vigente")
    rules = ContractRules.model_validate(contract.rules)
    raw_invoice_ids = job.payload.get("invoice_ids", [str(job.invoice_id)])
    invoice_ids: list[uuid.UUID] = []
    for value in raw_invoice_ids:
        try:
            invoice_ids.append(uuid.UUID(str(value)))
        except ValueError:
            continue
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.client_id == job.client_id, Invoice.id.in_(invoice_ids))
            .order_by(Invoice.due_on, Invoice.folio)
        )
    )
    if not invoices:
        raise ValueError("El trabajo no contiene facturas válidas del cliente")
    contact = db.get(Contact, job.recipient_contact_id) if job.recipient_contact_id else None
    if contact is not None and contact.client_id != job.client_id:
        contact = None
    channel, destination, channel_flags = _select_channel(rules, contact)
    template = _default_template(db, client_id=client.id, job=job, channel=channel)

    missing_map = job.payload.get("missing_items", {})
    missing = sorted(
        {
            str(label)
            for values in missing_map.values()
            if isinstance(values, list)
            for label in values
        }
    )
    bank_details = _bank_details(client.bank_details or {})
    bank_section = ""
    if job.action_type in PAYMENT_ACTIONS:
        bank_section = (
            f"\n\nDatos de transferencia informados por {client.name}:\n{bank_details}"
            if bank_details
            else ""
        )
    context = {
        "recipient_name": contact.name if contact else "equipo responsable",
        "client_name": client.name,
        "sender_name": client.sender_name or client.name,
        "payer_name": invoices[0].payer_name,
        "invoice_summary": _invoice_summary(invoices),
        "action_request": ACTION_REQUESTS.get(
            job.action_type,
            "Agradecemos informar el estado actual de las facturas indicadas.",
        ),
        "missing_items_section": (
            f"\n\nRequisitos pendientes: {', '.join(missing)}." if missing else ""
        ),
        "bank_details_section": bank_section,
    }
    validate_template_text(template.subject_template, template.body_template)
    subject = template.subject_template.format_map(context) if template.subject_template else None
    body = template.body_template.format_map(context)
    content_flags = safety_flags(subject, body)
    safety_status = "safe"
    if content_flags:
        subject = DEFAULT_SUBJECT.format_map(context) if channel == "email" else None
        body = FALLBACK_BODY.format_map(context)
        safety_status = "fallback"

    blocked_flags = list(dict.fromkeys(channel_flags))
    if channel == "email" and not client.sender_email:
        blocked_flags.append("missing_sender_email")
    if destination is None:
        blocked_flags.append("missing_destination")
    status = "blocked" if blocked_flags else (
        "assisted_ready" if channel == "whatsapp_assisted" else "draft"
    )
    thread = None
    if contact is not None and destination is not None:
        thread = _get_or_create_thread(
            db,
            client_id=client.id,
            payer_id=invoices[0].payer_id,
            contact_id=contact.id,
            channel=channel,
        )
    provider_payload = {
        "provider": "local_simulator",
        "external_delivery": False,
        "destination": destination,
        "sender_name": client.sender_name or client.name,
        "sender_email": client.sender_email,
    }
    if channel == "whatsapp_assisted" and destination:
        digits = re.sub(r"\D", "", destination)
        provider_payload["assisted_link"] = f"https://wa.me/{digits}?text={quote(body)}"

    message = Message(
        client_id=client.id,
        invoice_id=invoices[0].id,
        payer_id=invoices[0].payer_id,
        contact_id=contact.id if contact else None,
        thread_id=thread.id if thread else None,
        template_id=template.id,
        workflow_job_id=job.id,
        channel=channel,
        direction="outbound",
        mode=job.mode,
        subject=subject,
        body=body,
        status=status,
        idempotency_key=idempotency_key,
        provider_payload=provider_payload,
        safety_status=safety_status if not blocked_flags else "blocked",
        safety_flags=list(dict.fromkeys(content_flags + blocked_flags)),
        llm_cost=Decimal("0"),
        messaging_cost=Decimal("0"),
        cost_currency="USD",
    )
    db.add(message)
    db.flush()

    for invoice in invoices:
        db.add(
            MessageInvoice(
                client_id=client.id,
                message_id=message.id,
                invoice_id=invoice.id,
                allocated_llm_cost=Decimal("0"),
                allocated_messaging_cost=Decimal("0"),
            )
        )
    documents = list(
        db.scalars(
            select(Document).where(
                Document.client_id == client.id,
                Document.invoice_id.in_([invoice.id for invoice in invoices]),
            )
        )
    )
    for document in documents:
        db.add(
            MessageDocument(
                client_id=client.id,
                message_id=message.id,
                document_id=document.id,
            )
        )
    event_type = "communication.blocked" if status == "blocked" else "communication.draft_created"
    for invoice in invoices:
        record_event(
            db,
            client_id=client.id,
            invoice_id=invoice.id,
            event_type=event_type,
            actor_type=ActorType.SYSTEM,
            mode=job.mode,
            payload={
                "message_id": str(message.id),
                "workflow_job_id": str(job.id),
                "channel": channel,
                "status": status,
                "template_id": str(template.id),
                "template_version": template.version,
                "safety_status": message.safety_status,
                "safety_flags": message.safety_flags,
                "external_delivery": False,
            },
        )
    return message


def suggest_exception_response(db: Session, case: ExceptionCase) -> dict:
    source = db.get(Message, case.message_id) if case.message_id else None
    invoice = db.get(Invoice, case.invoice_id) if case.invoice_id else None
    client = db.get(Client, case.client_id)
    classification = (
        db.get(MessageClassification, case.classification_id)
        if case.classification_id
        else None
    )
    contact = db.get(Contact, source.contact_id) if source and source.contact_id else None
    if invoice is None or client is None or source is None:
        raise ValueError("La excepción no tiene contexto suficiente para preparar una respuesta")
    if source.channel == "whatsapp":
        channel = "whatsapp_assisted"
    elif source.channel == "email":
        channel = "email"
    elif contact and contact.email:
        channel = "email"
    else:
        channel = "whatsapp_assisted"
    category = classification.category if classification else "other"
    extracted = classification.extracted_data if classification else {}
    dates = extracted.get("payment_dates", []) if isinstance(extracted, dict) else []
    category_text = {
        "paid": "Gracias por informarnos. Para actualizar el registro, agradeceremos adjuntar el comprobante de pago si aún no fue enviado.",
        "payment_scheduled": (
            f"Gracias por confirmar la programación de pago para {dates[0]}. Conservaremos el caso en seguimiento hasta contar con la confirmación del pago."
            if dates
            else "Gracias por confirmar la programación. Agradeceremos indicar la fecha de pago para actualizar el seguimiento."
        ),
        "missing_oc_hes": "Gracias por indicar el requisito pendiente. Lo revisaremos con la pyme antes de continuar la gestión.",
        "supplier_data_issue": "Gracias por la observación. Los datos del proveedor serán revisados con la pyme antes de cualquier actualización.",
        "invoice_disputed": "Gracias por informar el reclamo. El caso quedó pausado y será revisado por una persona antes de continuar.",
        "payment_promise": (
            f"Gracias por el compromiso informado para {dates[0]}. Mantendremos el seguimiento hasta verificar el pago."
            if dates
            else "Gracias por el compromiso informado. Agradeceremos confirmar la fecha prevista de pago."
        ),
        "dispute": "Gracias por detallar la discrepancia. El caso quedó pausado para revisión humana y no se continuará la gestión hasta aclararlo.",
        "document_request": "Gracias por indicar el documento requerido. Revisaremos su disponibilidad con la pyme antes de responder.",
        "wrong_contact": "Gracias por avisarnos. Dejaremos este contacto fuera de la gestión de este caso; si es posible, agradeceremos indicar el canal correcto.",
        "other": "Gracias por su respuesta. La información quedó registrada y será revisada por una persona antes de continuar.",
    }.get(category, "Gracias por su respuesta. La información será revisada antes de continuar.")
    greeting = contact.name if contact else "equipo responsable"
    body = (
        f"Hola {greeting}:\n\n"
        f"Respecto de la factura {invoice.folio} de {client.name}, {category_text}\n\n"
        "Saludos,\n"
        f"{client.sender_name or client.name}"
    )
    return {
        "exception_id": case.id,
        "channel": channel,
        "subject": f"Respuesta sobre factura {invoice.folio}" if channel == "email" else None,
        "body": body,
        "requires_human_review": True,
        "external_delivery": False,
    }


def prepare_exception_response(
    db: Session,
    case: ExceptionCase,
    payload: ExceptionResponseDraftCreate,
    *,
    actor_id: uuid.UUID,
) -> Message:
    idempotency_key = f"exception:{case.id}:response:v1"
    existing = db.scalar(select(Message).where(Message.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    source = db.get(Message, case.message_id) if case.message_id else None
    invoice = db.get(Invoice, case.invoice_id) if case.invoice_id else None
    client = db.get(Client, case.client_id)
    if source is None or invoice is None or client is None:
        raise ValueError("La excepción no tiene contexto suficiente para preparar una respuesta")
    contact = db.get(Contact, source.contact_id) if source.contact_id else None
    if contact is not None and contact.client_id != case.client_id:
        contact = None
    content_flags = safety_flags(payload.subject, payload.body)
    suggestion = suggest_exception_response(db, case)
    subject = payload.subject if payload.channel == "email" else None
    body = payload.body
    safety_status = "safe"
    if content_flags:
        subject = suggestion["subject"] if payload.channel == "email" else None
        body = suggestion["body"]
        safety_status = "fallback"
    blocked_flags: list[str] = []
    destination = None
    if contact is None:
        blocked_flags.append("missing_contact")
    elif payload.channel == "email":
        if contact.opted_out_email:
            blocked_flags.append("email_opt_out")
        elif contact.email:
            destination = contact.email
        else:
            blocked_flags.append("missing_email")
    else:
        if contact.opted_out_whatsapp:
            blocked_flags.append("whatsapp_opt_out")
        elif contact.phone:
            destination = contact.phone
        else:
            blocked_flags.append("missing_phone")
    if payload.channel == "email" and not client.sender_email:
        blocked_flags.append("missing_sender_email")
    status = "blocked" if blocked_flags else (
        "assisted_ready" if payload.channel == "whatsapp_assisted" else "draft"
    )
    thread = None
    if contact is not None and destination is not None:
        thread = _get_or_create_thread(
            db,
            client_id=case.client_id,
            payer_id=invoice.payer_id,
            contact_id=contact.id,
            channel=payload.channel,
        )
    provider_payload = {
        "provider": "local_simulator",
        "external_delivery": False,
        "destination": destination,
        "sender_name": client.sender_name or client.name,
        "sender_email": client.sender_email,
        "exception_id": str(case.id),
        "source_message_id": str(source.id),
        "requires_human_review": True,
    }
    if payload.channel == "whatsapp_assisted" and destination:
        digits = re.sub(r"\D", "", destination)
        provider_payload["assisted_link"] = f"https://wa.me/{digits}?text={quote(body)}"
    message = Message(
        client_id=case.client_id,
        invoice_id=invoice.id,
        payer_id=invoice.payer_id,
        contact_id=contact.id if contact else None,
        thread_id=thread.id if thread else None,
        channel=payload.channel,
        direction="outbound",
        mode="manual",
        subject=subject,
        body=body,
        status=status,
        idempotency_key=idempotency_key,
        provider_payload=provider_payload,
        safety_status="blocked" if blocked_flags else safety_status,
        safety_flags=list(dict.fromkeys([*content_flags, *blocked_flags])),
        llm_cost=Decimal("0"),
        messaging_cost=Decimal("0"),
        cost_currency="USD",
    )
    db.add(message)
    db.flush()
    db.add(
        MessageInvoice(
            client_id=case.client_id,
            message_id=message.id,
            invoice_id=invoice.id,
            allocated_llm_cost=Decimal("0"),
            allocated_messaging_cost=Decimal("0"),
        )
    )
    record_event(
        db,
        client_id=case.client_id,
        invoice_id=invoice.id,
        event_type=(
            "communication.blocked" if status == "blocked" else "exception.response_draft_created"
        ),
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="manual",
        payload={
            "exception_id": str(case.id),
            "source_message_id": str(source.id),
            "message_id": str(message.id),
            "channel": payload.channel,
            "status": status,
            "safety_status": message.safety_status,
            "safety_flags": message.safety_flags,
            "external_delivery": False,
            "requires_human_review": True,
        },
    )
    return message


def simulate_delivery(
    db: Session,
    message: Message,
    *,
    actor_id: uuid.UUID | None,
) -> Message:
    if message.status == "blocked":
        raise ValueError("El mensaje está bloqueado por reglas de canal o seguridad")
    if message.status == "simulated":
        return message
    if message.status not in {"draft", "assisted_ready"}:
        raise ValueError("El mensaje no está listo para simulación")
    message.status = "simulated"
    message.sent_at = datetime.now(timezone.utc)
    message.provider_id = f"local-sim-{message.id}"
    message.messaging_cost = (
        Decimal("0.001000") if message.channel == "email" else Decimal("0")
    )
    message.provider_payload = {
        **(message.provider_payload or {}),
        "simulated_at": message.sent_at.isoformat(),
        "external_delivery": False,
    }
    links = list(
        db.scalars(select(MessageInvoice).where(MessageInvoice.message_id == message.id))
    )
    if links:
        share = (message.messaging_cost / len(links)).quantize(Decimal("0.000001"))
        allocated = Decimal("0")
        for index, link in enumerate(links):
            link.allocated_llm_cost = Decimal("0")
            link.allocated_messaging_cost = (
                message.messaging_cost - allocated if index == len(links) - 1 else share
            )
            allocated += link.allocated_messaging_cost
            record_event(
                db,
                client_id=message.client_id,
                invoice_id=link.invoice_id,
                event_type="communication.simulated",
                actor_type=ActorType.HUMAN,
                actor_id=actor_id,
                mode="simulation",
                payload={
                    "message_id": str(message.id),
                    "channel": message.channel,
                    "external_delivery": False,
                    "llm_cost": "0.000000",
                    "messaging_cost": str(link.allocated_messaging_cost),
                    "cost_currency": message.cost_currency,
                },
            )
    return message


def _linked_invoice_ids(db: Session, message_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(MessageInvoice.invoice_id)
            .where(MessageInvoice.message_id == message_id)
            .order_by(MessageInvoice.created_at, MessageInvoice.id)
        )
    )


def _contact_for_sender(
    db: Session,
    *,
    client_id: uuid.UUID,
    channel: str,
    sender: str,
) -> Contact | None:
    contacts = list(db.scalars(select(Contact).where(Contact.client_id == client_id)))
    if channel == "email":
        normalized = sender.strip().casefold()
        return next(
            (
                contact
                for contact in contacts
                if contact.email and contact.email.strip().casefold() == normalized
            ),
            None,
        )
    normalized = re.sub(r"\D", "", sender)
    return next(
        (
            contact
            for contact in contacts
            if contact.phone and re.sub(r"\D", "", contact.phone) == normalized
        ),
        None,
    )


def _inbound_thread(
    db: Session,
    *,
    payload: InboundMessageCreate,
    contact: Contact | None,
    payer_id: uuid.UUID | None,
    reply: Message | None,
) -> CommunicationThread | None:
    if reply is not None and reply.thread_id is not None:
        reply_thread = db.get(CommunicationThread, reply.thread_id)
        if (
            reply_thread is not None
            and payload.external_thread_key
            and not reply_thread.external_thread_key
        ):
            reply_thread.external_thread_key = payload.external_thread_key
        return reply_thread
    channel_values = (
        ["whatsapp", "whatsapp_assisted"]
        if payload.channel == "whatsapp"
        else ["email"]
    )
    thread = None
    if payload.external_thread_key:
        thread = db.scalar(
            select(CommunicationThread).where(
                CommunicationThread.client_id == payload.client_id,
                CommunicationThread.external_thread_key == payload.external_thread_key,
                CommunicationThread.channel.in_(channel_values),
            )
        )
    if thread is None and contact is not None and payer_id is not None:
        thread = db.scalar(
            select(CommunicationThread).where(
                CommunicationThread.client_id == payload.client_id,
                CommunicationThread.payer_id == payer_id,
                CommunicationThread.contact_id == contact.id,
                CommunicationThread.channel.in_(channel_values),
                CommunicationThread.status == "open",
            )
        )
    if thread is None and contact is not None and payer_id is not None:
        thread = CommunicationThread(
            client_id=payload.client_id,
            payer_id=payer_id,
            contact_id=contact.id,
            channel=payload.channel,
            external_thread_key=payload.external_thread_key,
            status="open",
        )
        db.add(thread)
        db.flush()
    elif thread is not None and payload.external_thread_key and not thread.external_thread_key:
        thread.external_thread_key = payload.external_thread_key
    return thread


def register_inbound_message(db: Session, payload: InboundMessageCreate) -> Message:
    """Register a deterministic local webhook without contacting a provider."""

    idempotency_key = f"inbound:{payload.client_id}:{payload.channel}:{payload.provider_id}"
    existing = db.scalar(select(Message).where(Message.idempotency_key == idempotency_key))
    if existing is not None:
        classify_message(db, existing)
        return existing

    if db.get(Client, payload.client_id) is None:
        raise ValueError("Cliente no encontrado")
    reply = None
    if payload.in_reply_to_provider_id:
        reply = db.scalar(
            select(Message).where(
                Message.client_id == payload.client_id,
                Message.provider_id == payload.in_reply_to_provider_id,
            )
        )
    contact = db.get(Contact, reply.contact_id) if reply and reply.contact_id else None
    if contact is None:
        contact = _contact_for_sender(
            db,
            client_id=payload.client_id,
            channel=payload.channel,
            sender=payload.sender,
        )
    payer_id = reply.payer_id if reply else (contact.payer_id if contact else None)

    invoice_by_id: dict[uuid.UUID, Invoice] = {}
    if reply is not None:
        reply_invoice_ids = _linked_invoice_ids(db, reply.id)
        for invoice in db.scalars(
            select(Invoice).where(
                Invoice.client_id == payload.client_id,
                Invoice.id.in_(reply_invoice_ids),
            )
        ):
            invoice_by_id[invoice.id] = invoice
    requested_folios = list(dict.fromkeys(folio.strip() for folio in payload.invoice_folios if folio.strip()))
    matched_folios: set[str] = set()
    ambiguous_folios: set[str] = set()
    if requested_folios:
        invoice_query = select(Invoice).where(
            Invoice.client_id == payload.client_id,
            Invoice.folio.in_(requested_folios),
        )
        if payer_id is not None:
            invoice_query = invoice_query.where(Invoice.payer_id == payer_id)
        candidates_by_folio: dict[str, list[Invoice]] = {}
        for invoice in db.scalars(invoice_query):
            candidates_by_folio.setdefault(invoice.folio, []).append(invoice)
        for folio, candidates in candidates_by_folio.items():
            if len(candidates) == 1:
                invoice_by_id[candidates[0].id] = candidates[0]
                matched_folios.add(folio)
            else:
                ambiguous_folios.add(folio)
    invoices = sorted(invoice_by_id.values(), key=lambda item: (item.due_on, item.folio))
    if payer_id is None and invoices:
        payer_ids = {invoice.payer_id for invoice in invoices}
        if len(payer_ids) == 1:
            payer_id = next(iter(payer_ids))
    if contact is not None and payer_id is not None and contact.payer_id != payer_id:
        contact = None
    unmatched_folios = set(requested_folios) - matched_folios - ambiguous_folios
    needs_review = (
        contact is None
        or not invoices
        or bool(unmatched_folios)
        or bool(ambiguous_folios)
    )

    thread = _inbound_thread(
        db,
        payload=payload,
        contact=contact,
        payer_id=payer_id,
        reply=reply,
    )
    received_at = payload.received_at or datetime.now(timezone.utc)
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    message = Message(
        id=uuid.uuid4(),
        client_id=payload.client_id,
        invoice_id=invoices[0].id if invoices else None,
        payer_id=payer_id,
        contact_id=contact.id if contact else None,
        thread_id=thread.id if thread else None,
        channel=payload.channel,
        direction="inbound",
        mode="simulation",
        subject=payload.subject,
        body=payload.body,
        status="received",
        idempotency_key=idempotency_key,
        provider_id=payload.provider_id,
        provider_payload={
            "provider": "local_webhook_simulator",
            "external_delivery": False,
            "sender": payload.sender,
            "external_thread_key": payload.external_thread_key,
            "in_reply_to_provider_id": payload.in_reply_to_provider_id,
            "correlation": {
                "reply": reply is not None,
                "contact": contact is not None,
                "matched_invoice_folios": sorted(matched_folios),
                "unmatched_invoice_folios": sorted(unmatched_folios),
                "ambiguous_invoice_folios": sorted(ambiguous_folios),
                "needs_review": needs_review,
            },
        },
        safety_status="not_applicable",
        safety_flags=[],
        llm_cost=Decimal("0"),
        messaging_cost=Decimal("0"),
        cost_currency="USD",
        received_at=received_at,
    )
    db.add(message)
    db.flush()
    for invoice in invoices:
        db.add(
            MessageInvoice(
                client_id=payload.client_id,
                message_id=message.id,
                invoice_id=invoice.id,
                allocated_llm_cost=Decimal("0"),
                allocated_messaging_cost=Decimal("0"),
            )
        )
    for attachment in payload.attachments:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", attachment.original_name).strip("-_")
        safe_name = safe_name or "attachment"
        checksum = attachment.sha256 or hashlib.sha256(
            f"{payload.provider_id}:{attachment.original_name}".encode("utf-8")
        ).hexdigest()
        document = Document(
            client_id=payload.client_id,
            invoice_id=invoices[0].id if len(invoices) == 1 else None,
            kind=attachment.kind,
            object_key=f"local-inbound/{payload.client_id}/{message.id}/{safe_name}",
            original_name=attachment.original_name,
            sha256=checksum.lower(),
        )
        db.add(document)
        db.flush()
        db.add(
            MessageDocument(
                client_id=payload.client_id,
                message_id=message.id,
                document_id=document.id,
            )
        )

    event_invoice_ids = [invoice.id for invoice in invoices] or [None]
    for invoice_id in event_invoice_ids:
        record_event(
            db,
            client_id=payload.client_id,
            invoice_id=invoice_id,
            event_type="communication.received",
            actor_type=ActorType.SYSTEM,
            mode="simulation",
            payload={
                "message_id": str(message.id),
                "channel": payload.channel,
                "provider": "local_webhook_simulator",
                "contact_id": str(contact.id) if contact else None,
                "thread_id": str(thread.id) if thread else None,
                "attachment_count": len(payload.attachments),
                "needs_review": needs_review,
                "external_delivery": False,
            },
        )
    classify_message(db, message)
    return message


def register_manual_response(
    db: Session,
    payload: ManualResponseCreate,
    *,
    actor_id: uuid.UUID,
) -> Message:
    invoices = list(
        db.scalars(
            select(Invoice).where(
                Invoice.client_id == payload.client_id,
                Invoice.id.in_(payload.invoice_ids),
            )
        )
    )
    if len(invoices) != len(set(payload.invoice_ids)):
        raise ValueError("Una o más facturas no pertenecen al cliente")
    payer_ids = {invoice.payer_id for invoice in invoices}
    if len(payer_ids) != 1:
        raise ValueError("La respuesta manual sólo puede agrupar facturas del mismo pagador")
    payer_id = next(iter(payer_ids))
    contact = None
    if payload.contact_id:
        contact = db.scalar(
            select(Contact).where(
                Contact.id == payload.contact_id,
                Contact.client_id == payload.client_id,
                Contact.payer_id == payer_id,
            )
        )
        if contact is None:
            raise ValueError("El contacto no pertenece al cliente y pagador seleccionados")
    received_at = payload.received_at or datetime.now(timezone.utc)
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    thread = None
    if contact is not None:
        thread = _get_or_create_thread(
            db,
            client_id=payload.client_id,
            payer_id=payer_id,
            contact_id=contact.id,
            channel=payload.channel,
        )
    message = Message(
        client_id=payload.client_id,
        invoice_id=invoices[0].id,
        payer_id=payer_id,
        contact_id=contact.id if contact else None,
        thread_id=thread.id if thread else None,
        channel=payload.channel,
        direction="inbound",
        mode="manual",
        subject=payload.subject,
        body=payload.body,
        status="received",
        idempotency_key=f"manual:{payload.client_id}:{uuid.uuid4()}",
        provider_payload={
            "provider": "manual_operator",
            "external_delivery": False,
            "recorded_by": str(actor_id),
        },
        safety_status="not_applicable",
        safety_flags=[],
        llm_cost=Decimal("0"),
        messaging_cost=Decimal("0"),
        cost_currency="USD",
        received_at=received_at,
    )
    db.add(message)
    db.flush()
    for invoice in invoices:
        db.add(
            MessageInvoice(
                client_id=payload.client_id,
                message_id=message.id,
                invoice_id=invoice.id,
                allocated_llm_cost=Decimal("0"),
                allocated_messaging_cost=Decimal("0"),
            )
        )
        record_event(
            db,
            client_id=payload.client_id,
            invoice_id=invoice.id,
            event_type="communication.manual_response_recorded",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="manual",
            payload={
                "message_id": str(message.id),
                "channel": payload.channel,
                "contact_id": str(contact.id) if contact else None,
            },
        )
    classify_message(db, message)
    return message


def update_delivery_status(
    db: Session,
    message: Message,
    payload: DeliveryStatusUpdate,
    *,
    actor_id: uuid.UUID,
) -> Message:
    if message.direction != "outbound":
        raise ValueError("Sólo los mensajes salientes tienen estado de entrega")
    transitions = {
        "simulated": {"delivered", "failed"},
        "delivered": {"read", "failed"},
        "read": {"read"},
        "failed": {"failed"},
    }
    if payload.status == message.status:
        return message
    if payload.status not in transitions.get(message.status, set()):
        raise ValueError(f"Transición no permitida: {message.status} → {payload.status}")
    previous = message.status
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    message.status = payload.status
    message.provider_payload = {
        **(message.provider_payload or {}),
        f"{payload.status}_at": occurred_at.isoformat(),
        "delivery_detail": payload.detail,
        "external_delivery": False,
    }
    for invoice_id in _linked_invoice_ids(db, message.id) or [None]:
        record_event(
            db,
            client_id=message.client_id,
            invoice_id=invoice_id,
            event_type="communication.delivery_status_changed",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="simulation",
            payload={
                "message_id": str(message.id),
                "from": previous,
                "to": payload.status,
                "occurred_at": occurred_at.isoformat(),
                "detail": payload.detail,
                "external_delivery": False,
            },
        )
    return message
