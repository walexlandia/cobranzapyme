import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base
from app.domain import ActorType, InvoiceStatus, Role


class BaseRecord:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Client(BaseRecord, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(200))
    sender_email: Mapped[str | None] = mapped_column(String(320))
    bank_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    baseline_dso: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    baseline_on_time_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    baseline_late_distribution: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'::json"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(BaseRecord, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    client: Mapped[Client | None] = relationship()


class Contract(BaseRecord, Base):
    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint("client_id", "version", name="uq_contract_client_version"),
        Index(
            "uq_contract_active_client",
            "client_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PilotAuthorizationEvent(Base):
    __tablename__ = "pilot_authorization_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_pilot_authorization_idempotency"),
        CheckConstraint("action IN ('approved', 'revoked')", name="ck_pilot_authorization_action"),
        Index("ix_pilot_authorization_client_created", "client_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    authorized_contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    authorized_contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pilot_authorization_events.id"))
    performed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Payer(BaseRecord, Base):
    __tablename__ = "payers"

    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(250), nullable=False)


class PayerProfile(BaseRecord, Base):
    __tablename__ = "payer_profiles"

    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), unique=True, nullable=False)
    operational_requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    supplier_portal_url: Mapped[str | None] = mapped_column(String(500))
    supplier_portal_instructions: Mapped[str | None] = mapped_column(Text)
    corporate_channels: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    payment_cycle: Mapped[str | None] = mapped_column(String(200))


class PayerProfileRevision(Base):
    __tablename__ = "payer_profile_revisions"
    __table_args__ = (
        UniqueConstraint("payer_profile_id", "version", name="uq_payer_profile_revision_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payer_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payer_profiles.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClientPayerRelation(BaseRecord, Base):
    __tablename__ = "client_payer_relations"
    __table_args__ = (UniqueConstraint("client_id", "payer_id", name="uq_client_payer"),)

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), nullable=False, index=True)
    private_notes: Mapped[str | None] = mapped_column(Text)


class Contact(BaseRecord, Base):
    __tablename__ = "contacts"
    __table_args__ = (Index("ix_contact_client_payer", "client_id", "payer_id"),)

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    opted_out_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opted_out_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Invoice(BaseRecord, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("client_id", "document_type", "folio", name="uq_invoice_client_document"),
        Index("ix_invoice_client_payer", "client_id", "payer_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(30), default="factura", nullable=False)
    folio: Mapped[str] = mapped_column(String(80), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CLP", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    purchase_order: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.ISSUED, nullable=False
    )
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)

    payer: Mapped[Payer] = relationship()

    @property
    def payer_name(self) -> str:
        return self.payer.legal_name


class PayabilityItem(BaseRecord, Base):
    __tablename__ = "payability_items"
    __table_args__ = (
        UniqueConstraint("invoice_id", "item_type", name="uq_payability_invoice_item"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocks_payability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    responsible_role: Mapped[str] = mapped_column(String(80), default="client", nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class DelayCause(BaseRecord, Base):
    __tablename__ = "delay_causes"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id"), unique=True, nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)


class Document(BaseRecord, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "content IS NULL OR encryption_version = 'legacy_plaintext' OR "
            "(encryption_version = 'aesgcm-v1' AND encryption_nonce IS NOT NULL)",
            name="ck_document_encryption_metadata",
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(300), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    encryption_version: Mapped[str | None] = mapped_column(String(30))
    encryption_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)


class MessageTemplate(BaseRecord, Base):
    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint(
            "client_id", "template_key", "channel", "version",
            name="uq_message_template_version",
        ),
        Index(
            "uq_message_template_active",
            "client_id",
            "template_key",
            "channel",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient_role: Mapped[str] = mapped_column(String(80), nullable=False)
    tone: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_template: Mapped[str | None] = mapped_column(Text)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CommunicationThread(BaseRecord, Base):
    __tablename__ = "communication_threads"
    __table_args__ = (
        Index(
            "ix_communication_thread_participants",
            "client_id",
            "payer_id",
            "contact_id",
            "channel",
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    external_thread_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)


class Message(BaseRecord, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_message_idempotency_key"),
        Index("ix_message_outbox", "client_id", "status", "created_at"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    payer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payers.id"), index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_threads.id"), index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_templates.id"), index=True
    )
    workflow_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_jobs.id"), index=True
    )
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    provider_id: Mapped[str | None] = mapped_column(String(200))
    provider_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(30), default="safe", nullable=False)
    safety_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    llm_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), default=Decimal("0"), nullable=False
    )
    messaging_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), default=Decimal("0"), nullable=False
    )
    cost_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MessageInvoice(BaseRecord, Base):
    __tablename__ = "message_invoices"
    __table_args__ = (
        UniqueConstraint("message_id", "invoice_id", name="uq_message_invoice"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    allocated_llm_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), default=Decimal("0"), nullable=False
    )
    allocated_messaging_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), default=Decimal("0"), nullable=False
    )


class MessageDocument(BaseRecord, Base):
    __tablename__ = "message_documents"
    __table_args__ = (
        UniqueConstraint("message_id", "document_id", name="uq_message_document"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)


class Payment(BaseRecord, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),
        UniqueConstraint(
            "bank_transaction_id", "invoice_id", name="uq_payment_bank_transaction_invoice"
        ),
        CheckConstraint("amount > 0", name="ck_payment_positive_amount"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))
    bank_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_transactions.id"), index=True
    )
    source: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))


class PaymentAttribution(BaseRecord, Base):
    __tablename__ = "payment_attributions"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_payment_attribution_payment"),
        CheckConstraint("percentage >= 0 AND percentage <= 100", name="ck_attribution_percentage"),
        CheckConstraint("base_amount > 0", name="ck_attribution_positive_base"),
        CheckConstraint("commission_amount >= 0", name="ck_attribution_nonnegative_commission"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contracts.id"), index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    rationale: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    calculated_by: Mapped[str] = mapped_column(String(40), default="rules_v1", nullable=False)


class BankTransaction(BaseRecord, Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (UniqueConstraint("client_id", "external_id", name="uq_bank_tx_client_external"),)

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    counterparty_rut: Mapped[str | None] = mapped_column(String(12))
    currency: Mapped[str] = mapped_column(String(3), default="CLP", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="unmatched", nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(300))
    source_row: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    imported_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)


class ReconciliationProposal(BaseRecord, Base):
    __tablename__ = "reconciliation_proposals"
    __table_args__ = (
        UniqueConstraint(
            "bank_transaction_id", "candidate_key", name="uq_reconciliation_candidate"
        ),
        Index(
            "uq_reconciliation_confirmed_transaction",
            "bank_transaction_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_transactions.id"), nullable=False, index=True
    )
    candidate_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class ReconciliationItem(BaseRecord, Base):
    __tablename__ = "reconciliation_items"
    __table_args__ = (
        UniqueConstraint("proposal_id", "invoice_id", name="uq_reconciliation_item_invoice"),
        CheckConstraint("allocated_amount > 0", name="ck_reconciliation_positive_allocation"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliation_proposals.id"), nullable=False, index=True
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class ExceptionCase(BaseRecord, Base):
    __tablename__ = "exception_cases"
    __table_args__ = (
        Index("ix_exception_queue", "client_id", "status", "priority", "created_at"),
        Index(
            "uq_exception_open_message",
            "message_id",
            unique=True,
            postgresql_where=text("status = 'open' AND message_id IS NOT NULL"),
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"), index=True)
    classification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_classifications.id"), index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    human_minutes: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class MessageClassification(BaseRecord, Base):
    __tablename__ = "message_classifications"
    __table_args__ = (
        UniqueConstraint("message_id", "version", name="uq_message_classification_version"),
        Index("ix_message_classification_history", "client_id", "message_id", "created_at"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    classifier_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    classifier_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    decision_source: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_classifications.id"), index=True
    )


class EvaluationSet(BaseRecord, Base):
    __tablename__ = "evaluation_sets"
    __table_args__ = (
        UniqueConstraint("client_id", "version", name="uq_evaluation_set_version"),
        Index(
            "uq_evaluation_set_open",
            "client_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    anonymization_version: Mapped[str] = mapped_column(String(80), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationExample(BaseRecord, Base):
    __tablename__ = "evaluation_examples"
    __table_args__ = (
        UniqueConstraint("evaluation_set_id", "source_hash", name="uq_evaluation_example_source"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    evaluation_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_sets.id"), nullable=False, index=True
    )
    classification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("message_classifications.id"), nullable=False, unique=True, index=True
    )
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    redacted_text: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_category: Mapped[str] = mapped_column(String(80), nullable=False)
    actual_category: Mapped[str] = mapped_column(String(80), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ClassificationPolicy(BaseRecord, Base):
    __tablename__ = "classification_policies"
    __table_args__ = (
        UniqueConstraint("client_id", "category", name="uq_classification_policy_category"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="supervised", nullable=False)
    minimum_precision: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.9000"), nullable=False
    )
    minimum_samples: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    current_precision: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    eligible_for_automation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PayerProfileProposal(BaseRecord, Base):
    __tablename__ = "payer_profile_proposals"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payers.id"), nullable=False, index=True)
    exception_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exception_cases.id"), index=True
    )
    classification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_classifications.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    proposed_changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowState(BaseRecord, Base):
    __tablename__ = "workflow_states"
    __table_args__ = (UniqueConstraint("invoice_id", name="uq_workflow_state_invoice"),)

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    pause_reason: Mapped[str | None] = mapped_column(String(120))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class WorkflowControl(BaseRecord, Base):
    __tablename__ = "workflow_controls"
    __table_args__ = (
        UniqueConstraint("client_id", "scope_type", "scope_id", name="uq_workflow_control_scope"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    resume_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class WorkflowJob(BaseRecord, Base):
    __tablename__ = "workflow_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_workflow_job_idempotency_key"),
        Index("ix_workflow_job_due", "status", "scheduled_for"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    payer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payers.id"), index=True)
    recipient_contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="automatic", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_event_client_invoice_created", "client_id", "invoice_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType, name="actor_type"), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    mode: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DataAccessLog(Base):
    __tablename__ = "data_access_logs"
    __table_args__ = (Index("ix_data_access_client_created", "client_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(30), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    remote_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

