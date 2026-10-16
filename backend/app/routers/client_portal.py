import csv
import io
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.routers.invoices import _authorized_client
from app.schemas import ClientPortalSummaryView, WeeklyClientReportView
from app.security import CurrentUser
from app.services.client_portal import build_client_portal_summary, build_weekly_report


router = APIRouter(prefix="/api/v1/client-portal", tags=["client-portal"])


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
