import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.domain import ActorType, InvoiceStatus, Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DataAccessLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    user_id: uuid.UUID
    actor_role: str
    client_id: uuid.UUID | None
    method: str
    path: str
    status_code: int
    duration_ms: int
    remote_hash: str | None
    user_agent: str | None
    created_at: datetime


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    client_id: uuid.UUID | None


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    rut: str
    sender_name: str | None = None
    sender_email: EmailStr | None = None
    bank_details: dict = Field(default_factory=dict)
    baseline_dso: Decimal | None = Field(default=None, ge=0)
    baseline_on_time_percent: Decimal | None = Field(default=None, ge=0, le=100)
    baseline_late_distribution: dict = Field(default_factory=dict)


class ClientView(ClientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    active: bool
    created_at: datetime


class ClientPortalTotals(BaseModel):
    invoice_count: int
    managed_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    payable_count: int
    at_risk_count: int
    paid_count: int
    pending_client_count: int
    dispute_count: int


class ClientPortalInvoiceView(BaseModel):
    id: uuid.UUID
    folio: str
    payer_name: str
    issued_on: date
    due_on: date
    currency: str
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str
    payability_status: str
    checklist_completed: int
    checklist_total: int
    missing_items: list[str]
    pending_client_items: list[str]


class ClientPortalSummaryView(BaseModel):
    client_id: uuid.UUID
    client_name: str
    as_of: date
    totals: ClientPortalTotals
    invoices: list[ClientPortalInvoiceView]


class WeeklyClientReportView(BaseModel):
    client_id: uuid.UUID
    client_name: str
    period_start: date
    period_end: date
    generated_at: datetime
    payments_this_week_count: int
    payments_this_week_amount: Decimal
    summary: ClientPortalSummaryView


class ClientDocumentSubmissionView(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_folio: str
    payability_item_id: uuid.UUID
    item_label: str
    document_id: uuid.UUID
    original_name: str
    content_sha256: str
    status: Literal["pending", "accepted", "rejected"]
    submitted_by: uuid.UUID
    submitted_by_name: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class ClientDocumentReviewCommand(BaseModel):
    client_id: uuid.UUID
    decision: Literal["accepted", "rejected"]
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def rejection_requires_note(self) -> "ClientDocumentReviewCommand":
        if self.decision == "rejected" and not (self.note or "").strip():
            raise ValueError("El rechazo debe incluir una observación")
        return self


class InvoiceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    payer_id: uuid.UUID
    payer_name: str
    document_type: str
    folio: str
    issued_on: date
    due_on: date
    currency: str
    total_amount: Decimal
    purchase_order: str | None
    status: InvoiceStatus
    source: str
    payability_status: str = "incomplete"
    payability_completed: int = 0
    payability_total: int = 0


class InvoiceStatusUpdate(BaseModel):
    client_id: uuid.UUID
    status: InvoiceStatus


class ContactImportRow(BaseModel):
    row: int
    payer_rut: str
    payer_name: str
    name: str
    role: str
    email: EmailStr | None = None
    phone: str | None = None


class ImportIssue(BaseModel):
    row: int
    field: str | None = None
    message: str


class InvoiceImportRow(BaseModel):
    row: int
    payer_rut: str
    payer_name: str
    document_type: str = "factura"
    folio: str
    issued_on: date
    due_on: date
    total_amount: Decimal
    currency: str = "CLP"
    purchase_order: str | None = None


class ImportPreview(BaseModel):
    valid_rows: list[InvoiceImportRow]
    issues: list[ImportIssue]
    can_commit: bool
    imported_count: int = 0


class ContactImportPreview(BaseModel):
    valid_rows: list[ContactImportRow]
    issues: list[ImportIssue]
    can_commit: bool
    imported_count: int = 0


class SiiStatusImportRow(BaseModel):
    row: int
    folio: str
    document_type: str = "factura"
    sii_status: Literal["accepted", "claimed", "pending", "rejected"]
    checked_on: date
    claim_deadline: date | None = None
    detail: str | None = None


class SiiStatusImportPreview(BaseModel):
    valid_rows: list[SiiStatusImportRow]
    issues: list[ImportIssue]
    can_commit: bool
    imported_count: int = 0


class BankStatementRow(BaseModel):
    row: int
    external_id: str
    occurred_on: date
    amount: Decimal
    description: str | None = None
    counterparty_rut: str | None = None
    currency: str = "CLP"


class BankStatementPreview(BaseModel):
    valid_rows: list[BankStatementRow]
    issues: list[ImportIssue]
    can_commit: bool
    imported_count: int = 0
    proposals_created: int = 0


class PaymentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    paid_on: date
    verified: bool
    evidence_document_id: uuid.UUID | None
    bank_transaction_id: uuid.UUID | None
    source: str
    reference: str | None
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    created_at: datetime


class CommissionDetailView(BaseModel):
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    folio: str | None
    paid_on: date
    payment_amount: Decimal
    source: str
    category: str
    percentage: Decimal
    commission_amount: Decimal
    contract_id: uuid.UUID | None
    rationale: dict


class CommissionReportView(BaseModel):
    client_id: uuid.UUID
    period: str
    currency: str
    totals: dict
    metrics: dict
    details: list[CommissionDetailView]
    generated_at: datetime


class BankTransactionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    external_id: str
    occurred_on: date
    amount: Decimal
    description: str | None
    counterparty_rut: str | None
    currency: str
    status: str
    source_filename: str | None
    source_row: int | None
    created_at: datetime


class ReconciliationProposalView(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    bank_transaction_id: uuid.UUID
    status: str
    score: Decimal
    score_breakdown: dict
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    transaction: dict
    invoices: list[dict]


class ReconciliationDecision(BaseModel):
    client_id: uuid.UUID
    decision: Literal["confirmed", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


class CommissionRules(BaseModel):
    preventive_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    recovery_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class ContractRules(BaseModel):
    timezone: Literal["America/Santiago"] = "America/Santiago"
    allowed_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    window_start: time = time(9, 0)
    window_end: time = time(18, 0)
    max_contacts_per_week: int = Field(default=2, ge=1, le=7)
    channels: list[Literal["email", "whatsapp_assisted"]] = Field(default_factory=lambda: ["email"])
    tone: Literal["cordial", "direct", "formal"] = "cordial"
    preventive_days_before_due: int = Field(default=7, ge=1, le=30)
    escalation_days_after_due: int = Field(default=15, ge=1, le=90)
    commission: CommissionRules = Field(default_factory=CommissionRules)

    @field_validator("allowed_weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        normalized = sorted(set(value))
        if not normalized or any(day < 0 or day > 6 for day in normalized):
            raise ValueError("allowed_weekdays debe contener días entre 0 y 6")
        return normalized

    @model_validator(mode="after")
    def validate_window(self) -> "ContractRules":
        if self.window_end <= self.window_start:
            raise ValueError("window_end debe ser posterior a window_start")
        if not self.channels:
            raise ValueError("Debe existir al menos un canal")
        return self


class ContractCreate(BaseModel):
    client_id: uuid.UUID
    rules: ContractRules
    activate: bool = True


class ContractView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    version: int
    rules: ContractRules
    active: bool
    created_at: datetime


class ContractActivate(BaseModel):
    client_id: uuid.UUID


class PilotAuthorizationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    contract_id: uuid.UUID
    action: str
    channels: list[str]
    authorized_contact_name: str
    authorized_contact_email: str
    valid_from: date
    valid_until: date | None
    evidence_document_id: uuid.UUID | None
    supersedes_id: uuid.UUID | None
    performed_by: uuid.UUID
    note: str | None
    created_at: datetime


class PilotAuthorizationRevoke(BaseModel):
    client_id: uuid.UUID
    note: str = Field(min_length=3, max_length=2000)


class PilotReadinessView(BaseModel):
    client_id: uuid.UUID
    ready: bool
    checks: dict[str, bool]
    blockers: list[str]
    active_contract_id: uuid.UUID | None
    required_channels: list[str]
    authorization: PilotAuthorizationView | None


class WorkflowRunRequest(BaseModel):
    client_id: uuid.UUID | None = None
    mode: Literal["manual", "automatic"] = "manual"


class WorkflowRunResult(BaseModel):
    clients_processed: int
    invoices_evaluated: int
    states_created: int
    states_updated: int
    jobs_created: int
    jobs_skipped: int


class WorkflowStateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    contract_id: uuid.UUID
    stage: str
    status: str
    pause_reason: str | None
    next_run_at: datetime | None
    updated_at: datetime


class WorkflowJobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    payer_id: uuid.UUID | None
    recipient_contact_id: uuid.UUID | None
    contract_id: uuid.UUID
    action_type: str
    stage: str
    status: str
    scheduled_for: datetime
    processed_at: datetime | None
    attempts: int
    mode: str
    payload: dict


class WorkflowControlCommand(BaseModel):
    client_id: uuid.UUID
    scope_type: Literal["invoice", "payer"]
    scope_id: uuid.UUID
    action: Literal["pause", "resume"]
    reason: str | None = Field(default=None, max_length=200)
    resume_at: datetime | None = None


class WorkflowControlView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    scope_type: str
    scope_id: uuid.UUID
    status: str
    reason: str | None
    resume_at: datetime | None
    updated_at: datetime


class EventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID | None
    event_type: str
    actor_type: ActorType
    actor_id: uuid.UUID | None
    mode: str
    payload: dict
    created_at: datetime


class WorkflowSimulationRequest(BaseModel):
    client_id: uuid.UUID
    simulation_date: date
    invoice_id: uuid.UUID | None = None


class WorkflowStageWindow(BaseModel):
    stage: str
    action_type: str | None
    starts_on: date
    ends_on: date | None


class WorkflowSimulationItem(BaseModel):
    invoice_id: uuid.UUID
    folio: str
    payer_id: uuid.UUID
    payer_name: str
    simulation_date: date
    stage: str
    state_status: str
    pause_reason: str | None
    action_type: str | None
    scheduled_for: datetime | None
    contract_id: uuid.UUID
    contract_version: int
    decision_reasons: list[str]
    stage_windows: list[WorkflowStageWindow]


class OtherRequirement(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]{2,40}$")
    label: str = Field(min_length=2, max_length=160)
    responsible_role: Literal["client", "requester", "accounts_payable"] = "client"


class PayerRequirements(BaseModel):
    requires_purchase_order: bool = True
    requires_hes: bool = False
    requires_delivery_note: bool = False
    requires_supplier_portal: bool = False
    other_requirements: list[OtherRequirement] = Field(default_factory=list)
    risk_days_before_due: int = Field(default=7, ge=1, le=30)

    @field_validator("other_requirements")
    @classmethod
    def unique_requirement_codes(
        cls, value: list[OtherRequirement]
    ) -> list[OtherRequirement]:
        codes = [item.code for item in value]
        if len(codes) != len(set(codes)):
            raise ValueError("Los códigos de requisitos adicionales deben ser únicos")
        return value


class PayerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rut: str
    legal_name: str


class PayerProfileUpdate(BaseModel):
    operational_requirements: PayerRequirements
    supplier_portal_url: str | None = Field(default=None, max_length=500)
    supplier_portal_instructions: str | None = Field(default=None, max_length=4000)
    corporate_channels: dict = Field(default_factory=dict)
    payment_cycle: str | None = Field(default=None, max_length=200)


class PayerProfileView(PayerProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payer_id: uuid.UUID
    version: int
    updated_at: datetime


class PayerProfileRevisionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payer_profile_id: uuid.UUID
    version: int
    snapshot: dict
    actor_id: uuid.UUID | None
    created_at: datetime


class PayabilityItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    item_type: str
    label: str
    status: str
    required: bool
    blocks_payability: bool
    responsible_role: str
    evidence: dict
    updated_at: datetime


class PayabilityItemUpdate(BaseModel):
    status: Literal["pending", "requested", "fulfilled", "not_applicable", "blocked"]
    evidence: dict = Field(default_factory=dict)


class PayabilityChecklistView(BaseModel):
    invoice_id: uuid.UUID
    folio: str
    payer_id: uuid.UUID
    payer_name: str
    status: Literal["payable", "incomplete", "at_risk", "claimed"]
    completed: int
    total: int
    missing_items: list[str]
    items: list[PayabilityItemView]


class PortalEvidenceCreate(BaseModel):
    entry_number: str = Field(min_length=1, max_length=120)
    uploaded_at: datetime
    evidence_reference: str = Field(min_length=1, max_length=500)


class PreventiveConfirmationCreate(BaseModel):
    approval_status: Literal["approved", "rejected"]
    approved_at: datetime
    scheduled_payment_date: date | None = None
    reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_schedule(self) -> "PreventiveConfirmationCreate":
        if self.approval_status == "approved" and self.scheduled_payment_date is None:
            raise ValueError("Una aprobación debe incluir la fecha programada de pago")
        if self.approval_status == "rejected" and self.scheduled_payment_date is not None:
            raise ValueError("Un pago rechazado no puede tener fecha programada")
        return self


class DelayCauseUpdate(BaseModel):
    category: Literal[
        "sii_acceptance",
        "purchase_order",
        "hes_conformity",
        "supplier_portal",
        "payment_data",
        "payer_liquidity",
        "commercial_dispute",
        "other",
    ]
    detail: str | None = Field(default=None, max_length=1000)


class DelayCauseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    category: str
    detail: str | None
    source: str
    updated_at: datetime


class DelayCauseSummary(BaseModel):
    category: str
    invoice_count: int
    total_amount: Decimal


class ClientBaselineUpdate(BaseModel):
    baseline_dso: Decimal | None = Field(default=None, ge=0)
    baseline_on_time_percent: Decimal | None = Field(default=None, ge=0, le=100)
    baseline_late_distribution: dict = Field(default_factory=dict)


class MessageTemplateCreate(BaseModel):
    client_id: uuid.UUID
    template_key: str = Field(pattern=r"^[a-z0-9_]{2,80}$")
    channel: Literal["email", "whatsapp_assisted"]
    stage: Literal[
        "emission", "documental", "preventive", "due", "early_arrears", "escalation"
    ]
    recipient_role: Literal["client", "requester", "accounts_payable"]
    tone: Literal["cordial", "direct", "formal"]
    subject_template: str | None = Field(default=None, max_length=500)
    body_template: str = Field(min_length=10, max_length=10000)
    approved: bool = False


class MessageTemplateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    template_key: str
    version: int
    channel: str
    stage: str
    recipient_role: str
    tone: str
    subject_template: str | None
    body_template: str
    approved: bool
    active: bool
    created_at: datetime


class CommunicationMessageView(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID | None
    payer_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    thread_id: uuid.UUID | None
    template_id: uuid.UUID | None
    workflow_job_id: uuid.UUID | None
    channel: str
    direction: str
    mode: str
    subject: str | None
    body: str
    status: str
    provider_id: str | None
    provider_payload: dict
    safety_status: str
    safety_flags: list[str]
    llm_cost: Decimal
    messaging_cost: Decimal
    cost_currency: str
    sent_at: datetime | None
    received_at: datetime | None
    created_at: datetime
    invoice_ids: list[uuid.UUID] = Field(default_factory=list)
    invoice_folios: list[str] = Field(default_factory=list)
    attachment_names: list[str] = Field(default_factory=list)
    contact_name: str | None = None
    destination: str | None = None


class ContactOptOutCommand(BaseModel):
    client_id: uuid.UUID
    channel: Literal["email", "whatsapp"]
    opted_out: bool
    reason: str | None = Field(default=None, max_length=500)


class CommunicationContactView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    payer_id: uuid.UUID
    name: str
    role: str
    email: str | None
    phone: str | None
    opted_out_email: bool
    opted_out_whatsapp: bool


class InboundAttachmentCreate(BaseModel):
    original_name: str = Field(min_length=1, max_length=300)
    kind: str = Field(default="reply_attachment", min_length=2, max_length=80)
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class InboundMessageCreate(BaseModel):
    client_id: uuid.UUID
    channel: Literal["email", "whatsapp"]
    provider_id: str = Field(min_length=2, max_length=200)
    sender: str = Field(min_length=3, max_length=320)
    external_thread_key: str | None = Field(default=None, max_length=255)
    in_reply_to_provider_id: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, max_length=20000)
    invoice_folios: list[str] = Field(default_factory=list, max_length=100)
    attachments: list[InboundAttachmentCreate] = Field(default_factory=list, max_length=20)
    received_at: datetime | None = None


class ManualResponseCreate(BaseModel):
    client_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    invoice_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    channel: Literal["phone", "personal_email", "other"]
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, max_length=20000)
    received_at: datetime | None = None


class DeliveryStatusUpdate(BaseModel):
    client_id: uuid.UUID
    status: Literal["delivered", "read", "failed"]
    occurred_at: datetime | None = None
    detail: str | None = Field(default=None, max_length=1000)


ClassificationCategory = Literal[
    "paid",
    "payment_scheduled",
    "missing_oc_hes",
    "supplier_data_issue",
    "invoice_disputed",
    "payment_promise",
    "dispute",
    "document_request",
    "wrong_contact",
    "other",
]


class MessageClassificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    message_id: uuid.UUID
    invoice_id: uuid.UUID | None
    version: int
    category: str
    confidence: Decimal
    extracted_data: dict
    evidence: dict
    classifier_kind: str
    classifier_version: str
    prompt_version: str | None
    decision_source: str
    actor_id: uuid.UUID | None
    supersedes_id: uuid.UUID | None
    created_at: datetime


class ExceptionCaseView(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID | None
    message_id: uuid.UUID | None
    classification_id: uuid.UUID | None
    assigned_to: uuid.UUID | None
    kind: str
    status: str
    priority: int
    detail: dict
    human_minutes: Decimal
    resolved_at: datetime | None
    resolution: dict
    created_at: datetime
    classification: MessageClassificationView | None = None
    context: dict = Field(default_factory=dict)


class ChecklistCorrection(BaseModel):
    item_id: uuid.UUID
    status: Literal["pending", "requested", "fulfilled", "not_applicable", "blocked"]
    evidence: dict = Field(default_factory=dict)


class ExceptionReviewCommand(BaseModel):
    client_id: uuid.UUID
    category: ClassificationCategory
    extracted_data: dict = Field(default_factory=dict)
    human_minutes: Decimal = Field(default=Decimal("0"), ge=0, le=480)
    note: str | None = Field(default=None, max_length=2000)
    checklist_updates: list[ChecklistCorrection] = Field(default_factory=list, max_length=30)
    workflow_stage: Literal[
        "emission",
        "documental",
        "preventive",
        "due",
        "early_arrears",
        "escalation",
        "closed",
    ] | None = None


class ExceptionResponseDraftCreate(BaseModel):
    client_id: uuid.UUID
    channel: Literal["email", "whatsapp_assisted"]
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=10, max_length=10000)


class ExceptionResponseSuggestion(BaseModel):
    exception_id: uuid.UUID
    channel: str
    subject: str | None
    body: str
    requires_human_review: bool = True
    external_delivery: bool = False


class EvaluationSetView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    version: int
    status: str
    anonymization_version: str
    sample_count: int
    metrics: dict
    frozen_at: datetime | None
    created_at: datetime
    examples: list[dict] = Field(default_factory=list)


class EvaluationReportView(BaseModel):
    client_id: uuid.UUID
    generated_at: datetime
    total_examples: int
    correct_count: int
    error_count: int
    reviewed_cases: int
    corrected_cases: int
    total_human_minutes: Decimal
    average_human_minutes: Decimal
    categories: list[dict] = Field(default_factory=list)
    recent_errors: list[dict] = Field(default_factory=list)


class ClassificationPolicyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    category: str
    mode: str
    minimum_precision: Decimal
    minimum_samples: int
    current_precision: Decimal | None
    sample_count: int
    eligible_for_automation: bool
    updated_at: datetime


class ClassificationPolicyUpdate(BaseModel):
    client_id: uuid.UUID
    mode: Literal["supervised", "automatic"]


class ExceptionEscalationCommand(BaseModel):
    client_id: uuid.UUID
    note: str = Field(min_length=3, max_length=2000)


class PayerProfileProposalCreate(BaseModel):
    client_id: uuid.UUID
    exception_id: uuid.UUID
    proposed_changes: dict
    rationale: str = Field(min_length=3, max_length=2000)


class PayerProfileProposalChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operational_requirements: PayerRequirements | None = None
    supplier_portal_url: str | None = Field(default=None, max_length=500)
    supplier_portal_instructions: str | None = Field(default=None, max_length=4000)
    corporate_channels: dict | None = None
    payment_cycle: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def require_explicit_change(self) -> "PayerProfileProposalChanges":
        if not self.model_fields_set:
            raise ValueError("Debe proponer al menos un cambio")
        if (
            "operational_requirements" in self.model_fields_set
            and self.operational_requirements is None
        ):
            raise ValueError("Los requisitos operativos no pueden ser nulos")
        if "corporate_channels" in self.model_fields_set and self.corporate_channels is None:
            raise ValueError("Los canales corporativos no pueden ser nulos")
        return self


class PayerProfileProposalDecision(BaseModel):
    client_id: uuid.UUID
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


class PayerProfileProposalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    payer_id: uuid.UUID
    exception_id: uuid.UUID | None
    classification_id: uuid.UUID | None
    status: str
    proposed_changes: dict
    rationale: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class PilotTrendPoint(BaseModel):
    week_start: date
    week_end: date
    settled_invoices: int
    on_time_percent: Decimal | None
    average_dso: Decimal | None
    verified_amount: Decimal


class PilotMetricsView(BaseModel):
    client_id: uuid.UUID
    client_name: str
    date_from: date
    date_to: date
    baseline: dict[str, Any]
    outcomes: dict[str, Any]
    operations: dict[str, Any]
    economics: dict[str, Any]
    assumptions: dict[str, Any]
    delay_causes: list[dict[str, Any]] = Field(default_factory=list)
    resolution_times: list[dict[str, Any]] = Field(default_factory=list)
    trend: list[PilotTrendPoint] = Field(default_factory=list)
    generated_at: datetime


class ClientTrendView(BaseModel):
    client_id: uuid.UUID
    client_name: str
    date_from: date
    date_to: date
    baseline: dict[str, Any]
    outcomes: dict[str, Any]
    trend: list[PilotTrendPoint] = Field(default_factory=list)


class PilotLogCreate(BaseModel):
    client_id: uuid.UUID
    entry_type: Literal["decision", "incident", "manual_work", "rule_change", "learning"]
    severity: Literal["info", "warning", "critical"] = "info"
    title: str = Field(min_length=3, max_length=200)
    detail: str = Field(min_length=3, max_length=4000)
    occurred_on: date
    human_minutes: Decimal = Field(default=Decimal("0"), ge=0, le=1440)
    related_invoice_id: uuid.UUID | None = None


class PilotLogResolve(BaseModel):
    client_id: uuid.UUID
    resolution_note: str = Field(min_length=3, max_length=2000)


class PilotLogEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    related_invoice_id: uuid.UUID | None
    entry_type: str
    severity: str
    title: str
    detail: str
    status: str
    occurred_on: date
    human_minutes: Decimal
    created_by: uuid.UUID
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime


class ClientExceptionResponseCreate(BaseModel):
    response_type: Literal["approved", "information_provided", "rejected"]
    message: str = Field(min_length=3, max_length=2000)


class ClientEscalatedExceptionView(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID | None
    invoice_folio: str | None
    payer_name: str | None
    kind: str
    priority: int
    note: str
    escalated_at: datetime
    response: dict[str, Any] | None = None


class DemoWalkthroughView(BaseModel):
    client_id: uuid.UUID
    client_name: str
    operation_date: date
    ready_steps: int
    total_steps: int
    steps: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime

