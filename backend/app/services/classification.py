import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType
from app.models import (
    Document,
    ExceptionCase,
    Invoice,
    Message,
    MessageClassification,
    MessageDocument,
    MessageInvoice,
    PayabilityItem,
    WorkflowState,
)
from app.schemas import ChecklistCorrection


CLASSIFIER_VERSION = "local-rules-v1"
LOW_CONFIDENCE_THRESHOLD = Decimal("0.9000")

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "paid": (
        r"\b(?:pago|transferencia)\s+(?:(?:ya\s+)?(?:fue|est[aá])\s+|ya\s+)?(?:realizad[oa]|efectuad[oa])\b",
        r"\badjunto\s+(?:el\s+)?comprobante\b",
        r"\bya\s+(?:fue|est[aá])\s+pagad[oa]\b",
    ),
    "payment_scheduled": (
        r"\b(?:pago|transferencia)\s+(?:qued[oó]\s+)?programad[oa]\b",
        r"\bprogramad[oa]\s+para\s+(?:el\s+)?",
        r"\bfecha\s+de\s+pago\b",
    ),
    "missing_oc_hes": (
        r"\bfalta\s+(?:la\s+|el\s+)?(?:oc|orden\s+de\s+compra|hes)\b",
        r"\bsin\s+(?:oc|orden\s+de\s+compra|hes)\b",
        r"\b(?:oc|hes|orden\s+de\s+compra)\s+(?:est[aá]\s+)?pendiente\b",
    ),
    "supplier_data_issue": (
        r"\bproveedor\s+no\s+(?:est[aá]\s+)?registrad[oa]\b",
        r"\bdatos\s+(?:bancarios|del\s+proveedor)\s+(?:est[aá]n?\s+)?(?:incorrectos|incompletos)\b",
        r"\bactualizar\s+(?:los\s+)?datos\s+del\s+proveedor\b",
    ),
    "invoice_disputed": (
        r"\bfactura\s+(?:fue\s+|est[aá]\s+)?(?:reclamada|rechazada|observada)\b",
        r"\brechazo\s+de\s+(?:la\s+)?factura\b",
    ),
    "payment_promise": (
        r"\b(?:pagaremos|transferiremos|abonaremos)\b",
        r"\bcompromiso\s+de\s+pago\b",
        r"\bnos\s+comprometemos\s+a\s+pagar\b",
    ),
    "dispute": (
        r"\b(?:monto|servicio|cobro)\s+(?:no\s+corresponde|incorrecto)\b",
        r"\b(?:disputa|discrepancia|controversia)\b",
        r"\bno\s+reconocemos\s+(?:la\s+)?(?:deuda|factura)\b",
    ),
    "document_request": (
        r"\b(?:env[ií]e|enviar|adjunte|adjuntar|necesitamos)\b.{0,50}\b(?:factura|oc|hes|gu[ií]a|certificado|documento)\b",
        r"\bsolicitamos\s+(?:la\s+|el\s+)?(?:factura|oc|hes|documento)\b",
    ),
    "wrong_contact": (
        r"\bcontacto\s+equivocado\b",
        r"\bno\s+corresponde\s+a\s+(?:este\s+)?(?:correo|n[uú]mero|contacto)\b",
        r"\bcontacte\s+a\b",
    ),
}

MANDATORY_REVIEW_CATEGORIES = {
    "invoice_disputed",
    "dispute",
    "wrong_contact",
    "other",
}


def _classification_result(text: str) -> tuple[str, Decimal, dict]:
    matches: dict[str, list[str]] = {}
    for category, patterns in CATEGORY_PATTERNS.items():
        category_matches = [
            match.group(0)
            for pattern in patterns
            if (match := re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL))
        ]
        if category_matches:
            matches[category] = category_matches
    if not matches:
        return "other", Decimal("0.3500"), {"matched_phrases": {}, "ambiguous": False}
    ranked = sorted(matches.items(), key=lambda item: (-len(item[1]), list(CATEGORY_PATTERNS).index(item[0])))
    category, phrases = ranked[0]
    tied = len(ranked) > 1 and len(ranked[1][1]) == len(phrases)
    confidence = Decimal("0.6800") if tied else min(
        Decimal("0.9800"), Decimal("0.9200") + Decimal("0.0200") * (len(phrases) - 1)
    )
    return category, confidence, {
        "matched_phrases": matches,
        "ambiguous": tied,
        "candidate_categories": [item[0] for item in ranked],
    }


def _extract_dates(text: str) -> list[str]:
    values: set[str] = set()
    for raw in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
        try:
            values.add(date.fromisoformat(raw).isoformat())
        except ValueError:
            pass
    for day, month, year in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text):
        try:
            values.add(date(int(year), int(month), int(day)).isoformat())
        except ValueError:
            pass
    return sorted(values)


def _extract_amounts(text: str) -> list[int]:
    amounts: set[int] = set()
    for raw in re.findall(
        r"(?:\bCLP\s*|\$\s*)([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{4,})\b",
        text,
        flags=re.IGNORECASE,
    ):
        amounts.add(int(raw.replace(".", "")))
    return sorted(amounts)


def extract_structured_data(db: Session, message: Message) -> dict:
    text = f"{message.subject or ''}\n{message.body}"
    purchase_orders = sorted(
        set(
            match.upper()
            for match in re.findall(
                r"\bOC\s*[-:#]?\s*([A-Z0-9][A-Z0-9-]{2,})\b", text, flags=re.IGNORECASE
            )
        )
    )
    hes_numbers = sorted(
        set(
            match.upper()
            for match in re.findall(
                r"\bHES\s*[-:#]?\s*([A-Z0-9][A-Z0-9-]{2,})\b", text, flags=re.IGNORECASE
            )
        )
    )
    documents = list(
        db.execute(
            select(Document.id, Document.original_name, Document.kind)
            .join(MessageDocument, MessageDocument.document_id == Document.id)
            .where(MessageDocument.message_id == message.id)
        ).all()
    )
    receipt_document_ids = [
        str(row.id)
        for row in documents
        if "comprobante" in row.original_name.casefold()
        or row.kind in {"payment_receipt", "transfer_receipt"}
    ]
    return {
        "payment_dates": _extract_dates(text),
        "amounts": _extract_amounts(text),
        "purchase_orders": purchase_orders,
        "hes_numbers": hes_numbers,
        "receipt_document_ids": receipt_document_ids,
    }


def _priority(message: Message, invoice: Invoice | None, category: str, confidence: Decimal) -> int:
    score = {
        "dispute": 82,
        "invoice_disputed": 82,
        "other": 68,
        "wrong_contact": 64,
        "supplier_data_issue": 58,
        "missing_oc_hes": 55,
        "paid": 48,
        "payment_promise": 44,
        "payment_scheduled": 38,
        "document_request": 36,
    }.get(category, 50)
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        score += 12
    if (message.provider_payload or {}).get("correlation", {}).get("needs_review"):
        score += 12
    if invoice is not None:
        if invoice.due_on < date.today():
            score += min(10, max(1, (date.today() - invoice.due_on).days // 15))
        if invoice.total_amount >= Decimal("5000000"):
            score += 8
        elif invoice.total_amount >= Decimal("1000000"):
            score += 4
    return min(score, 100)


def classify_message(db: Session, message: Message) -> MessageClassification:
    if message.direction != "inbound":
        raise ValueError("Sólo se clasifican mensajes entrantes")
    existing = db.scalar(
        select(MessageClassification)
        .where(MessageClassification.message_id == message.id)
        .order_by(MessageClassification.version.desc())
    )
    if existing is not None:
        return existing
    category, confidence, evidence = _classification_result(
        f"{message.subject or ''}\n{message.body}"
    )
    extracted_data = extract_structured_data(db, message)
    invoice_ids = list(
        db.scalars(
            select(MessageInvoice.invoice_id).where(MessageInvoice.message_id == message.id)
        )
    )
    invoice = db.get(Invoice, invoice_ids[0]) if invoice_ids else None
    classification = MessageClassification(
        client_id=message.client_id,
        message_id=message.id,
        invoice_id=invoice.id if invoice else None,
        version=1,
        category=category,
        confidence=confidence,
        extracted_data=extracted_data,
        evidence=evidence,
        classifier_kind="rule_based",
        classifier_version=CLASSIFIER_VERSION,
        prompt_version=None,
        decision_source="system",
        actor_id=None,
        supersedes_id=None,
    )
    db.add(classification)
    db.flush()
    correlation_review = (message.provider_payload or {}).get("correlation", {}).get(
        "needs_review", False
    )
    if correlation_review:
        kind = "correlation_review"
    elif confidence < LOW_CONFIDENCE_THRESHOLD:
        kind = "low_confidence"
    elif category in MANDATORY_REVIEW_CATEGORIES:
        kind = "mandatory_review"
    else:
        kind = "supervised_review"
    exception = ExceptionCase(
        client_id=message.client_id,
        invoice_id=invoice.id if invoice else None,
        message_id=message.id,
        classification_id=classification.id,
        kind=kind,
        status="open",
        priority=_priority(message, invoice, category, confidence),
        detail={
            "reason": kind,
            "category": category,
            "confidence": str(confidence),
            "classifier_version": CLASSIFIER_VERSION,
            "fully_supervised": True,
        },
        human_minutes=Decimal("0"),
        resolution={},
    )
    db.add(exception)
    db.flush()
    event_invoice_ids = invoice_ids or [None]
    for invoice_id in event_invoice_ids:
        record_event(
            db,
            client_id=message.client_id,
            invoice_id=invoice_id,
            event_type="classification.created",
            actor_type=ActorType.SYSTEM,
            mode="supervised",
            payload={
                "message_id": str(message.id),
                "classification_id": str(classification.id),
                "exception_id": str(exception.id),
                "category": category,
                "confidence": str(confidence),
                "classifier_kind": classification.classifier_kind,
                "classifier_version": CLASSIFIER_VERSION,
                "prompt_version": None,
                "extracted_data": extracted_data,
                "action_executed": False,
            },
        )
    return classification


def review_exception(
    db: Session,
    exception: ExceptionCase,
    *,
    category: str,
    extracted_data: dict,
    human_minutes: Decimal,
    note: str | None,
    checklist_updates: list[ChecklistCorrection],
    workflow_stage: str | None,
    actor_id: uuid.UUID,
) -> MessageClassification:
    current = db.get(MessageClassification, exception.classification_id)
    if current is None:
        raise ValueError("La excepción no tiene clasificación vigente")
    version = int(
        db.scalar(
            select(func.coalesce(func.max(MessageClassification.version), 0)).where(
                MessageClassification.message_id == current.message_id
            )
        )
        or 0
    ) + 1
    decision = MessageClassification(
        client_id=current.client_id,
        message_id=current.message_id,
        invoice_id=current.invoice_id,
        version=version,
        category=category,
        confidence=Decimal("1.0000"),
        extracted_data=extracted_data,
        evidence={"review_note": note, "previous_category": current.category},
        classifier_kind="human_review",
        classifier_version="operator-v1",
        prompt_version=None,
        decision_source="human",
        actor_id=actor_id,
        supersedes_id=current.id,
    )
    db.add(decision)
    db.flush()
    applied_actions: list[dict] = []
    for update in checklist_updates:
        item = db.scalar(
            select(PayabilityItem).where(
                PayabilityItem.id == update.item_id,
                PayabilityItem.client_id == exception.client_id,
                PayabilityItem.invoice_id == exception.invoice_id,
            )
        )
        if item is None:
            raise ValueError("Un requisito del checklist no pertenece al caso")
        previous = {"status": item.status, "evidence": item.evidence}
        item.status = update.status
        item.evidence = update.evidence
        applied_actions.append(
            {
                "type": "checklist",
                "item_id": str(item.id),
                "from": previous,
                "to": {"status": item.status, "evidence": item.evidence},
            }
        )
        record_event(
            db,
            client_id=exception.client_id,
            invoice_id=exception.invoice_id,
            event_type="classification.checklist_correction_applied",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="supervised",
            payload={
                "exception_id": str(exception.id),
                "classification_id": str(decision.id),
                **applied_actions[-1],
            },
        )
    if workflow_stage is not None:
        workflow = db.scalar(
            select(WorkflowState).where(
                WorkflowState.client_id == exception.client_id,
                WorkflowState.invoice_id == exception.invoice_id,
            )
        )
        if workflow is None:
            raise ValueError("La factura no tiene un estado de flujo para corregir")
        previous = {"stage": workflow.stage, "status": workflow.status}
        workflow.stage = workflow_stage
        workflow.status = "completed" if workflow_stage == "closed" else "active"
        workflow.pause_reason = None
        applied_actions.append(
            {
                "type": "workflow_stage",
                "from": previous,
                "to": {"stage": workflow.stage, "status": workflow.status},
            }
        )
        record_event(
            db,
            client_id=exception.client_id,
            invoice_id=exception.invoice_id,
            event_type="classification.workflow_stage_corrected",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="supervised",
            payload={
                "exception_id": str(exception.id),
                "classification_id": str(decision.id),
                **applied_actions[-1],
            },
        )
    exception.classification_id = decision.id
    exception.assigned_to = actor_id
    exception.human_minutes += human_minutes
    exception.human_minutes_measured = True
    exception.status = "resolved"
    exception.resolved_at = datetime.now(timezone.utc)
    exception.resolution = {
        "decision": "confirmed" if category == current.category else "corrected",
        "category": category,
        "note": note,
        "classification_version": version,
        "applied_actions": applied_actions,
    }
    from app.services.evaluation import add_review_example

    evaluation_example = add_review_example(
        db,
        original=current,
        human_decision=decision,
        actor_id=actor_id,
    )
    message_invoice_ids = list(
        db.scalars(
            select(MessageInvoice.invoice_id).where(
                MessageInvoice.message_id == current.message_id
            )
        )
    )
    for invoice_id in message_invoice_ids or [exception.invoice_id]:
        record_event(
            db,
            client_id=exception.client_id,
            invoice_id=invoice_id,
            event_type="classification.human_decision",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="supervised",
            payload={
                "exception_id": str(exception.id),
                "message_id": str(current.message_id),
                "classification_id": str(decision.id),
                "supersedes_id": str(current.id),
                "from_category": current.category,
                "to_category": category,
                "human_minutes": str(human_minutes),
                "note": note,
                "evaluation_example_id": str(evaluation_example.id),
                "applied_actions": applied_actions,
                "action_executed": bool(applied_actions),
            },
        )
    return decision
