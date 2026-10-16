import hashlib
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType
from app.models import (
    ClassificationPolicy,
    Client,
    Contact,
    EvaluationExample,
    EvaluationSet,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    MessageInvoice,
)
from app.services.classification import CATEGORY_PATTERNS


ANONYMIZATION_VERSION = "local-redaction-v1"
DEFAULT_MINIMUM_PRECISION = Decimal("0.9000")
DEFAULT_MINIMUM_SAMPLES = 20
NEVER_AUTOMATE = {"invoice_disputed", "dispute", "wrong_contact", "other"}


def _redacted_text(db: Session, message: Message) -> str:
    text = f"{message.subject or ''}\n{message.body}".strip()
    replacements: list[tuple[str, str]] = []
    client = db.get(Client, message.client_id)
    contact = db.get(Contact, message.contact_id) if message.contact_id else None
    if client:
        replacements.extend([(client.name, "[EMPRESA]"), (client.rut, "[RUT]")])
    if contact:
        replacements.append((contact.name, "[CONTACTO]"))
        if contact.email:
            replacements.append((contact.email, "[EMAIL]"))
        if contact.phone:
            replacements.append((contact.phone, "[TELEFONO]"))
    invoice_ids = list(
        db.scalars(
            select(MessageInvoice.invoice_id).where(MessageInvoice.message_id == message.id)
        )
    )
    for invoice in db.scalars(select(Invoice).where(Invoice.id.in_(invoice_ids))):
        replacements.extend([(invoice.folio, "[FOLIO]"), (invoice.payer_name, "[PAGADOR]")])
    for raw, replacement in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        if raw:
            text = re.sub(re.escape(raw), replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s()-]{7,}\d", "[TELEFONO]", text)
    text = re.sub(r"\b\d{1,2}(?:\.\d{3}){2}-[\dkK]\b", "[RUT]", text)
    text = re.sub(
        r"(?:\bCLP\s*|\$\s*)[0-9]{1,3}(?:\.[0-9]{3})+",
        "[MONTO]",
        text,
        flags=re.IGNORECASE,
    )
    return text


def ensure_policies(db: Session, client_id: uuid.UUID) -> list[ClassificationPolicy]:
    existing = {
        policy.category: policy
        for policy in db.scalars(
            select(ClassificationPolicy).where(ClassificationPolicy.client_id == client_id)
        )
    }
    for category in [*CATEGORY_PATTERNS.keys(), "other"]:
        if category not in existing:
            policy = ClassificationPolicy(
                client_id=client_id,
                category=category,
                mode="supervised",
                minimum_precision=DEFAULT_MINIMUM_PRECISION,
                minimum_samples=DEFAULT_MINIMUM_SAMPLES,
                current_precision=None,
                sample_count=0,
                eligible_for_automation=False,
            )
            db.add(policy)
            existing[category] = policy
    db.flush()
    return [existing[category] for category in [*CATEGORY_PATTERNS.keys(), "other"]]


def get_or_create_open_set(db: Session, client_id: uuid.UUID) -> EvaluationSet:
    evaluation_set = db.scalar(
        select(EvaluationSet).where(
            EvaluationSet.client_id == client_id,
            EvaluationSet.status == "open",
        )
    )
    if evaluation_set is not None:
        return evaluation_set
    version = int(
        db.scalar(
            select(func.coalesce(func.max(EvaluationSet.version), 0)).where(
                EvaluationSet.client_id == client_id
            )
        )
        or 0
    ) + 1
    evaluation_set = EvaluationSet(
        client_id=client_id,
        version=version,
        status="open",
        anonymization_version=ANONYMIZATION_VERSION,
        sample_count=0,
        metrics={},
    )
    db.add(evaluation_set)
    db.flush()
    return evaluation_set


def recompute_metrics(db: Session, client_id: uuid.UUID) -> dict[str, dict]:
    examples = list(
        db.scalars(
            select(EvaluationExample).where(EvaluationExample.client_id == client_id)
        )
    )
    metrics: dict[str, dict] = {}
    for category in [*CATEGORY_PATTERNS.keys(), "other"]:
        category_examples = [item for item in examples if item.predicted_category == category]
        correct = sum(1 for item in category_examples if item.correct)
        count = len(category_examples)
        precision = (Decimal(correct) / Decimal(count)).quantize(Decimal("0.0001")) if count else None
        metrics[category] = {
            "sample_count": count,
            "correct_count": correct,
            "precision": str(precision) if precision is not None else None,
        }
    for policy in ensure_policies(db, client_id):
        metric = metrics[policy.category]
        policy.sample_count = metric["sample_count"]
        policy.current_precision = (
            Decimal(metric["precision"]) if metric["precision"] is not None else None
        )
        policy.eligible_for_automation = (
            policy.category not in NEVER_AUTOMATE
            and policy.sample_count >= policy.minimum_samples
            and policy.current_precision is not None
            and policy.current_precision >= policy.minimum_precision
        )
        if policy.mode == "automatic" and not policy.eligible_for_automation:
            policy.mode = "supervised"
    open_set = db.scalar(
        select(EvaluationSet).where(
            EvaluationSet.client_id == client_id,
            EvaluationSet.status == "open",
        )
    )
    if open_set:
        open_examples = list(
            db.scalars(
                select(EvaluationExample).where(
                    EvaluationExample.evaluation_set_id == open_set.id
                )
            )
        )
        open_set.sample_count = len(open_examples)
        open_set.metrics = metrics
    return metrics


def build_evaluation_report(db: Session, client_id: uuid.UUID) -> dict:
    recompute_metrics(db, client_id)
    examples = list(
        db.scalars(
            select(EvaluationExample)
            .where(EvaluationExample.client_id == client_id)
            .order_by(EvaluationExample.created_at, EvaluationExample.id)
        )
    )
    policies = {
        policy.category: policy
        for policy in db.scalars(
            select(ClassificationPolicy).where(ClassificationPolicy.client_id == client_id)
        )
    }
    categories: list[dict] = []
    for category in [*CATEGORY_PATTERNS.keys(), "other"]:
        predicted = [item for item in examples if item.predicted_category == category]
        actual = [item for item in examples if item.actual_category == category]
        true_positive = sum(
            1
            for item in examples
            if item.predicted_category == category and item.actual_category == category
        )
        precision = (
            (Decimal(true_positive) / Decimal(len(predicted))).quantize(Decimal("0.0001"))
            if predicted
            else None
        )
        recall = (
            (Decimal(true_positive) / Decimal(len(actual))).quantize(Decimal("0.0001"))
            if actual
            else None
        )
        policy = policies[category]
        categories.append(
            {
                "category": category,
                "predicted_count": len(predicted),
                "actual_count": len(actual),
                "correct_count": true_positive,
                "error_count": len(predicted) - true_positive,
                "false_negative_count": len(actual) - true_positive,
                "precision": str(precision) if precision is not None else None,
                "recall": str(recall) if recall is not None else None,
                "mode": policy.mode,
                "minimum_precision": str(policy.minimum_precision),
                "minimum_samples": policy.minimum_samples,
                "eligible_for_automation": policy.eligible_for_automation,
                "permanent_supervision": category in NEVER_AUTOMATE,
            }
        )
    reviewed = list(
        db.scalars(
            select(ExceptionCase).where(
                ExceptionCase.client_id == client_id,
                ExceptionCase.status == "resolved",
            )
        )
    )
    total_minutes = sum(
        (Decimal(item.human_minutes or 0) for item in reviewed), Decimal("0")
    ).quantize(Decimal("0.01"))
    average_minutes = (
        (total_minutes / Decimal(len(reviewed))).quantize(Decimal("0.01"))
        if reviewed
        else Decimal("0.00")
    )
    errors = [item for item in reversed(examples) if not item.correct][:50]
    return {
        "client_id": client_id,
        "generated_at": datetime.now(timezone.utc),
        "total_examples": len(examples),
        "correct_count": sum(1 for item in examples if item.correct),
        "error_count": sum(1 for item in examples if not item.correct),
        "reviewed_cases": len(reviewed),
        "corrected_cases": sum(
            1 for item in reviewed if (item.resolution or {}).get("decision") == "corrected"
        ),
        "total_human_minutes": total_minutes,
        "average_human_minutes": average_minutes,
        "categories": categories,
        "recent_errors": [
            {
                "example_id": str(item.id),
                "evaluation_set_id": str(item.evaluation_set_id),
                "predicted_category": item.predicted_category,
                "actual_category": item.actual_category,
                "redacted_text": item.redacted_text,
                "created_at": item.created_at,
            }
            for item in errors
        ],
    }


def add_review_example(
    db: Session,
    *,
    original: MessageClassification,
    human_decision: MessageClassification,
    actor_id: uuid.UUID,
) -> EvaluationExample:
    existing = db.scalar(
        select(EvaluationExample).where(
            EvaluationExample.classification_id == original.id
        )
    )
    if existing is not None:
        return existing
    message = db.get(Message, original.message_id)
    if message is None:
        raise ValueError("No se encontró el mensaje de la clasificación")
    evaluation_set = get_or_create_open_set(db, original.client_id)
    redacted = _redacted_text(db, message)
    source_hash = hashlib.sha256(
        f"{original.client_id}:{original.message_id}:{redacted}".encode("utf-8")
    ).hexdigest()
    example = EvaluationExample(
        client_id=original.client_id,
        evaluation_set_id=evaluation_set.id,
        classification_id=original.id,
        source_hash=source_hash,
        redacted_text=redacted,
        predicted_category=original.category,
        actual_category=human_decision.category,
        correct=original.category == human_decision.category,
        metadata_json={
            "classifier_version": original.classifier_version,
            "classification_version": original.version,
            "human_decision_version": human_decision.version,
            "anonymization_version": ANONYMIZATION_VERSION,
        },
    )
    db.add(example)
    db.flush()
    metrics = recompute_metrics(db, original.client_id)
    record_event(
        db,
        client_id=original.client_id,
        invoice_id=original.invoice_id,
        event_type="evaluation.example_added",
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="supervised",
        payload={
            "evaluation_set_id": str(evaluation_set.id),
            "evaluation_set_version": evaluation_set.version,
            "example_id": str(example.id),
            "predicted_category": original.category,
            "actual_category": human_decision.category,
            "correct": example.correct,
            "category_metrics": metrics[original.category],
            "contains_raw_personal_data": False,
        },
    )
    return example


def freeze_evaluation_set(
    db: Session, evaluation_set: EvaluationSet, *, actor_id: uuid.UUID
) -> EvaluationSet:
    if evaluation_set.status == "frozen":
        return evaluation_set
    evaluation_set.metrics = recompute_metrics(db, evaluation_set.client_id)
    evaluation_set.status = "frozen"
    evaluation_set.frozen_at = datetime.now(timezone.utc)
    record_event(
        db,
        client_id=evaluation_set.client_id,
        event_type="evaluation.set_frozen",
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="supervised",
        payload={
            "evaluation_set_id": str(evaluation_set.id),
            "version": evaluation_set.version,
            "sample_count": evaluation_set.sample_count,
            "metrics": evaluation_set.metrics,
        },
    )
    return evaluation_set


def update_policy_mode(
    db: Session,
    policy: ClassificationPolicy,
    *,
    mode: str,
    actor_id: uuid.UUID,
) -> ClassificationPolicy:
    recompute_metrics(db, policy.client_id)
    if mode == "automatic" and not policy.eligible_for_automation:
        raise ValueError(
            "La categoría no alcanza precisión y muestra mínimas, o requiere revisión obligatoria"
        )
    previous = policy.mode
    policy.mode = mode
    record_event(
        db,
        client_id=policy.client_id,
        event_type="classification.policy_changed",
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="manual",
        payload={
            "category": policy.category,
            "from": previous,
            "to": mode,
            "precision": str(policy.current_precision) if policy.current_precision else None,
            "sample_count": policy.sample_count,
            "minimum_precision": str(policy.minimum_precision),
            "minimum_samples": policy.minimum_samples,
            "eligible": policy.eligible_for_automation,
        },
    )
    return policy
