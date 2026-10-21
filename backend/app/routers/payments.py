import csv
import io
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import (
    BankTransaction,
    Invoice,
    Payment,
    ReconciliationItem,
    ReconciliationProposal,
    User,
)
from app.schemas import (
    BankStatementPreview,
    BankTransactionView,
    CommissionReportView,
    ImportIssue,
    PaymentView,
    ReconciliationDecision,
    ReconciliationProposalView,
)
from app.security import require_roles
from app.services.payments import (
    decide_reconciliation,
    generate_reconciliation_proposals,
    parse_bank_statement_file,
    register_manual_payment,
)
from app.services.commissions import build_commission_report


router = APIRouter(prefix="/api/v1/payments", tags=["payments-and-reconciliation"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _proposal_view(db: Session, proposal: ReconciliationProposal) -> ReconciliationProposalView:
    transaction = db.get(BankTransaction, proposal.bank_transaction_id)
    items = list(
        db.scalars(
            select(ReconciliationItem)
            .where(ReconciliationItem.proposal_id == proposal.id)
            .order_by(ReconciliationItem.created_at, ReconciliationItem.id)
        )
    )
    invoices = {item.invoice_id: db.get(Invoice, item.invoice_id) for item in items}
    assert transaction is not None
    return ReconciliationProposalView(
        id=proposal.id,
        client_id=proposal.client_id,
        bank_transaction_id=proposal.bank_transaction_id,
        status=proposal.status,
        score=proposal.score,
        score_breakdown=proposal.score_breakdown,
        reviewed_by=proposal.reviewed_by,
        reviewed_at=proposal.reviewed_at,
        review_note=proposal.review_note,
        human_minutes=proposal.human_minutes,
        created_at=proposal.created_at,
        transaction={
            "external_id": transaction.external_id,
            "occurred_on": transaction.occurred_on,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "counterparty_rut": transaction.counterparty_rut,
            "description": transaction.description,
            "status": transaction.status,
        },
        invoices=[
            {
                "id": str(item.invoice_id),
                "folio": invoices[item.invoice_id].folio if invoices[item.invoice_id] else None,
                "payer_name": (
                    invoices[item.invoice_id].payer_name if invoices[item.invoice_id] else None
                ),
                "total_amount": (
                    invoices[item.invoice_id].total_amount if invoices[item.invoice_id] else None
                ),
                "allocated_amount": item.allocated_amount,
            }
            for item in items
        ],
    )


@router.get("", response_model=list[PaymentView])
def list_payments(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    invoice_id: uuid.UUID | None = None,
) -> list[Payment]:
    query = select(Payment).where(Payment.client_id == client_id)
    if invoice_id:
        query = query.where(Payment.invoice_id == invoice_id)
    return list(db.scalars(query.order_by(Payment.paid_on.desc(), Payment.created_at.desc())))


@router.get("/commission-report", response_model=CommissionReportView)
def commission_report(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    period: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> dict:
    try:
        return build_commission_report(db, client_id=client_id, period=period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/commission-report.csv")
def export_commission_report(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    period: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> Response:
    try:
        report = build_commission_report(db, client_id=client_id, period=period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "periodo",
            "pago_id",
            "factura_id",
            "folio",
            "fecha_pago",
            "monto_pago_clp",
            "origen",
            "atribucion",
            "porcentaje",
            "comision_clp",
            "contrato_id",
            "regla",
        ]
    )
    for detail in report["details"]:
        writer.writerow(
            [
                period,
                detail["payment_id"],
                detail["invoice_id"],
                detail["folio"],
                detail["paid_on"],
                detail["payment_amount"],
                detail["source"],
                detail["category"],
                detail["percentage"],
                detail["commission_amount"],
                detail["contract_id"] or "",
                detail["rationale"].get("rule", ""),
            ]
        )
    return Response(
        content=stream.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="comisiones-{period}.csv"'
        },
    )


@router.post("/manual", response_model=PaymentView)
async def create_manual_payment(
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    evidence: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID, Form()],
    invoice_id: Annotated[uuid.UUID, Form()],
    amount: Annotated[Decimal, Form(gt=0)],
    paid_on: Annotated[date, Form()],
    reference: Annotated[str, Form(min_length=2, max_length=200)],
) -> Payment:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client_id,
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    content = await evidence.read()
    if not content:
        raise HTTPException(status_code=422, detail="El comprobante está vacío")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El comprobante supera 10 MB")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", evidence.filename or "comprobante.bin")
    try:
        payment = register_manual_payment(
            db,
            invoice=invoice,
            amount=amount,
            paid_on=paid_on,
            reference=reference,
            evidence_name=safe_name,
            evidence_content=content,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/bank-statements", response_model=BankStatementPreview)
async def import_bank_statement(
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID, Form()],
    commit: Annotated[bool, Form()] = False,
) -> BankStatementPreview:
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="La cartola supera 10 MB")
    try:
        rows, issues = parse_bank_statement_file(file.filename or "cartola.csv", content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    accepted = []
    for row in rows:
        existing = db.scalar(
            select(BankTransaction.id).where(
                BankTransaction.client_id == client_id,
                BankTransaction.external_id == row.external_id,
            )
        )
        if existing:
            issues.append(
                ImportIssue(row=row.row, field="external_id", message="El movimiento ya fue importado")
            )
        else:
            accepted.append(row)
    imported_count = 0
    proposals_created = 0
    if commit and not issues:
        for row in accepted:
            transaction = BankTransaction(
                client_id=client_id,
                external_id=row.external_id,
                occurred_on=row.occurred_on,
                amount=row.amount,
                description=row.description,
                counterparty_rut=row.counterparty_rut,
                currency=row.currency,
                status="unmatched",
                source_filename=file.filename,
                source_row=row.row,
                raw_data=row.model_dump(mode="json"),
                imported_by=user.id,
            )
            db.add(transaction)
            db.flush()
            record_event(
                db,
                client_id=client_id,
                event_type="bank_transaction.imported",
                actor_type=ActorType.HUMAN,
                actor_id=user.id,
                mode="manual",
                payload={
                    "bank_transaction_id": str(transaction.id),
                    "external_id": transaction.external_id,
                    "amount": str(transaction.amount),
                    "occurred_on": transaction.occurred_on.isoformat(),
                    "source_filename": file.filename,
                    "source_row": row.row,
                },
            )
            proposals_created += len(generate_reconciliation_proposals(db, transaction))
            imported_count += 1
        db.commit()
    return BankStatementPreview(
        valid_rows=accepted,
        issues=issues,
        can_commit=bool(accepted) and not issues,
        imported_count=imported_count,
        proposals_created=proposals_created,
    )


@router.get("/bank-transactions", response_model=list[BankTransactionView])
def list_bank_transactions(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> list[BankTransaction]:
    query = select(BankTransaction).where(BankTransaction.client_id == client_id)
    if status:
        query = query.where(BankTransaction.status == status)
    return list(
        db.scalars(query.order_by(BankTransaction.occurred_on.desc(), BankTransaction.created_at))
    )


@router.get("/reconciliation-proposals", response_model=list[ReconciliationProposalView])
def list_reconciliation_proposals(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> list[ReconciliationProposalView]:
    query = select(ReconciliationProposal).where(
        ReconciliationProposal.client_id == client_id
    )
    if status:
        query = query.where(ReconciliationProposal.status == status)
    proposals = list(
        db.scalars(query.order_by(ReconciliationProposal.score.desc(), ReconciliationProposal.created_at))
    )
    return [_proposal_view(db, proposal) for proposal in proposals]


@router.post(
    "/reconciliation-proposals/{proposal_id}/decision",
    response_model=ReconciliationProposalView,
)
def review_reconciliation_proposal(
    proposal_id: uuid.UUID,
    payload: ReconciliationDecision,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> ReconciliationProposalView:
    proposal = db.scalar(
        select(ReconciliationProposal).where(
            ReconciliationProposal.id == proposal_id,
            ReconciliationProposal.client_id == payload.client_id,
        )
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    try:
        decide_reconciliation(
            db,
            proposal,
            decision=payload.decision,
            note=payload.note,
            human_minutes=payload.human_minutes,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(proposal)
    return _proposal_view(db, proposal)
