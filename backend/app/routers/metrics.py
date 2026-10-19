import csv
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Role
from app.models import Client, User
from app.schemas import ClientTrendView, FinalPilotReportView, PilotMetricsView
from app.security import CurrentUser, require_roles
from app.services.final_report import (
    anonymized_dataset_csv,
    build_final_report,
    final_report_markdown,
)
from app.services.pilot_metrics import build_pilot_metrics


router = APIRouter(prefix="/api/v1/metrics", tags=["pilot-metrics"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _client(db: Session, client_id: uuid.UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


def _report(
    db: Session,
    *,
    client_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    human_hourly_cost_clp: Decimal,
    usd_clp_rate: Decimal,
) -> dict:
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=83))
    try:
        return build_pilot_metrics(
            db,
            client=_client(db, client_id),
            date_from=start,
            date_to=end,
            human_hourly_cost_clp=human_hourly_cost_clp,
            usd_clp_rate=usd_clp_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _final_report(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    human_hourly_cost_clp: Decimal,
    usd_clp_rate: Decimal,
    minimum_group_size: int,
    evidence_kind: Literal["synthetic", "authorized_pilot"],
) -> dict:
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=55))
    try:
        return build_final_report(
            db,
            date_from=start,
            date_to=end,
            human_hourly_cost_clp=human_hourly_cost_clp,
            usd_clp_rate=usd_clp_rate,
            minimum_group_size=minimum_group_size,
            evidence_kind=evidence_kind,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/pilot", response_model=PilotMetricsView)
def pilot_metrics(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    human_hourly_cost_clp: Annotated[Decimal, Query(ge=0)] = Decimal("8000"),
    usd_clp_rate: Annotated[Decimal, Query(gt=0)] = Decimal("950"),
) -> dict:
    return _report(
        db,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=human_hourly_cost_clp,
        usd_clp_rate=usd_clp_rate,
    )


@router.get("/pilot.csv")
def pilot_metrics_csv(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    human_hourly_cost_clp: Annotated[Decimal, Query(ge=0)] = Decimal("8000"),
    usd_clp_rate: Annotated[Decimal, Query(gt=0)] = Decimal("950"),
) -> Response:
    report = _report(
        db,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=human_hourly_cost_clp,
        usd_clp_rate=usd_clp_rate,
    )
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["seccion", "metrica", "periodo", "valor", "unidad"])
    for section in ("baseline", "outcomes", "operations", "economics", "assumptions"):
        for key, value in report[section].items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    writer.writerow([section, f"{key}.{nested_key}", "", nested_value, ""])
            elif key != "note":
                writer.writerow([section, key, "", value if value is not None else "", ""])
    for point in report["trend"]:
        period = f'{point["week_start"]}/{point["week_end"]}'
        for key in ("settled_invoices", "on_time_percent", "average_dso", "verified_amount"):
            writer.writerow(["trend", key, period, point[key] if point[key] is not None else "", ""])
    for cause in report["delay_causes"]:
        writer.writerow(["delay_cause", cause["category"], "", cause["invoice_count"], "facturas"])
        writer.writerow(["delay_cause", cause["category"], "", cause["amount"], "CLP"])
    for resolution in report["resolution_times"]:
        writer.writerow(
            [
                "resolution_time",
                resolution["item_type"],
                "",
                resolution["average_hours"],
                "horas promedio",
            ]
        )
        writer.writerow(
            [
                "resolution_time",
                resolution["item_type"],
                "",
                resolution["resolved_count"],
                "requisitos",
            ]
        )
    return Response(
        content=stream.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="metricas-piloto-{client_id}-{report["date_to"]}.csv"'
            )
        },
    )


@router.get("/client-trend", response_model=ClientTrendView)
def client_trend(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> dict:
    if user.role != Role.CLIENT or user.client_id is None:
        raise HTTPException(status_code=403, detail="Disponible únicamente para usuarios cliente")
    report = _report(
        db,
        client_id=user.client_id,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=Decimal("0"),
        usd_clp_rate=Decimal("1"),
    )
    return {
        "client_id": report["client_id"],
        "client_name": report["client_name"],
        "date_from": report["date_from"],
        "date_to": report["date_to"],
        "baseline": report["baseline"],
        "outcomes": report["outcomes"],
        "trend": report["trend"],
    }


@router.get("/final-report", response_model=FinalPilotReportView)
def final_report(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    human_hourly_cost_clp: Annotated[Decimal, Query(ge=0)] = Decimal("8000"),
    usd_clp_rate: Annotated[Decimal, Query(gt=0)] = Decimal("950"),
    minimum_group_size: Annotated[int, Query(ge=1, le=50)] = 2,
    evidence_kind: Annotated[Literal["synthetic", "authorized_pilot"], Query()] = "synthetic",
) -> dict:
    return _final_report(
        db,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=human_hourly_cost_clp,
        usd_clp_rate=usd_clp_rate,
        minimum_group_size=minimum_group_size,
        evidence_kind=evidence_kind,
    )


@router.get("/anonymized-dataset.csv")
def final_report_dataset_csv(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    human_hourly_cost_clp: Annotated[Decimal, Query(ge=0)] = Decimal("8000"),
    usd_clp_rate: Annotated[Decimal, Query(gt=0)] = Decimal("950"),
    minimum_group_size: Annotated[int, Query(ge=1, le=50)] = 2,
    evidence_kind: Annotated[Literal["synthetic", "authorized_pilot"], Query()] = "synthetic",
) -> Response:
    report = _final_report(
        db,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=human_hourly_cost_clp,
        usd_clp_rate=usd_clp_rate,
        minimum_group_size=minimum_group_size,
        evidence_kind=evidence_kind,
    )
    return Response(
        content=anonymized_dataset_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dataset-piloto-anonimizado-{report["date_to"]}.csv"'
            )
        },
    )


@router.get("/final-report.md")
def final_report_document(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    human_hourly_cost_clp: Annotated[Decimal, Query(ge=0)] = Decimal("8000"),
    usd_clp_rate: Annotated[Decimal, Query(gt=0)] = Decimal("950"),
    minimum_group_size: Annotated[int, Query(ge=1, le=50)] = 2,
    evidence_kind: Annotated[Literal["synthetic", "authorized_pilot"], Query()] = "synthetic",
) -> Response:
    report = _final_report(
        db,
        date_from=date_from,
        date_to=date_to,
        human_hourly_cost_clp=human_hourly_cost_clp,
        usd_clp_rate=usd_clp_rate,
        minimum_group_size=minimum_group_size,
        evidence_kind=evidence_kind,
    )
    return Response(
        content=final_report_markdown(report),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="informe-final-v10-{report["date_to"]}.md"'
            )
        },
    )
