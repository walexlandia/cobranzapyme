import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.document_crypto import encrypt_document_content
from app.domain import ActorType
from app.models import (
    ClientDocumentSubmission,
    Document,
    Invoice,
    PayabilityItem,
    User,
)


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv", ".xlsx"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
COMPLETED_ITEM_STATUSES = {"fulfilled", "not_applicable"}


def submission_view(db: Session, submission: ClientDocumentSubmission) -> dict:
    invoice = db.get(Invoice, submission.invoice_id)
    item = db.get(PayabilityItem, submission.payability_item_id)
    document = db.get(Document, submission.document_id)
    submitter = db.get(User, submission.submitted_by)
    assert invoice is not None and item is not None and document is not None and submitter is not None
    return {
        "id": submission.id,
        "client_id": submission.client_id,
        "invoice_id": submission.invoice_id,
        "invoice_folio": invoice.folio,
        "payability_item_id": submission.payability_item_id,
        "item_label": item.label,
        "document_id": submission.document_id,
        "original_name": document.original_name,
        "content_sha256": submission.content_sha256,
        "status": submission.status,
        "submitted_by": submission.submitted_by,
        "submitted_by_name": submitter.full_name,
        "reviewed_by": submission.reviewed_by,
        "reviewed_at": submission.reviewed_at,
        "review_note": submission.review_note,
        "created_at": submission.created_at,
    }


def create_client_document_submission(
    db: Session,
    *,
    user: User,
    invoice: Invoice,
    item: PayabilityItem,
    filename: str,
    content: bytes,
) -> tuple[ClientDocumentSubmission, bool]:
    if not content:
        raise ValueError("El documento está vacío")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise OverflowError("El documento supera 10 MB")
    suffix = Path(filename).suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no permitido; use PDF, imagen, TXT, CSV o XLSX")
    if item.client_id != invoice.client_id or item.invoice_id != invoice.id:
        raise ValueError("El requisito no pertenece a la factura")
    if item.responsible_role != "client" or not item.required:
        raise ValueError("El requisito no admite documentos de la pyme")
    if item.status in COMPLETED_ITEM_STATUSES:
        raise ValueError("El requisito ya está resuelto")
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(ClientDocumentSubmission).where(
            ClientDocumentSubmission.client_id == invoice.client_id,
            ClientDocumentSubmission.payability_item_id == item.id,
            ClientDocumentSubmission.content_sha256 == digest,
        )
    )
    if existing is not None:
        return existing, True
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename or f"documento{suffix}")
    document_id = uuid.uuid4()
    ciphertext, nonce, version = encrypt_document_content(
        document_id=document_id,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        content=content,
    )
    document = Document(
        id=document_id,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        kind=item.item_type,
        object_key=(
            f"client-submissions/{invoice.client_id}/{invoice.id}/{item.id}/{digest}/{safe_name}"
        ),
        original_name=safe_name,
        sha256=digest,
        content=ciphertext,
        encryption_version=version,
        encryption_nonce=nonce,
    )
    db.add(document)
    db.flush()
    submission = ClientDocumentSubmission(
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        payability_item_id=item.id,
        document_id=document.id,
        content_sha256=digest,
        status="pending",
        submitted_by=user.id,
    )
    db.add(submission)
    db.flush()
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="client_document.submitted",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "submission_id": str(submission.id),
            "payability_item_id": str(item.id),
            "document_id": str(document.id),
            "original_name": safe_name,
            "sha256": digest,
            "encryption_version": version,
        },
    )
    return submission, False


def review_client_document_submission(
    db: Session,
    *,
    submission: ClientDocumentSubmission,
    decision: str,
    note: str | None,
    reviewer: User,
) -> ClientDocumentSubmission:
    if submission.status != "pending":
        if submission.status == decision:
            return submission
        raise ValueError("El documento ya fue revisado")
    item = db.get(PayabilityItem, submission.payability_item_id)
    if item is None or item.client_id != submission.client_id:
        raise ValueError("El requisito asociado ya no está disponible")
    previous = {"status": item.status, "evidence": item.evidence}
    now = datetime.now(timezone.utc)
    submission.status = decision
    submission.reviewed_by = reviewer.id
    submission.reviewed_at = now
    submission.review_note = (note or "").strip() or None
    if decision == "accepted":
        item.status = "fulfilled"
        item.evidence = {
            **(item.evidence or {}),
            "client_submission_id": str(submission.id),
            "document_id": str(submission.document_id),
            "sha256": submission.content_sha256,
            "reviewed_at": now.isoformat(),
        }
        record_event(
            db,
            client_id=submission.client_id,
            invoice_id=submission.invoice_id,
            event_type="payability.item_changed",
            actor_type=ActorType.HUMAN,
            actor_id=reviewer.id,
            payload={
                "item_id": str(item.id),
                "item_type": item.item_type,
                "from": previous,
                "to": {"status": item.status, "evidence": item.evidence},
                "source": "client_document_review",
            },
        )
    elif item.status == "pending":
        item.status = "requested"
        record_event(
            db,
            client_id=submission.client_id,
            invoice_id=submission.invoice_id,
            event_type="payability.item_changed",
            actor_type=ActorType.HUMAN,
            actor_id=reviewer.id,
            payload={
                "item_id": str(item.id),
                "item_type": item.item_type,
                "from": previous,
                "to": {"status": item.status, "evidence": item.evidence},
                "source": "client_document_rejection",
            },
        )
    record_event(
        db,
        client_id=submission.client_id,
        invoice_id=submission.invoice_id,
        event_type="client_document.reviewed",
        actor_type=ActorType.HUMAN,
        actor_id=reviewer.id,
        payload={
            "submission_id": str(submission.id),
            "payability_item_id": str(item.id),
            "document_id": str(submission.document_id),
            "decision": decision,
            "note": submission.review_note,
        },
    )
    return submission
