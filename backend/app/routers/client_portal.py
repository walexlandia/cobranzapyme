import csv
import io
import re
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Role
from app.models import Client, ClientDocumentSubmission, Invoice, PayabilityItem, User
from app.routers.invoices import _authorized_client
from app.schemas import (
    ClientDocumentReviewCommand,
    ClientDocumentSubmissionView,
    ClientPortalSummaryView,
    WeeklyClientReportView,
)
from app.security import CurrentUser, require_roles
from app.services.client_documents import (
    create_client_document_submission,
    review_client_document_submission,
    submission_view,
)
from app.services.client_portal import build_client_portal_summary, build_weekly_report


router = APIRouter(prefix="/api/v1/client-portal", tags=["client-portal"])
ClientUser = Annotated[User, Depends(require_roles(Role.CLIENT))]
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _client(db: Session, user: CurrentUser, requested: uuid.UUID | None) -> Client:
    client_id = _authorized_client(user, requested)
    client = db.get(Client, client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.get("/summary", response_model=ClientPortalSummaryView)
def portal_summary(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    as_of: Annotated[date | None, Query()] = None,
) -> dict:
    return build_client_portal_summary(
        db,
        client=_client(db, user, client_id),
        as_of=as_of or date.today(),
    )


@router.get("/weekly-report", response_model=WeeklyClientReportView)
def weekly_report(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    week_ending: Annotated[date | None, Query()] = None,
) -> dict:
    return build_weekly_report(
        db,
        client=_client(db, user, client_id),
        week_ending=week_ending or date.today(),
    )


@router.get("/weekly-report.csv")
def weekly_report_csv(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    week_ending: Annotated[date | None, Query()] = None,
) -> Response:
    report_date = week_ending or date.today()
    report = build_weekly_report(
        db,
        client=_client(db, user, client_id),
        week_ending=report_date,
    )
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "periodo_desde",
            "periodo_hasta",
            "folio",
            "pagador",
            "vencimiento",
            "estado",
            "pagabilidad",
            "total_clp",
            "pagado_clp",
            "saldo_clp",
            "checklist",
            "pendiente_pyme",
        ]
    )
    for invoice in report["summary"]["invoices"]:
        writer.writerow(
            [
                report["period_start"],
                report["period_end"],
                invoice["folio"],
                invoice["payer_name"],
                invoice["due_on"],
                invoice["status"],
                invoice["payability_status"],
                invoice["total_amount"],
                invoice["paid_amount"],
                invoice["outstanding_amount"],
                f'{invoice["checklist_completed"]}/{invoice["checklist_total"]}',
                " | ".join(invoice["pending_client_items"]),
            ]
        )
    filename = f"reporte-semanal-{report['client_id']}-{report_date.isoformat()}.csv"
    return Response(
        content=stream.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/document-submissions", response_model=list[ClientDocumentSubmissionView])
def list_document_submissions(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query(pattern=r"^(pending|accepted|rejected)$")] = None,
) -> list[dict]:
    scoped_client = _authorized_client(user, client_id)
    query = select(ClientDocumentSubmission).where(
        ClientDocumentSubmission.client_id == scoped_client
    )
    if status:
        query = query.where(ClientDocumentSubmission.status == status)
    submissions = list(
        db.scalars(query.order_by(ClientDocumentSubmission.created_at.desc()))
    )
    return [submission_view(db, submission) for submission in submissions]


@router.post(
    "/documents",
    response_model=ClientDocumentSubmissionView,
    status_code=201,
)
async def upload_client_document(
    user: ClientUser,
    db: Annotated[Session, Depends(get_db)],
    document: Annotated[UploadFile, File()],
    invoice_id: Annotated[uuid.UUID, Form()],
    payability_item_id: Annotated[uuid.UUID, Form()],
) -> dict:
    if user.client_id is None:
        raise HTTPException(status_code=403, detail="Usuario cliente sin empresa")
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == user.client_id,
        )
    )
    item = db.scalar(
        select(PayabilityItem).where(
            PayabilityItem.id == payability_item_id,
            PayabilityItem.client_id == user.client_id,
            PayabilityItem.invoice_id == invoice_id,
        )
    )
    if invoice is None or item is None:
        raise HTTPException(status_code=404, detail="Factura o requisito no encontrado")
    content = await document.read()
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", document.filename or "documento.bin")
    try:
        submission, duplicate = create_client_document_submission(
            db,
            user=user,
            invoice=invoice,
            item=item,
            filename=filename,
            content=content,
        )
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not duplicate:
        db.commit()
        db.refresh(submission)
    return submission_view(db, submission)


@router.post(
    "/document-submissions/{submission_id}/review",
    response_model=ClientDocumentSubmissionView,
)
def review_client_document(
    submission_id: uuid.UUID,
    payload: ClientDocumentReviewCommand,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    submission = db.scalar(
        select(ClientDocumentSubmission)
        .where(
            ClientDocumentSubmission.id == submission_id,
            ClientDocumentSubmission.client_id == payload.client_id,
        )
        .with_for_update()
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Documento enviado no encontrado")
    try:
        review_client_document_submission(
            db,
            submission=submission,
            decision=payload.decision,
            note=payload.note,
            reviewer=user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(submission)
    return submission_view(db, submission)
