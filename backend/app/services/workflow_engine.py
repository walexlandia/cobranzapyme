import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType, InvoiceStatus
from app.models import (
    Contact,
    Contract,
    Invoice,
    PayabilityItem,
    PayerProfile,
    WorkflowControl,
    WorkflowJob,
    WorkflowState,
)
from app.schemas import (
    ContractRules,
    PayerRequirements,
    WorkflowSimulationItem,
    WorkflowStageWindow,
)
from app.services.communications import prepare_job_message
from app.services.payability import DEFAULT_REQUIREMENTS, checklist_status


STAGE_ACTIONS = {
    "emission": "verify_intake",
    "documental": "resolve_payability",
    "preventive": "confirm_payment_schedule",
    "due": "payment_due",
    "early_arrears": "early_arrears_contact",
    "escalation": "escalate_case",
}
STAGE_PRIORITY = {
    "emission": 0,
    "documental": 1,
    "preventive": 2,
    "due": 3,
    "early_arrears": 4,
    "escalation": 5,
}


@dataclass
class CycleResult:
    clients_processed: int = 0
    invoices_evaluated: int = 0
    states_created: int = 0
    states_updated: int = 0
    jobs_created: int = 0
    jobs_skipped: int = 0

    def merge(self, other: "CycleResult") -> None:
        for field, value in asdict(other).items():
            setattr(self, field, getattr(self, field) + value)


def determine_stage(invoice: Invoice, today: date, rules: ContractRules) -> str:
    if invoice.status in {InvoiceStatus.PAID, InvoiceStatus.VOID}:
        return "closed"
    if today <= invoice.issued_on:
        return "emission"
    preventive_start = invoice.due_on - timedelta(days=rules.preventive_days_before_due)
    if today < preventive_start:
        return "documental"
    if today < invoice.due_on:
        return "preventive"
    if today == invoice.due_on:
        return "due"
    if today <= invoice.due_on + timedelta(days=rules.escalation_days_after_due):
        return "early_arrears"
    return "escalation"


def pause_reason(invoice: Invoice) -> str | None:
    reasons = {
        InvoiceStatus.PAID: "paid",
        InvoiceStatus.VOID: "void",
        InvoiceStatus.CLAIMED: "claimed",
        InvoiceStatus.DISPUTED: "disputed",
    }
    return reasons.get(invoice.status)


def stage_windows(invoice: Invoice, rules: ContractRules) -> list[WorkflowStageWindow]:
    preventive_start = invoice.due_on - timedelta(days=rules.preventive_days_before_due)
    documental_start = invoice.issued_on + timedelta(days=1)
    windows = [
        WorkflowStageWindow(
            stage="emission",
            action_type=STAGE_ACTIONS["emission"],
            starts_on=invoice.issued_on,
            ends_on=invoice.issued_on,
        )
    ]
    if documental_start < preventive_start:
        windows.append(
            WorkflowStageWindow(
                stage="documental",
                action_type=STAGE_ACTIONS["documental"],
                starts_on=documental_start,
                ends_on=preventive_start - timedelta(days=1),
            )
        )
    preventive_start = max(preventive_start, documental_start)
    if preventive_start < invoice.due_on:
        windows.append(
            WorkflowStageWindow(
                stage="preventive",
                action_type=STAGE_ACTIONS["preventive"],
                starts_on=preventive_start,
                ends_on=invoice.due_on - timedelta(days=1),
            )
        )
    windows.extend(
        [
            WorkflowStageWindow(
                stage="due",
                action_type=STAGE_ACTIONS["due"],
                starts_on=invoice.due_on,
                ends_on=invoice.due_on,
            ),
            WorkflowStageWindow(
                stage="early_arrears",
                action_type=STAGE_ACTIONS["early_arrears"],
                starts_on=invoice.due_on + timedelta(days=1),
                ends_on=invoice.due_on + timedelta(days=rules.escalation_days_after_due),
            ),
            WorkflowStageWindow(
                stage="escalation",
                action_type=STAGE_ACTIONS["escalation"],
                starts_on=invoice.due_on
                + timedelta(days=rules.escalation_days_after_due + 1),
                ends_on=None,
            ),
        ]
    )
    return windows


def simulate_invoice(
    invoice: Invoice,
    *,
    contract: Contract,
    rules: ContractRules,
    simulation_date: date,
    controls: list[WorkflowControl],
) -> WorkflowSimulationItem:
    local_timezone = ZoneInfo(rules.timezone)
    simulated_local = datetime.combine(simulation_date, time(12, 0), local_timezone)
    simulated_utc = simulated_local.astimezone(timezone.utc)
    stage = determine_stage(invoice, simulation_date, rules)
    reason = pause_reason(invoice)
    decision_reasons = [
        f"Fecha evaluada: {simulation_date.isoformat()} en {rules.timezone}",
        f"Etapa calculada desde emisión {invoice.issued_on.isoformat()} y vencimiento {invoice.due_on.isoformat()}",
        f"Contrato v{contract.version}: prevención {rules.preventive_days_before_due} días y escalamiento {rules.escalation_days_after_due} días",
    ]
    active_control = next(
        (
            control
            for control in controls
            if control.status == "paused"
            and (control.resume_at is None or control.resume_at > simulated_utc)
            and (
                (control.scope_type == "invoice" and control.scope_id == invoice.id)
                or (control.scope_type == "payer" and control.scope_id == invoice.payer_id)
            )
        ),
        None,
    )
    if active_control is not None:
        reason = f"manual:{active_control.reason or active_control.scope_type}"
        decision_reasons.append(
            f"Control manual activo por {active_control.scope_type}: {active_control.reason or 'sin motivo'}"
        )
    elif reason:
        decision_reasons.append(f"Estado de factura {invoice.status.value}: gestión pausada")

    state_status = "completed" if stage == "closed" else ("paused" if reason else "active")
    action_type = STAGE_ACTIONS.get(stage) if state_status == "active" else None
    scheduled_for = next_allowed_at(simulated_utc, rules) if action_type else None
    if action_type:
        decision_reasons.append(
            f"Acción {action_type} habilitada en la siguiente ventana contractual"
        )

    return WorkflowSimulationItem(
        invoice_id=invoice.id,
        folio=invoice.folio,
        payer_id=invoice.payer_id,
        payer_name=invoice.payer_name,
        simulation_date=simulation_date,
        stage=stage,
        state_status=state_status,
        pause_reason=reason,
        action_type=action_type,
        scheduled_for=scheduled_for,
        contract_id=contract.id,
        contract_version=contract.version,
        decision_reasons=decision_reasons,
        stage_windows=stage_windows(invoice, rules),
    )


def next_allowed_at(now: datetime, rules: ContractRules) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_timezone = ZoneInfo(rules.timezone)
    local_now = now.astimezone(local_timezone)
    for offset in range(8):
        candidate_date = local_now.date() + timedelta(days=offset)
        if candidate_date.weekday() not in rules.allowed_weekdays:
            continue
        start = datetime.combine(candidate_date, rules.window_start, local_timezone)
        end = datetime.combine(candidate_date, rules.window_end, local_timezone)
        if offset == 0 and local_now > end:
            continue
        if offset == 0 and start <= local_now <= end:
            return local_now.replace(second=0, microsecond=0).astimezone(timezone.utc)
        return start.astimezone(timezone.utc)
    raise ValueError("No se encontró un horario permitido en los próximos siete días")


def _week_bounds(moment: datetime, rules: ContractRules) -> tuple[datetime, datetime]:
    local_timezone = ZoneInfo(rules.timezone)
    local = moment.astimezone(local_timezone)
    monday = local.date() - timedelta(days=local.weekday())
    start = datetime.combine(monday, time.min, local_timezone).astimezone(timezone.utc)
    end = datetime.combine(monday + timedelta(days=7), time.min, local_timezone).astimezone(
        timezone.utc
    )
    return start, end


def _recipient_for_stage(contacts: list[Contact], stage: str) -> tuple[Contact | None, str]:
    preferred_role = "requester" if stage in {"emission", "documental"} else "accounts_payable"
    fallback_role = "accounts_payable" if preferred_role == "requester" else "requester"
    recipient = next((item for item in contacts if item.role == preferred_role), None)
    if recipient is None:
        recipient = next((item for item in contacts if item.role == fallback_role), None)
    return recipient, recipient.role if recipient is not None else preferred_role


def _recipient_for_role(
    contacts: list[Contact], preferred_role: str
) -> tuple[Contact | None, str]:
    if preferred_role == "client":
        return None, "client"
    recipient = next((item for item in contacts if item.role == preferred_role), None)
    if recipient is None:
        fallback_role = "accounts_payable" if preferred_role != "accounts_payable" else "requester"
        recipient = next((item for item in contacts if item.role == fallback_role), None)
    return recipient, recipient.role if recipient is not None else preferred_role


def schedule_client_cycle(
    db: Session,
    *,
    contract: Contract,
    now: datetime,
    mode: str,
    actor_id: uuid.UUID | None = None,
) -> CycleResult:
    rules = ContractRules.model_validate(contract.rules)
    scheduled_for = next_allowed_at(now, rules)
    local_date = scheduled_for.astimezone(ZoneInfo(rules.timezone)).date().isoformat()
    week_start, week_end = _week_bounds(scheduled_for, rules)
    result = CycleResult(clients_processed=1)

    contacts_by_payer: dict[uuid.UUID, list[Contact]] = defaultdict(list)
    for contact in db.scalars(
        select(Contact)
        .where(Contact.client_id == contract.client_id)
        .order_by(Contact.created_at, Contact.id)
    ):
        contacts_by_payer[contact.payer_id].append(contact)

    controls = list(
        db.scalars(select(WorkflowControl).where(WorkflowControl.client_id == contract.client_id))
    )
    controls_by_scope = {(control.scope_type, control.scope_id): control for control in controls}
    for control in controls:
        if control.status == "paused" and control.resume_at is not None and control.resume_at <= now:
            control.status = "active"
            resumed_invoice_id = control.scope_id if control.scope_type == "invoice" else None
            record_event(
                db,
                client_id=control.client_id,
                invoice_id=resumed_invoice_id,
                event_type="workflow.resumed",
                actor_type=ActorType.SYSTEM,
                mode="automatic",
                payload={
                    "scope_type": control.scope_type,
                    "scope_id": str(control.scope_id),
                    "reason": "scheduled_resume",
                },
            )

    profiles_by_payer = {
        profile.payer_id: profile
        for profile in db.scalars(select(PayerProfile))
    }
    payability_by_invoice: dict[uuid.UUID, list[PayabilityItem]] = defaultdict(list)
    for item in db.scalars(
        select(PayabilityItem).where(PayabilityItem.client_id == contract.client_id)
    ):
        payability_by_invoice[item.invoice_id].append(item)

    groups: dict[tuple[uuid.UUID, uuid.UUID | None, str], list[dict]] = defaultdict(list)

    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.client_id == contract.client_id)
            .order_by(Invoice.due_on, Invoice.id)
        )
    )
    for invoice in invoices:
        result.invoices_evaluated += 1
        stage = determine_stage(invoice, now.astimezone(ZoneInfo(rules.timezone)).date(), rules)
        reason = pause_reason(invoice)
        manual_control = next(
            (
                control
                for control in (
                    controls_by_scope.get(("invoice", invoice.id)),
                    controls_by_scope.get(("payer", invoice.payer_id)),
                )
                if control is not None and control.status == "paused"
            ),
            None,
        )
        if manual_control is not None:
            reason = f"manual:{manual_control.reason or manual_control.scope_type}"
        state_status = "completed" if stage == "closed" else ("paused" if reason else "active")
        next_run = None if state_status != "active" else scheduled_for
        state = db.scalar(select(WorkflowState).where(WorkflowState.invoice_id == invoice.id))
        if state is None:
            state = WorkflowState(
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                contract_id=contract.id,
                stage=stage,
                status=state_status,
                pause_reason=reason,
                next_run_at=next_run,
            )
            db.add(state)
            result.states_created += 1
            state_changed = True
        else:
            state_changed = (
                state.stage != stage
                or state.status != state_status
                or state.contract_id != contract.id
                or state.pause_reason != reason
            )
            state.contract_id = contract.id
            state.stage = stage
            state.status = state_status
            state.pause_reason = reason
            state.next_run_at = next_run
            if state_changed:
                result.states_updated += 1

        if state_changed:
            record_event(
                db,
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                event_type="workflow.state_changed",
                actor_type=ActorType.HUMAN if actor_id else ActorType.SYSTEM,
                actor_id=actor_id,
                mode=mode,
                payload={
                    "contract_id": str(contract.id),
                    "contract_version": contract.version,
                    "stage": stage,
                    "status": state_status,
                    "pause_reason": reason,
                },
            )

        action_type = STAGE_ACTIONS.get(stage)
        if state_status != "active" or action_type is None:
            result.jobs_skipped += 1
            continue

        profile = profiles_by_payer.get(invoice.payer_id)
        payer_requirements = PayerRequirements.model_validate(
            profile.operational_requirements if profile else DEFAULT_REQUIREMENTS
        )
        invoice_items = payability_by_invoice[invoice.id]
        payability_status, _, _, missing_items = checklist_status(
            invoice,
            invoice_items,
            requirements=payer_requirements,
            today=now.astimezone(ZoneInfo(rules.timezone)).date(),
        )
        missing_item = next(
            (
                item
                for item in invoice_items
                if item.required
                and item.blocks_payability
                and item.status not in {"fulfilled", "not_applicable"}
            ),
            None,
        )
        if stage != "emission" and invoice_items and payability_status != "payable":
            recipient_role = missing_item.responsible_role if missing_item else "client"
            action_type = (
                "request_client_document"
                if recipient_role == "client"
                else "request_missing_requirement"
            )
            recipient, recipient_role = _recipient_for_role(
                contacts_by_payer[invoice.payer_id], recipient_role
            )
        else:
            recipient, recipient_role = _recipient_for_stage(
                contacts_by_payer[invoice.payer_id], stage
            )
        groups[(invoice.payer_id, recipient.id if recipient else None, action_type)].append(
            {
                "invoice": invoice,
                "stage": stage,
                "action_type": action_type,
                "recipient": recipient,
                "recipient_role": recipient_role,
                "payability_status": payability_status,
                "missing_items": missing_items,
            }
        )

    for (payer_id, recipient_id, grouped_action_type), items in groups.items():
        representative = items[0]["invoice"]
        dominant = max(items, key=lambda item: STAGE_PRIORITY[item["stage"]])
        stage = dominant["stage"]
        action_type = grouped_action_type

        weekly_jobs = db.scalar(
            select(func.count())
            .select_from(WorkflowJob)
            .where(
                WorkflowJob.client_id == contract.client_id,
                WorkflowJob.payer_id == payer_id,
                (
                    WorkflowJob.recipient_contact_id == recipient_id
                    if recipient_id is not None
                    else WorkflowJob.recipient_contact_id.is_(None)
                ),
                WorkflowJob.scheduled_for >= week_start,
                WorkflowJob.scheduled_for < week_end,
            )
        ) or 0
        if weekly_jobs >= rules.max_contacts_per_week:
            result.jobs_skipped += len(items)
            continue

        recipient_key = str(recipient_id) if recipient_id else "unassigned"
        idempotency_key = (
            f"{contract.client_id}:{contract.id}:{payer_id}:{recipient_key}:"
            f"{action_type}:{local_date}"
        )
        job_id = uuid.uuid4()
        inserted_job_id = db.execute(
            insert(WorkflowJob)
            .values(
                id=job_id,
                client_id=contract.client_id,
                invoice_id=representative.id,
                payer_id=payer_id,
                recipient_contact_id=recipient_id,
                contract_id=contract.id,
                idempotency_key=idempotency_key,
                action_type=action_type,
                stage=stage,
                status="pending",
                scheduled_for=scheduled_for,
                attempts=0,
                mode=mode,
                payload={
                    "contract_version": contract.version,
                    "channels": rules.channels,
                    "tone": rules.tone,
                    "recipient_role": dominant["recipient_role"],
                    "invoice_ids": [str(item["invoice"].id) for item in items],
                    "invoice_stages": {
                        str(item["invoice"].id): item["stage"] for item in items
                    },
                    "payability_statuses": {
                        str(item["invoice"].id): item["payability_status"] for item in items
                    },
                    "missing_items": {
                        str(item["invoice"].id): item["missing_items"] for item in items
                    },
                },
            )
            .on_conflict_do_nothing(index_elements=[WorkflowJob.idempotency_key])
            .returning(WorkflowJob.id)
        ).scalar_one_or_none()
        if inserted_job_id is None:
            result.jobs_skipped += len(items)
            continue
        for item in items:
            record_event(
                db,
                client_id=contract.client_id,
                invoice_id=item["invoice"].id,
                event_type="workflow.job_scheduled",
                actor_type=ActorType.HUMAN if actor_id else ActorType.SYSTEM,
                actor_id=actor_id,
                mode=mode,
                payload={
                    "job_id": str(inserted_job_id),
                    "action_type": action_type,
                    "stage": item["stage"],
                    "scheduled_for": scheduled_for.isoformat(),
                    "contract_version": contract.version,
                    "grouped_invoice_count": len(items),
                    "payer_id": str(payer_id),
                    "recipient_contact_id": str(recipient_id) if recipient_id else None,
                    "payability_status": item["payability_status"],
                    "missing_items": item["missing_items"],
                },
            )
        result.jobs_created += 1

    return result


def run_scheduler_cycle(
    db: Session,
    *,
    client_id: uuid.UUID | None = None,
    now: datetime | None = None,
    mode: str = "automatic",
    actor_id: uuid.UUID | None = None,
) -> CycleResult:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    query = select(Contract).where(Contract.active.is_(True)).order_by(Contract.client_id)
    if client_id is not None:
        query = query.where(Contract.client_id == client_id)
    contracts = list(db.scalars(query))
    result = CycleResult()
    for contract in contracts:
        result.merge(
            schedule_client_cycle(
                db,
                contract=contract,
                now=moment,
                mode=mode,
                actor_id=actor_id,
            )
        )
    db.commit()
    return result


def process_due_jobs(db: Session, *, now: datetime | None = None, limit: int = 100) -> int:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    jobs = list(
        db.scalars(
            select(WorkflowJob)
            .where(WorkflowJob.status == "pending", WorkflowJob.scheduled_for <= moment)
            .order_by(WorkflowJob.scheduled_for, WorkflowJob.id)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
    )
    for job in jobs:
        job.status = "done"
        job.attempts += 1
        job.processed_at = moment
        invoice_ids = [
            uuid.UUID(value) for value in job.payload.get("invoice_ids", [str(job.invoice_id)])
        ]
        for invoice_id in invoice_ids:
            record_event(
                db,
                client_id=job.client_id,
                invoice_id=invoice_id,
                event_type="workflow.action_ready",
                actor_type=ActorType.SYSTEM,
                mode=job.mode,
                payload={
                    "job_id": str(job.id),
                    "action_type": job.action_type,
                    "stage": job.payload.get("invoice_stages", {}).get(str(invoice_id), job.stage),
                    "contract_id": str(job.contract_id),
                    "contract_version": job.payload.get("contract_version"),
                    "grouped_invoice_count": len(invoice_ids),
                },
            )
        prepare_job_message(db, job)
    db.commit()
    return len(jobs)
