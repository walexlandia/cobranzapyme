import hashlib
import itertools
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType, InvoiceStatus
from app.models import (
    BankTransaction,
    Document,
    Invoice,
    Payment,
    Payer,
    ReconciliationItem,
    ReconciliationProposal,
)
from app.schemas import BankStatementRow, ImportIssue
from app.services.invoice_import import _normalize_header, _parse_amount, _parse_date, _read_rows
from app.services.commissions import attribute_payment
from app.document_crypto import encrypt_document_content
from app.utils.rut import normalize_rut


BANK_ALIASES = {
    "external_id": ["id movimiento", "id", "referencia", "external_id"],
    "occurred_on": ["fecha", "fecha movimiento", "occurred_on"],
    "amount": ["monto", "abono", "importe", "amount"],
    "description": ["descripcion", "descripción", "glosa", "description"],
    "counterparty_rut": ["rut contraparte", "rut", "counterparty_rut"],
    "currency": ["moneda", "currency"],
}
REQUIRED_BANK_FIELDS = {"external_id", "occurred_on", "amount"}


def parse_bank_statement_file(
    filename: str, content: bytes
) -> tuple[list[BankStatementRow], list[ImportIssue]]:
    raw_rows = _read_rows(filename, content)
    if not raw_rows:
        return [], [ImportIssue(row=1, message="El archivo no contiene movimientos")]
    headers = set(raw_rows[0])
    mapping: dict[str, str] = {}
    for field, aliases in BANK_ALIASES.items():
        match = next((alias for alias in aliases if _normalize_header(alias) in headers), None)
        if match:
            mapping[field] = _normalize_header(match)
    missing = REQUIRED_BANK_FIELDS - set(mapping)
    if missing:
        return [], [
            ImportIssue(row=1, field=field, message=f"Falta la columna {field}")
            for field in sorted(missing)
        ]
    valid: list[BankStatementRow] = []
    issues: list[ImportIssue] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_rows, start=2):
        if not any(value not in (None, "") for value in raw.values()):
            continue
        try:
            external_id = str(raw.get(mapping["external_id"]) or "").strip()
            if not external_id:
                raise ValueError("identificador de movimiento vacío")
            if external_id in seen:
                raise ValueError("movimiento duplicado dentro del archivo")
            raw_rut = str(raw.get(mapping.get("counterparty_rut", "")) or "").strip()
            row = BankStatementRow(
                row=index,
                external_id=external_id,
                occurred_on=_parse_date(raw.get(mapping["occurred_on"])),
                amount=_parse_amount(raw.get(mapping["amount"])),
                description=(
                    str(raw.get(mapping.get("description", ""))).strip()
                    if raw.get(mapping.get("description", "")) not in (None, "")
                    else None
                ),
                counterparty_rut=normalize_rut(raw_rut) if raw_rut else None,
                currency=str(raw.get(mapping.get("currency", "")) or "CLP").strip().upper(),
            )
            seen.add(external_id)
            valid.append(row)
        except (TypeError, ValueError) as exc:
            issues.append(ImportIssue(row=index, message=str(exc)))
    return valid, issues


def verified_total(db: Session, invoice_id: uuid.UUID) -> Decimal:
    return Decimal(
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice_id,
                Payment.verified.is_(True),
            )
        )
        or 0
    ).quantize(Decimal("0.01"))


def outstanding_amount(db: Session, invoice: Invoice) -> Decimal:
    return max(
        Decimal("0.00"),
        (Decimal(invoice.total_amount) - verified_total(db, invoice.id)).quantize(
            Decimal("0.01")
        ),
    )


def _score_candidate(
    transaction: BankTransaction,
    payer: Payer,
    invoices: list[Invoice],
    balances: list[Decimal],
) -> tuple[Decimal, dict[str, Any]]:
    exact_rut = bool(
        transaction.counterparty_rut and transaction.counterparty_rut == payer.rut
    )
    rut_points = 45 if exact_rut else (20 if not transaction.counterparty_rut else 0)
    expected = sum(balances, Decimal("0"))
    difference = abs(Decimal(transaction.amount) - expected)
    ratio = difference / expected if expected else Decimal("1")
    amount_points = 40 if difference <= Decimal("1") else (
        30 if ratio <= Decimal("0.01") else (15 if ratio <= Decimal("0.05") else 0)
    )
    in_window = all(
        invoice.issued_on <= transaction.occurred_on
        and (transaction.occurred_on - invoice.due_on).days <= 90
        for invoice in invoices
    )
    near_window = all(
        invoice.issued_on <= transaction.occurred_on
        and (transaction.occurred_on - invoice.due_on).days <= 180
        for invoice in invoices
    )
    date_points = 15 if in_window else (8 if near_window else 0)
    score = Decimal(rut_points + amount_points + date_points).quantize(Decimal("0.01"))
    return score, {
        "rut": {"points": rut_points, "exact": exact_rut},
        "amount": {
            "points": amount_points,
            "transaction_amount": str(transaction.amount),
            "candidate_balance": str(expected),
            "difference": str(difference),
        },
        "date": {"points": date_points, "within_window": in_window},
        "invoice_count": len(invoices),
        "synthetic_or_external_connection": False,
    }


def _allocations(balances: list[Decimal], amount: Decimal) -> list[Decimal]:
    remaining = Decimal(amount)
    allocations: list[Decimal] = []
    for balance in balances:
        allocation = min(balance, remaining).quantize(Decimal("0.01"))
        allocations.append(allocation)
        remaining -= allocation
    return allocations if abs(remaining) <= Decimal("0.01") else []


def generate_reconciliation_proposals(
    db: Session, transaction: BankTransaction
) -> list[ReconciliationProposal]:
    if transaction.status != "unmatched":
        return []
    invoice_rows = list(
        db.scalars(
            select(Invoice)
            .where(
                Invoice.client_id == transaction.client_id,
                Invoice.currency == transaction.currency,
                Invoice.status.notin_([InvoiceStatus.VOID, InvoiceStatus.PAID]),
            )
            .order_by(Invoice.due_on, Invoice.folio)
        )
    )
    by_payer: dict[uuid.UUID, list[tuple[Invoice, Decimal]]] = {}
    for invoice in invoice_rows:
        balance = outstanding_amount(db, invoice)
        if balance > 0:
            by_payer.setdefault(invoice.payer_id, []).append((invoice, balance))
    candidates: list[tuple[Decimal, dict, list[Invoice], list[Decimal]]] = []
    for payer_id, rows in by_payer.items():
        payer = db.get(Payer, payer_id)
        if payer is None:
            continue
        if transaction.counterparty_rut and transaction.counterparty_rut != payer.rut:
            continue
        limited = rows[:12]
        for size in range(1, min(3, len(limited)) + 1):
            for combination in itertools.combinations(limited, size):
                invoices = [row[0] for row in combination]
                balances = [row[1] for row in combination]
                allocations = _allocations(balances, Decimal(transaction.amount))
                if not allocations or any(amount <= 0 for amount in allocations):
                    continue
                score, breakdown = _score_candidate(
                    transaction, payer, invoices, balances
                )
                if score >= Decimal("60"):
                    candidates.append((score, breakdown, invoices, allocations))
    candidates.sort(
        key=lambda item: (-item[0], len(item[2]), [invoice.folio for invoice in item[2]])
    )
    created: list[ReconciliationProposal] = []
    for score, breakdown, invoices, allocations in candidates[:5]:
        candidate_key = ":".join(sorted(str(invoice.id) for invoice in invoices))
        existing = db.scalar(
            select(ReconciliationProposal).where(
                ReconciliationProposal.bank_transaction_id == transaction.id,
                ReconciliationProposal.candidate_key == candidate_key,
            )
        )
        if existing is not None:
            continue
        proposal = ReconciliationProposal(
            client_id=transaction.client_id,
            bank_transaction_id=transaction.id,
            candidate_key=candidate_key,
            status="pending",
            score=score,
            score_breakdown=breakdown,
        )
        db.add(proposal)
        db.flush()
        for invoice, allocated in zip(invoices, allocations, strict=True):
            db.add(
                ReconciliationItem(
                    client_id=transaction.client_id,
                    proposal_id=proposal.id,
                    invoice_id=invoice.id,
                    allocated_amount=allocated,
                )
            )
            record_event(
                db,
                client_id=transaction.client_id,
                invoice_id=invoice.id,
                event_type="reconciliation.proposed",
                actor_type=ActorType.SYSTEM,
                mode="supervised",
                payload={
                    "proposal_id": str(proposal.id),
                    "bank_transaction_id": str(transaction.id),
                    "allocated_amount": str(allocated),
                    "score": str(score),
                    "score_breakdown": breakdown,
                    "requires_human_review": True,
                },
            )
        created.append(proposal)
    return created


def _mark_paid_if_settled(
    db: Session, invoice: Invoice, *, actor_id: uuid.UUID, source: str
) -> None:
    if verified_total(db, invoice.id) < Decimal(invoice.total_amount):
        return
    if invoice.status == InvoiceStatus.PAID:
        return
    previous = invoice.status
    invoice.status = InvoiceStatus.PAID
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="invoice.status_changed",
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="manual",
        payload={"from": previous.value, "to": "paid", "source": source},
    )


def register_manual_payment(
    db: Session,
    *,
    invoice: Invoice,
    amount: Decimal,
    paid_on: date,
    reference: str,
    evidence_name: str,
    evidence_content: bytes,
    actor_id: uuid.UUID,
) -> Payment:
    idempotency_key = f"manual:{invoice.client_id}:{invoice.id}:{reference.strip().casefold()}"
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    normalized_amount = Decimal(amount).quantize(Decimal("0.01"))
    balance = outstanding_amount(db, invoice)
    if normalized_amount <= 0 or normalized_amount > balance:
        raise ValueError(f"El monto debe ser mayor a cero y no superar el saldo {balance}")
    digest = hashlib.sha256(evidence_content).hexdigest()
    document_id = uuid.uuid4()
    encrypted_content, encryption_nonce, encryption_version = encrypt_document_content(
        document_id=document_id,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        content=evidence_content,
    )
    document = Document(
        id=document_id,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        kind="payment_receipt",
        object_key=f"local-payment/{invoice.client_id}/{digest}/{evidence_name}",
        original_name=evidence_name,
        sha256=digest,
        content=encrypted_content,
        encryption_version=encryption_version,
        encryption_nonce=encryption_nonce,
    )
    db.add(document)
    db.flush()
    payment = Payment(
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        amount=normalized_amount,
        paid_on=paid_on,
        verified=True,
        evidence_document_id=document.id,
        source="manual",
        reference=reference,
        verified_by=actor_id,
        verified_at=datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()
    record_event(
        db,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        event_type="payment.verified",
        actor_type=ActorType.HUMAN,
        actor_id=actor_id,
        mode="manual",
        payload={
            "payment_id": str(payment.id),
            "amount": str(payment.amount),
            "paid_on": paid_on.isoformat(),
            "source": "manual",
            "reference": reference,
            "evidence_document_id": str(document.id),
            "evidence_sha256": digest,
        },
    )
    attribute_payment(db, payment)
    _mark_paid_if_settled(db, invoice, actor_id=actor_id, source="manual_payment")
    return payment


def decide_reconciliation(
    db: Session,
    proposal: ReconciliationProposal,
    *,
    decision: str,
    note: str | None,
    actor_id: uuid.UUID,
) -> list[Payment]:
    if proposal.status != "pending":
        raise ValueError("La propuesta ya fue revisada")
    transaction = db.scalar(
        select(BankTransaction)
        .where(BankTransaction.id == proposal.bank_transaction_id)
        .with_for_update()
    )
    if transaction is None or transaction.client_id != proposal.client_id:
        raise ValueError("Movimiento bancario no encontrado")
    items = list(
        db.scalars(
            select(ReconciliationItem)
            .where(ReconciliationItem.proposal_id == proposal.id)
            .order_by(ReconciliationItem.created_at, ReconciliationItem.id)
        )
    )
    now = datetime.now(timezone.utc)
    proposal.status = decision
    proposal.reviewed_by = actor_id
    proposal.reviewed_at = now
    proposal.review_note = note
    if decision == "rejected":
        for item in items or [None]:
            record_event(
                db,
                client_id=proposal.client_id,
                invoice_id=item.invoice_id if item else None,
                event_type="reconciliation.rejected",
                actor_type=ActorType.HUMAN,
                actor_id=actor_id,
                mode="manual",
                payload={
                    "proposal_id": str(proposal.id),
                    "bank_transaction_id": str(transaction.id),
                    "score": str(proposal.score),
                    "note": note,
                },
            )
        return []
    if transaction.status != "unmatched":
        raise ValueError("El movimiento bancario ya fue conciliado o descartado")
    allocated_total = sum(
        (Decimal(item.allocated_amount) for item in items), Decimal("0")
    ).quantize(Decimal("0.01"))
    if allocated_total != Decimal(transaction.amount).quantize(Decimal("0.01")):
        raise ValueError("La propuesta no distribuye exactamente el monto del movimiento")
    payments: list[Payment] = []
    for item in items:
        invoice = db.get(Invoice, item.invoice_id)
        if invoice is None or invoice.client_id != proposal.client_id:
            raise ValueError("La propuesta contiene una factura inválida")
        if Decimal(item.allocated_amount) > outstanding_amount(db, invoice):
            raise ValueError("El saldo de una factura cambió; regenere las propuestas")
        payment = Payment(
            client_id=proposal.client_id,
            invoice_id=invoice.id,
            amount=item.allocated_amount,
            paid_on=transaction.occurred_on,
            verified=True,
            bank_transaction_id=transaction.id,
            source="bank_statement",
            reference=transaction.external_id,
            verified_by=actor_id,
            verified_at=now,
            idempotency_key=f"bank:{transaction.id}:{invoice.id}",
        )
        db.add(payment)
        db.flush()
        payments.append(payment)
        record_event(
            db,
            client_id=proposal.client_id,
            invoice_id=invoice.id,
            event_type="reconciliation.confirmed",
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            mode="manual",
            payload={
                "proposal_id": str(proposal.id),
                "bank_transaction_id": str(transaction.id),
                "payment_id": str(payment.id),
                "amount": str(payment.amount),
                "score": str(proposal.score),
                "score_breakdown": proposal.score_breakdown,
                "origin": "bank_statement",
                "note": note,
            },
        )
        attribute_payment(db, payment)
        _mark_paid_if_settled(
            db, invoice, actor_id=actor_id, source="bank_reconciliation"
        )
    transaction.status = "matched"
    other_proposals = list(
        db.scalars(
            select(ReconciliationProposal).where(
                ReconciliationProposal.bank_transaction_id == transaction.id,
                ReconciliationProposal.id != proposal.id,
                ReconciliationProposal.status == "pending",
            )
        )
    )
    for other in other_proposals:
        other.status = "superseded"
        other.review_note = "Otra propuesta del movimiento fue confirmada"
    return payments
