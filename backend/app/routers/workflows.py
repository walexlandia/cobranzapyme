import uuid
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import Contract, Invoice, User, WorkflowControl, WorkflowJob, WorkflowState
from app.routers.invoices import _authorized_client
from app.schemas import (
    WorkflowControlCommand,
    WorkflowControlView,
    WorkflowJobView,
    WorkflowRunRequest,
    WorkflowRunResult,
    WorkflowSimulationItem,
    WorkflowSimulationRequest,
    WorkflowStateView,
)
from app.security import CurrentUser, require_roles
from app.schemas import ContractRules
from app.services.workflow_engine import run_scheduler_cycle, simulate_invoice


router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


@router.post("/run", response_model=WorkflowRunResult)
def run_cycle(
    payload: WorkflowRunRequest,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowRunResult:
    if payload.client_id is None:
        raise HTTPException(status_code=422, detail="client_id es obligatorio para el ciclo manual")
    result = run_scheduler_cycle(
        db,
        client_id=payload.client_id,
        mode=payload.mode,
        actor_id=user.id,
    )
    if result.clients_processed == 0:
        raise HTTPException(status_code=409, detail="El cliente no tiene un contrato activo")
    return WorkflowRunResult(**result.__dict__)


@router.post("/simulate", response_model=list[WorkflowSimulationItem])
def simulate_cycle(
    payload: WorkflowSimulationRequest,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkflowSimulationItem]:
    contract = db.scalar(
        select(Contract).where(
            Contract.client_id == payload.client_id,
            Contract.active.is_(True),
        )
    )
    if contract is None:
        raise HTTPException(status_code=409, detail="El cliente no tiene un contrato activo")
    query = select(Invoice).where(Invoice.client_id == payload.client_id)
    if payload.invoice_id is not None:
        query = query.where(Invoice.id == payload.invoice_id)
    invoices = list(db.scalars(query.order_by(Invoice.due_on, Invoice.folio)))
    if payload.invoice_id is not None and not invoices:
        raise HTTPException(status_code=404, detail="Factura no encontrada para el cliente")
    controls = list(
        db.scalars(select(WorkflowControl).where(WorkflowControl.client_id == payload.client_id))
    )
    rules = ContractRules.model_validate(contract.rules)
    return [
        simulate_invoice(
            invoice,
            contract=contract,
            rules=rules,
            simulation_date=payload.simulation_date,
            controls=controls,
        )
        for invoice in invoices
    ]


@router.get("/states", response_model=list[WorkflowStateView])
def list_states(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[WorkflowState]:
    scoped_client = _authorized_client(user, client_id)
    return list(
        db.scalars(
            select(WorkflowState)
            .where(WorkflowState.client_id == scoped_client)
            .order_by(WorkflowState.updated_at.desc())
        )
    )


@router.get("/jobs", response_model=list[WorkflowJobView])
def list_jobs(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[WorkflowJob]:
    return list(
        db.scalars(
            select(WorkflowJob)
            .where(WorkflowJob.client_id == client_id)
            .order_by(WorkflowJob.scheduled_for.desc())
            .limit(limit)
        )
    )


@router.get("/controls", response_model=list[WorkflowControlView])
def list_controls(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> list[WorkflowControl]:
    return list(
        db.scalars(
            select(WorkflowControl)
            .where(WorkflowControl.client_id == client_id)
            .order_by(WorkflowControl.updated_at.desc())
        )
    )


@router.post("/controls", response_model=WorkflowControlView)
def change_control(
    payload: WorkflowControlCommand,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowControl:
    invoice_id: uuid.UUID | None = None
    if payload.scope_type == "invoice":
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.id == payload.scope_id,
                Invoice.client_id == payload.client_id,
            )
        )
        if invoice is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada para el cliente")
        invoice_id = invoice.id
    else:
        payer_used_by_client = db.scalar(
            select(Invoice.id).where(
                Invoice.client_id == payload.client_id,
                Invoice.payer_id == payload.scope_id,
            ).limit(1)
        )
        if payer_used_by_client is None:
            raise HTTPException(status_code=404, detail="Pagador no asociado al cliente")

    control = db.scalar(
        select(WorkflowControl).where(
            WorkflowControl.client_id == payload.client_id,
            WorkflowControl.scope_type == payload.scope_type,
            WorkflowControl.scope_id == payload.scope_id,
        )
    )
    if control is None:
        control = WorkflowControl(
            client_id=payload.client_id,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
        )
        db.add(control)

    if payload.action == "pause":
        control.status = "paused"
        control.reason = payload.reason or "operator"
        control.resume_at = payload.resume_at
        if control.resume_at is not None and control.resume_at.tzinfo is None:
            control.resume_at = control.resume_at.replace(tzinfo=timezone.utc)
        event_type = "workflow.paused"
    else:
        control.status = "active"
        control.reason = None
        control.resume_at = None
        event_type = "workflow.resumed"

    record_event(
        db,
        client_id=payload.client_id,
        invoice_id=invoice_id,
        event_type=event_type,
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="manual",
        payload={
            "scope_type": payload.scope_type,
            "scope_id": str(payload.scope_id),
            "reason": control.reason,
            "resume_at": control.resume_at.isoformat() if control.resume_at else None,
        },
    )
    db.commit()
    db.refresh(control)
    return control
