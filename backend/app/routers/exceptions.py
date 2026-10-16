import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import (
    ClassificationPolicy,
    EvaluationExample,
    EvaluationSet,
    Event,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    PayabilityItem,
    PayerProfile,
    PayerProfileProposal,
    User,
)
from app.schemas import (
    ClassificationPolicyUpdate,
    ClassificationPolicyView,
    EvaluationSetView,
    EvaluationReportView,
    ExceptionCaseView,
    ExceptionEscalationCommand,
    ExceptionReviewCommand,
    MessageClassificationView,
    PayerProfileProposalCreate,
    PayerProfileProposalChanges,
    PayerProfileProposalDecision,
    PayerProfileProposalView,
)
from app.security import require_roles
from app.services.classification import classify_message, review_exception
from app.services.evaluation import (
    build_evaluation_report,
    ensure_policies,
    freeze_evaluation_set,
    recompute_metrics,
    update_policy_mode,
)
from app.services.payability import create_profile_revision, get_or_create_profile


router = APIRouter(prefix="/api/v1", tags=["supervised-intelligence"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _classification_view(
    classification: MessageClassification | None,
) -> MessageClassificationView | None:
    return (
        MessageClassificationView.model_validate(classification)
        if classification is not None
        else None
    )


def _case_view(db: Session, case: ExceptionCase, *, full: bool) -> ExceptionCaseView:
    classification = (
        db.get(MessageClassification, case.classification_id)
        if case.classification_id
        else None
    )
    message = db.get(Message, case.message_id) if case.message_id else None
    invoice = db.get(Invoice, case.invoice_id) if case.invoice_id else None
    context: dict = {
        "message": (
            {
                "id": str(message.id),
                "channel": message.channel,
                "direction": message.direction,
                "subject": message.subject,
                "body": message.body,
                "received_at": message.received_at,
                "provider_payload": message.provider_payload,
            }
            if message
            else None
        ),
        "invoice": (
            {
                "id": str(invoice.id),
                "folio": invoice.folio,
                "payer_id": str(invoice.payer_id),
                "payer_name": invoice.payer_name,
                "due_on": invoice.due_on,
                "total_amount": invoice.total_amount,
                "currency": invoice.currency,
                "status": invoice.status.value,
            }
            if invoice
            else None
        ),
    }
    if full and invoice is not None:
        context["payability"] = [
            {
                "id": str(item.id),
                "item_type": item.item_type,
                "label": item.label,
                "status": item.status,
                "required": item.required,
                "blocks_payability": item.blocks_payability,
                "responsible_role": item.responsible_role,
                "evidence": item.evidence,
            }
            for item in db.scalars(
                select(PayabilityItem)
                .where(
                    PayabilityItem.client_id == case.client_id,
                    PayabilityItem.invoice_id == invoice.id,
                )
                .order_by(PayabilityItem.created_at, PayabilityItem.id)
            )
        ]
        profile = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == invoice.payer_id))
        context["payer_profile"] = (
            {
                "operational_requirements": profile.operational_requirements,
                "supplier_portal_url": profile.supplier_portal_url,
                "supplier_portal_instructions": profile.supplier_portal_instructions,
                "payment_cycle": profile.payment_cycle,
                "corporate_channels": profile.corporate_channels,
            }
            if profile
            else None
        )
        context["events"] = [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "actor_type": event.actor_type.value,
                "mode": event.mode,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in db.scalars(
                select(Event)
                .where(Event.client_id == case.client_id, Event.invoice_id == invoice.id)
                .order_by(Event.created_at, Event.id)
                .limit(200)
            )
        ]
        if message is not None:
            context["classification_history"] = [
                MessageClassificationView.model_validate(item).model_dump(mode="json")
                for item in db.scalars(
                    select(MessageClassification)
                    .where(
                        MessageClassification.client_id == case.client_id,
                        MessageClassification.message_id == message.id,
                    )
                    .order_by(MessageClassification.version)
                )
            ]
    return ExceptionCaseView(
        id=case.id,
        client_id=case.client_id,
        invoice_id=case.invoice_id,
        message_id=case.message_id,
        classification_id=case.classification_id,
        assigned_to=case.assigned_to,
        kind=case.kind,
        status=case.status,
        priority=case.priority,
        detail=case.detail,
        human_minutes=case.human_minutes,
        resolved_at=case.resolved_at,
        resolution=case.resolution,
        created_at=case.created_at,
        classification=_classification_view(classification),
        context=context,
    )


@router.get("/exceptions", response_model=list[ExceptionCaseView])
def list_exceptions(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[str | None, Query(pattern="^(open|resolved)$")] = "open",
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ExceptionCaseView]:
    query = select(ExceptionCase).where(ExceptionCase.client_id == client_id)
    if status:
        query = query.where(ExceptionCase.status == status)
    cases = list(
        db.scalars(
            query.order_by(
                ExceptionCase.priority.desc(),
                ExceptionCase.created_at,
                ExceptionCase.id,
            ).limit(limit)
        )
    )
    return [_case_view(db, case, full=False) for case in cases]


@router.get("/exceptions/{exception_id}", response_model=ExceptionCaseView)
def get_exception(
    exception_id: uuid.UUID,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> ExceptionCaseView:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == exception_id,
            ExceptionCase.client_id == client_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    return _case_view(db, case, full=True)


@router.post(
    "/classifications/messages/{message_id}/run",
    response_model=MessageClassificationView,
)
def run_local_classification(
    message_id: uuid.UUID,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> MessageClassification:
    message = db.scalar(
        select(Message).where(Message.id == message_id, Message.client_id == client_id)
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    try:
        classification = classify_message(db, message)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(classification)
    return classification


@router.post("/exceptions/{exception_id}/review", response_model=ExceptionCaseView)
def resolve_exception(
    exception_id: uuid.UUID,
    payload: ExceptionReviewCommand,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionCaseView:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == exception_id,
            ExceptionCase.client_id == payload.client_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    if case.status != "open":
        raise HTTPException(status_code=409, detail="La excepción ya fue resuelta")
    try:
        review_exception(
            db,
            case,
            category=payload.category,
            extracted_data=payload.extracted_data,
            human_minutes=payload.human_minutes,
            note=payload.note,
            checklist_updates=payload.checklist_updates,
            workflow_stage=payload.workflow_stage,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(case)
    return _case_view(db, case, full=True)


@router.post("/exceptions/{exception_id}/escalate", response_model=ExceptionCaseView)
def escalate_exception(
    exception_id: uuid.UUID,
    payload: ExceptionEscalationCommand,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionCaseView:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == exception_id,
            ExceptionCase.client_id == payload.client_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    if case.status != "open":
        raise HTTPException(status_code=409, detail="Sólo se escalan excepciones abiertas")
    escalated_at = datetime.now(timezone.utc)
    case.priority = 100
    case.detail = {
        **(case.detail or {}),
        "client_escalation": {
            "note": payload.note,
            "actor_id": str(user.id),
            "created_at": escalated_at.isoformat(),
            "external_delivery": False,
        },
    }
    record_event(
        db,
        client_id=case.client_id,
        invoice_id=case.invoice_id,
        event_type="exception.escalated_to_client",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="manual",
        payload={
            "exception_id": str(case.id),
            "note": payload.note,
            "external_delivery": False,
        },
    )
    db.commit()
    db.refresh(case)
    return _case_view(db, case, full=True)


def _evaluation_set_view(db: Session, evaluation_set: EvaluationSet) -> EvaluationSetView:
    examples = [
        {
            "id": str(example.id),
            "source_hash": example.source_hash,
            "redacted_text": example.redacted_text,
            "predicted_category": example.predicted_category,
            "actual_category": example.actual_category,
            "correct": example.correct,
            "metadata": example.metadata_json,
            "created_at": example.created_at,
        }
        for example in db.scalars(
            select(EvaluationExample)
            .where(EvaluationExample.evaluation_set_id == evaluation_set.id)
            .order_by(EvaluationExample.created_at, EvaluationExample.id)
        )
    ]
    return EvaluationSetView(
        id=evaluation_set.id,
        client_id=evaluation_set.client_id,
        version=evaluation_set.version,
        status=evaluation_set.status,
        anonymization_version=evaluation_set.anonymization_version,
        sample_count=evaluation_set.sample_count,
        metrics=evaluation_set.metrics,
        frozen_at=evaluation_set.frozen_at,
        created_at=evaluation_set.created_at,
        examples=examples,
    )


@router.get("/evaluation/sets", response_model=list[EvaluationSetView])
def list_evaluation_sets(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> list[EvaluationSetView]:
    sets = list(
        db.scalars(
            select(EvaluationSet)
            .where(EvaluationSet.client_id == client_id)
            .order_by(EvaluationSet.version.desc())
        )
    )
    return [_evaluation_set_view(db, item) for item in sets]


@router.get("/evaluation/report", response_model=EvaluationReportView)
def evaluation_report(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> dict:
    report = build_evaluation_report(db, client_id)
    db.commit()
    return report


@router.get("/evaluation/report.csv", response_class=Response)
def export_evaluation_report(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> Response:
    report = build_evaluation_report(db, client_id)
    db.commit()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "category",
            "predicted_count",
            "actual_count",
            "correct_count",
            "error_count",
            "false_negative_count",
            "precision",
            "recall",
            "mode",
            "eligible_for_automation",
            "permanent_supervision",
        ],
    )
    writer.writeheader()
    for category in report["categories"]:
        writer.writerow({key: category.get(key) for key in writer.fieldnames})
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="evaluacion-g2-{client_id}.csv"'
        },
    )


@router.post("/evaluation/sets/{set_id}/freeze", response_model=EvaluationSetView)
def freeze_set(
    set_id: uuid.UUID,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> EvaluationSetView:
    evaluation_set = db.scalar(
        select(EvaluationSet).where(
            EvaluationSet.id == set_id,
            EvaluationSet.client_id == client_id,
        )
    )
    if evaluation_set is None:
        raise HTTPException(status_code=404, detail="Set de evaluación no encontrado")
    freeze_evaluation_set(db, evaluation_set, actor_id=user.id)
    db.commit()
    db.refresh(evaluation_set)
    return _evaluation_set_view(db, evaluation_set)


@router.get("/classification-policies", response_model=list[ClassificationPolicyView])
def list_classification_policies(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> list[ClassificationPolicy]:
    policies = ensure_policies(db, client_id)
    recompute_metrics(db, client_id)
    db.commit()
    return policies


@router.post(
    "/classification-policies/{policy_id}", response_model=ClassificationPolicyView
)
def change_classification_policy(
    policy_id: uuid.UUID,
    payload: ClassificationPolicyUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> ClassificationPolicy:
    policy = db.scalar(
        select(ClassificationPolicy).where(
            ClassificationPolicy.id == policy_id,
            ClassificationPolicy.client_id == payload.client_id,
        )
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    try:
        update_policy_mode(db, policy, mode=payload.mode, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/payer-profile-proposals", response_model=list[PayerProfileProposalView])
def list_profile_proposals(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: str | None = "pending",
) -> list[PayerProfileProposal]:
    query = select(PayerProfileProposal).where(PayerProfileProposal.client_id == client_id)
    if status:
        query = query.where(PayerProfileProposal.status == status)
    return list(db.scalars(query.order_by(PayerProfileProposal.created_at.desc())))


@router.post("/payer-profile-proposals", response_model=PayerProfileProposalView)
def create_profile_proposal(
    payload: PayerProfileProposalCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PayerProfileProposal:
    case = db.scalar(
        select(ExceptionCase).where(
            ExceptionCase.id == payload.exception_id,
            ExceptionCase.client_id == payload.client_id,
        )
    )
    invoice = db.get(Invoice, case.invoice_id) if case and case.invoice_id else None
    if case is None or invoice is None:
        raise HTTPException(status_code=409, detail="La excepción no tiene factura y pagador")
    try:
        normalized_changes = PayerProfileProposalChanges.model_validate(
            payload.proposed_changes
        ).model_dump(mode="json", exclude_unset=True)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "Propuesta de ficha inválida", "errors": exc.errors()},
        ) from exc
    proposal = PayerProfileProposal(
        client_id=payload.client_id,
        payer_id=invoice.payer_id,
        exception_id=case.id,
        classification_id=case.classification_id,
        status="pending",
        proposed_changes=normalized_changes,
        rationale=payload.rationale,
    )
    db.add(proposal)
    db.flush()
    record_event(
        db,
        client_id=payload.client_id,
        invoice_id=invoice.id,
        event_type="payer_profile.proposal_created",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="supervised",
        payload={
            "proposal_id": str(proposal.id),
            "payer_id": str(invoice.payer_id),
            "proposed_changes": normalized_changes,
            "applied": False,
        },
    )
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post(
    "/payer-profile-proposals/{proposal_id}/decision",
    response_model=PayerProfileProposalView,
)
def decide_profile_proposal(
    proposal_id: uuid.UUID,
    payload: PayerProfileProposalDecision,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PayerProfileProposal:
    proposal = db.scalar(
        select(PayerProfileProposal).where(
            PayerProfileProposal.id == proposal_id,
            PayerProfileProposal.client_id == payload.client_id,
        )
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="La propuesta ya fue revisada")
    applied = False
    if payload.decision == "approved":
        profile = get_or_create_profile(db, proposal.payer_id)
        try:
            normalized_changes = PayerProfileProposalChanges.model_validate(
                proposal.proposed_changes
            ).model_dump(mode="json", exclude_unset=True)
        except ValidationError as exc:
            raise HTTPException(
                status_code=409,
                detail={"message": "La propuesta almacenada ya no es válida", "errors": exc.errors()},
            ) from exc
        for field, value in normalized_changes.items():
            setattr(profile, field, value)
        create_profile_revision(db, profile, actor_id=user.id)
        applied = True
    proposal.status = payload.decision
    proposal.reviewed_by = user.id
    proposal.reviewed_at = datetime.now(timezone.utc)
    case = db.get(ExceptionCase, proposal.exception_id) if proposal.exception_id else None
    record_event(
        db,
        client_id=proposal.client_id,
        invoice_id=case.invoice_id if case else None,
        event_type="payer_profile.proposal_decided",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="supervised",
        payload={
            "proposal_id": str(proposal.id),
            "payer_id": str(proposal.payer_id),
            "decision": payload.decision,
            "note": payload.note,
            "applied": applied,
        },
    )
    db.commit()
    db.refresh(proposal)
    return proposal
