from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.audit import record_event
from app.config import settings
from app.database import SessionLocal
from app.domain import ActorType, InvoiceStatus, Role
from app.models import (
    Client,
    Contact,
    Contract,
    DelayCause,
    ExceptionCase,
    Invoice,
    MessageTemplate,
    PayabilityItem,
    Payer,
    PilotLogEntry,
    User,
)
from app.schemas import (
    ContractRules,
    InboundAttachmentCreate,
    InboundMessageCreate,
    MessageTemplateCreate,
    PayerRequirements,
)
from app.security import hash_password
from app.services.communications import (
    DEFAULT_BODY,
    DEFAULT_SUBJECT,
    create_template_version,
    register_inbound_message,
)
from app.services.client_documents import create_client_document_submission
from app.services.payability import (
    create_profile_revision,
    ensure_checklist,
    get_or_create_profile,
    profile_version,
)
from app.services.payments import register_manual_payment


DEMO_CLIENTS = [
    (
        "Servicios Cordillera SpA",
        "76123456-0",
        Decimal("51.40"),
        Decimal("46.67"),
        {"on_time": 7, "late_1_15": 6, "late_16_30": 2, "late_31_plus": 0},
    ),
    (
        "Ingeniería del Sur Ltda.",
        "76543210-3",
        Decimal("46.20"),
        Decimal("42.86"),
        {"on_time": 6, "late_1_15": 5, "late_16_30": 3, "late_31_plus": 0},
    ),
    (
        "Montajes Atacama SpA",
        "77345678-K",
        Decimal("57.80"),
        Decimal("43.75"),
        {"on_time": 7, "late_1_15": 6, "late_16_30": 3, "late_31_plus": 0},
    ),
]

DEMO_PAYERS = [
    ("96534210-9", "Compañía Minera Demo S.A."),
    ("76086428-5", "Retail Nacional Demo S.A."),
    ("77361871-2", "Energía Industrial Demo SpA"),
]

LEGACY_DEMO_ADMIN_EMAIL = "admin@recupera.local"


def seed() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.demo_admin_email.lower()))
        if admin is None and settings.demo_admin_email.lower() == "admin@example.com":
            admin = db.scalar(select(User).where(User.email == LEGACY_DEMO_ADMIN_EMAIL))
            if admin is not None:
                admin.email = settings.demo_admin_email.lower()
        if admin is None:
            admin = User(
                email=settings.demo_admin_email.lower(),
                full_name="Administrador Recupera",
                password_hash=hash_password(settings.demo_admin_password),
                role=Role.ADMIN,
            )
            db.add(admin)
            db.flush()

        clients: list[Client] = []
        for name, rut, dso, on_time, late_distribution in DEMO_CLIENTS:
            client = db.scalar(select(Client).where(Client.rut == rut))
            if client is None:
                client = Client(
                    name=name,
                    rut=rut,
                    baseline_dso=dso,
                    baseline_on_time_percent=on_time,
                    baseline_late_distribution=late_distribution,
                )
                db.add(client)
                db.flush()
                record_event(
                    db,
                    client_id=client.id,
                    event_type="client.seeded",
                    actor_type=ActorType.SYSTEM,
                    payload={"demo": True},
                )
            else:
                client.baseline_dso = client.baseline_dso or dso
                client.baseline_on_time_percent = client.baseline_on_time_percent or on_time
                if not client.baseline_late_distribution:
                    client.baseline_late_distribution = late_distribution
            clients.append(client)

        for client in clients:
            client.sender_name = client.sender_name or f"Equipo de pagos · {client.name}"
            client.sender_email = client.sender_email or (
                f"cobranza+{client.rut.split('-')[0]}@recupera.demo"
            )
            if not client.bank_details:
                client.bank_details = {
                    "bank": "Banco Demo",
                    "account_type": "Cuenta corriente",
                    "account_number": f"00{client.rut.split('-')[0]}",
                    "account_holder": client.name,
                    "rut": client.rut,
                    "email": client.sender_email,
                }
            contract = db.scalar(
                select(Contract).where(Contract.client_id == client.id, Contract.version == 1)
            )
            if contract is None:
                contract = Contract(
                    client_id=client.id,
                    version=1,
                    active=True,
                    rules=ContractRules().model_dump(mode="json"),
                )
                db.add(contract)
                db.flush()
                record_event(
                    db,
                    client_id=client.id,
                    event_type="contract.seeded",
                    actor_type=ActorType.SYSTEM,
                    payload={"contract_id": str(contract.id), "version": 1, "demo": True},
                )

        payers: list[Payer] = []
        for rut, name in DEMO_PAYERS:
            payer = db.scalar(select(Payer).where(Payer.rut == rut))
            if payer is None:
                payer = Payer(rut=rut, legal_name=name)
                db.add(payer)
                db.flush()
            payers.append(payer)

        demo_requirements = [
            PayerRequirements(
                requires_purchase_order=True,
                requires_hes=True,
                requires_supplier_portal=True,
                risk_days_before_due=10,
            ),
            PayerRequirements(
                requires_purchase_order=True,
                requires_delivery_note=True,
                requires_supplier_portal=True,
                risk_days_before_due=7,
            ),
            PayerRequirements(
                requires_purchase_order=True,
                requires_hes=True,
                risk_days_before_due=5,
            ),
        ]
        for index, payer in enumerate(payers):
            profile = get_or_create_profile(db, payer.id)
            if profile_version(db, profile.id) == 0:
                profile.operational_requirements = demo_requirements[index].model_dump(mode="json")
                profile.supplier_portal_url = (
                    f"https://portal.demo.local/{payer.rut}"
                    if demo_requirements[index].requires_supplier_portal
                    else None
                )
                profile.supplier_portal_instructions = (
                    "Ingresar factura, OC y respaldo de conformidad; conservar el número de ingreso."
                    if demo_requirements[index].requires_supplier_portal
                    else None
                )
                profile.corporate_channels = {"email": f"cxp{index + 1}@pagador.demo"}
                profile.payment_cycle = ["Viernes", "Días 10 y 25", "Último día hábil"][index]
                db.flush()
                create_profile_revision(db, profile, actor_id=None)

        for client_index, client in enumerate(clients):
            for payer_index, payer in enumerate(payers):
                contact = db.scalar(
                    select(Contact).where(
                        Contact.client_id == client.id,
                        Contact.payer_id == payer.id,
                        Contact.role == "accounts_payable",
                    )
                )
                if contact is None:
                    db.add(
                        Contact(
                            client_id=client.id,
                            payer_id=payer.id,
                            name=f"Contacto CxP {payer_index + 1}",
                            role="accounts_payable",
                            email=f"cxp{payer_index + 1}.cliente{client_index + 1}@pagador.demo",
                            phone=f"+5697000{client_index + 1}{payer_index + 1}00",
                        )
                    )
            for channel in ("email", "whatsapp_assisted"):
                existing_template = db.scalar(
                    select(MessageTemplate).where(
                        MessageTemplate.client_id == client.id,
                        MessageTemplate.template_key == "payment_due",
                        MessageTemplate.channel == channel,
                        MessageTemplate.active.is_(True),
                    )
                )
                if existing_template is None:
                    create_template_version(
                        db,
                        MessageTemplateCreate(
                            client_id=client.id,
                            template_key="payment_due",
                            channel=channel,
                            stage="due",
                            recipient_role="accounts_payable",
                            tone="cordial",
                            subject_template=(DEFAULT_SUBJECT if channel == "email" else None),
                            body_template=DEFAULT_BODY,
                            approved=False,
                        ),
                        actor_id=None,
                        actor_type=ActorType.SYSTEM,
                    )

        base_date = date.today() - timedelta(days=90)
        for client_index, client in enumerate(clients):
            client_user_email = f"cliente{client_index + 1}@example.com"
            client_user = db.scalar(select(User).where(User.email == client_user_email))
            if client_user is None:
                legacy_client_email = f"cliente{client_index + 1}@recupera.local"
                client_user = db.scalar(select(User).where(User.email == legacy_client_email))
                if client_user is not None:
                    client_user.email = client_user_email
            if client_user is None:
                client_user = User(
                    email=client_user_email,
                    full_name=f"Usuario {client.name}",
                    password_hash=hash_password(settings.demo_admin_password),
                    role=Role.CLIENT,
                    client_id=client.id,
                )
                db.add(client_user)
                db.flush()
            for index in range(30):
                folio = f"DEMO-{client_index + 1}-{index + 1:03d}"
                invoice = db.scalar(
                    select(Invoice).where(
                        Invoice.client_id == client.id,
                        Invoice.document_type == "factura",
                        Invoice.folio == folio,
                    )
                )
                if invoice is None:
                    issued_on = base_date + timedelta(days=index * 2)
                    invoice = Invoice(
                        client_id=client.id,
                        payer_id=payers[index % len(payers)].id,
                        folio=folio,
                        issued_on=issued_on,
                        due_on=issued_on + timedelta(days=30),
                        total_amount=Decimal(450000 + index * 37500),
                        purchase_order=f"OC-{1000 + index}" if index % 3 else None,
                        source="demo_seed",
                    )
                    db.add(invoice)
                    db.flush()
                    record_event(
                        db,
                        client_id=client.id,
                        invoice_id=invoice.id,
                        event_type="invoice.seeded",
                        actor_type=ActorType.SYSTEM,
                        payload={"demo": True},
                    )
                ensure_checklist(db, invoice, actor_type=ActorType.SYSTEM)
                items = list(
                    db.scalars(
                        select(PayabilityItem).where(PayabilityItem.invoice_id == invoice.id)
                    )
                )
                if index % 4 == 0:
                    for item in items:
                        if item.required and item.blocks_payability:
                            previous = {"status": item.status, "evidence": item.evidence}
                            item.status = "fulfilled"
                            item.evidence = {**item.evidence, "demo": True}
                            if item.item_type == "sii_acceptance":
                                item.evidence["sii_status"] = "accepted"
                            record_event(
                                db,
                                client_id=client.id,
                                invoice_id=invoice.id,
                                event_type="payability.item_changed",
                                actor_type=ActorType.SYSTEM,
                                mode="automatic",
                                payload={
                                    "item_id": str(item.id),
                                    "item_type": item.item_type,
                                    "from": previous,
                                    "to": {"status": item.status, "evidence": item.evidence},
                                    "demo": True,
                                },
                            )
                elif index % 4 == 2:
                    sii_item = next(
                        (item for item in items if item.item_type == "sii_acceptance"), None
                    )
                    if sii_item is not None:
                        previous = {"status": sii_item.status, "evidence": sii_item.evidence}
                        sii_item.status = "blocked"
                        sii_item.evidence = {"demo": True, "sii_status": "claimed"}
                        invoice.status = InvoiceStatus.CLAIMED
                        record_event(
                            db,
                            client_id=client.id,
                            invoice_id=invoice.id,
                            event_type="payability.item_changed",
                            actor_type=ActorType.SYSTEM,
                            mode="automatic",
                            payload={
                                "item_id": str(sii_item.id),
                                "item_type": sii_item.item_type,
                                "from": previous,
                                "to": {
                                    "status": sii_item.status,
                                    "evidence": sii_item.evidence,
                                },
                                "demo": True,
                            },
                        )

                if index % 4 != 0:
                    cause_categories = [
                        "sii_acceptance",
                        "purchase_order",
                        "hes_conformity",
                        "supplier_portal",
                        "payer_liquidity",
                        "commercial_dispute",
                        "other",
                    ]
                    cause = db.scalar(
                        select(DelayCause).where(DelayCause.invoice_id == invoice.id)
                    )
                    if cause is None:
                        db.add(
                            DelayCause(
                                client_id=client.id,
                                invoice_id=invoice.id,
                                category=cause_categories[index % len(cause_categories)],
                                detail="Caso sintético para validación local",
                                source="demo_seed",
                            )
                        )
                if index in {12, 24, 29}:
                    register_manual_payment(
                        db,
                        invoice=invoice,
                        amount=invoice.total_amount,
                        paid_on=min(invoice.due_on - timedelta(days=2), date.today()),
                        reference=f"DEMO-PAGO-{client_index + 1}-{index + 1:03d}",
                        evidence_name=f"comprobante-{invoice.folio}.txt",
                        evidence_content=(
                            f"Comprobante sintético sin validez bancaria · {invoice.folio}"
                        ).encode("utf-8"),
                        actor_id=admin.id,
                    )
                if index == 1:
                    pending_client_item = next(
                        (
                            item
                            for item in items
                            if item.required
                            and item.responsible_role == "client"
                            and item.status not in {"fulfilled", "not_applicable"}
                        ),
                        None,
                    )
                    if pending_client_item is not None:
                        create_client_document_submission(
                            db,
                            user=client_user,
                            invoice=invoice,
                            item=pending_client_item,
                            filename=f"respaldo-demo-{invoice.folio}.pdf",
                            content=(
                                "Documento sintético para revisar; no corresponde a una "
                                f"operación real. Factura {invoice.folio}."
                            ).encode("utf-8"),
                        )
        db.flush()
        for client_index, client in enumerate(clients):
            invoice = db.scalar(
                select(Invoice)
                .where(Invoice.client_id == client.id)
                .order_by(Invoice.issued_on, Invoice.folio)
            )
            if invoice is None:
                continue
            contact = db.scalar(
                select(Contact).where(
                    Contact.client_id == client.id,
                    Contact.payer_id == invoice.payer_id,
                    Contact.role == "accounts_payable",
                )
            )
            if contact is None or contact.email is None:
                continue
            inbound = register_inbound_message(
                db,
                InboundMessageCreate(
                    client_id=client.id,
                    channel="email",
                    provider_id=f"seed-inbound-{client_index + 1}",
                    sender=contact.email,
                    external_thread_key=f"seed-thread-{client_index + 1}",
                    subject=f"RE: factura {invoice.folio}",
                    body=(
                        "Confirmamos recepción. La factura quedó ingresada y será revisada "
                        "en el próximo ciclo de pagos."
                    ),
                    invoice_folios=[invoice.folio],
                    attachments=[
                        InboundAttachmentCreate(
                            original_name=f"acuse-{invoice.folio}.pdf",
                            kind="receipt_acknowledgement",
                        )
                    ],
                ),
            )
            case = db.scalar(
                select(ExceptionCase).where(ExceptionCase.message_id == inbound.id)
            )
            if case is not None:
                # The demo dataset explicitly declares zero operator effort so that a
                # measured zero is distinguishable from a missing legacy value.
                case.human_minutes = Decimal("0")
                case.human_minutes_measured = True
            if case is not None and not (case.detail or {}).get("client_escalation"):
                escalated_at = datetime.now(timezone.utc)
                case.priority = 100
                case.detail = {
                    **(case.detail or {}),
                    "client_escalation": {
                        "note": (
                            "Confirma si la factura fue aceptada para el próximo ciclo "
                            "de pago o entrega antecedentes adicionales."
                        ),
                        "actor_id": str(admin.id),
                        "created_at": escalated_at.isoformat(),
                        "external_delivery": False,
                        "demo": True,
                    },
                }
                record_event(
                    db,
                    client_id=client.id,
                    invoice_id=invoice.id,
                    event_type="exception.escalated_to_client",
                    actor_type=ActorType.SYSTEM,
                    mode="simulation",
                    payload={
                        "exception_id": str(case.id),
                        "external_delivery": False,
                        "demo": True,
                    },
                )
            demo_entries = [
                (
                    "decision",
                    "info",
                    "Mantener revisión humana de compromisos sin fecha",
                    "Decisión sintética: no automatizar respuestas ambiguas durante el piloto.",
                    Decimal("4"),
                ),
                (
                    "incident",
                    "warning",
                    "Documento pendiente bloquea pagabilidad",
                    "Incidencia sintética abierta para demostrar seguimiento y resolución.",
                    Decimal("6"),
                ),
                (
                    "manual_work",
                    "info",
                    "Revisión semanal de cartera",
                    "Trabajo manual sintético registrado fuera de los flujos automáticos.",
                    Decimal("18"),
                ),
            ]
            for entry_type, severity, title, detail, minutes in demo_entries:
                existing_entry = db.scalar(
                    select(PilotLogEntry).where(
                        PilotLogEntry.client_id == client.id,
                        PilotLogEntry.title == title,
                    )
                )
                if existing_entry is not None:
                    existing_entry.human_minutes_measured = True
                    existing_entry.labor_accounting = "additional"
                    continue
                closed = entry_type != "incident"
                entry = PilotLogEntry(
                    client_id=client.id,
                    related_invoice_id=invoice.id,
                    entry_type=entry_type,
                    severity=severity,
                    title=title,
                    detail=detail,
                    status="resolved" if closed else "open",
                    occurred_on=date.today() - timedelta(days=client_index + 1),
                    human_minutes=minutes,
                    human_minutes_measured=True,
                    labor_accounting="additional",
                    created_by=admin.id,
                    resolved_by=admin.id if closed else None,
                    resolved_at=datetime.now(timezone.utc) if closed else None,
                    resolution_note="Registro sintético completo." if closed else None,
                )
                db.add(entry)
                db.flush()
                record_event(
                    db,
                    client_id=client.id,
                    invoice_id=invoice.id,
                    event_type="pilot.log_recorded",
                    actor_type=ActorType.SYSTEM,
                    mode="simulation",
                    payload={
                        "pilot_log_entry_id": str(entry.id),
                        "entry_type": entry.entry_type,
                        "demo": True,
                    },
                )
        db.commit()


if __name__ == "__main__":
    seed()

