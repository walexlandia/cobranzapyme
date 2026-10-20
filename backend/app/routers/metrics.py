import csv
import hashlib
import io
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import Client, Event, Invoice, PilotClosureSnapshot, User
from app.schemas import (
    ClientTrendView,
    FinalPilotReportView,
    PilotClosureCreate,
    PilotClosureDecision,
    PilotClosureSnapshotView,
    PilotMetricsView,
)
from app.security import CurrentUser, require_roles
from app.services.final_report import (
    anonymized_dataset_csv,
    build_final_report,
    final_report_markdown,
)
from app.services.investor_package import build_investor_package
from app.services.pilot_metrics import build_pilot_metrics


router = APIRouter(prefix="/api/v1/metrics", tags=["pilot-metrics"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]
Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]


def _client(db: Session, client_id: uuid.UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


def _closure_client_ids(db: Session, date_from: date, date_to: date) -> list[uuid.UUID]:
    start_at = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    end_at = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
    client_ids = set(
        db.scalars(
            select(Invoice.client_id).join(Client, Client.id == Invoice.client_id).where(
                Client.active.is_(True),
                Invoice.issued_on >= date_from,
                Invoice.issued_on <= date_to,
            )
        )
    )
    client_ids.update(
        db.scalars(
            select(Event.client_id).join(Client, Client.id == Event.client_id).where(
                Client.active.is_(True),
                Event.invoice_id.is_not(None),
                Event.created_at >= start_at,
                Event.created_at <= end_at,
            )
        )
    )
    return sorted(client_ids, key=str)


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


@router.get("/closures", response_model=list[PilotClosureSnapshotView])
def list_pilot_closures(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> list[PilotClosureSnapshot]:
    return list(
        db.scalars(
            select(PilotClosureSnapshot)
            .order_by(
                PilotClosureSnapshot.created_at.desc(),
                PilotClosureSnapshot.id.desc(),
            )
            .limit(100)
        )
    )


@router.get("/closures/{closure_id}/package.zip")
def download_pilot_closure_package(
    closure_id: uuid.UUID,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    snapshot = db.get(PilotClosureSnapshot, closure_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Cierre de piloto no encontrado")
    content, _manifest = build_investor_package(
        snapshot.report_data,
        closure_status=snapshot.status,
        decision=snapshot.decision,
    )
    package_hash = hashlib.sha256(content).hexdigest()
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                'attachment; filename="paquete-postulacion-'
                f'{snapshot.report_fingerprint[:16]}-{snapshot.status}.zip"'
            ),
            "X-Report-Fingerprint": snapshot.report_fingerprint,
            "X-Package-SHA256": package_hash,
        },
    )


@router.post(
    "/closures",
    response_model=PilotClosureSnapshotView,
    status_code=201,
)
def prepare_pilot_closure(
    payload: PilotClosureCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PilotClosureSnapshot:
    report = _final_report(
        db,
        date_from=payload.date_from,
        date_to=payload.date_to,
        human_hourly_cost_clp=payload.human_hourly_cost_clp,
        usd_clp_rate=payload.usd_clp_rate,
        minimum_group_size=payload.minimum_group_size,
        evidence_kind=payload.evidence_kind,
    )
    existing = db.scalar(
        select(PilotClosureSnapshot).where(
            PilotClosureSnapshot.report_fingerprint == report["fingerprint_sha256"]
        )
    )
    if existing is not None:
        return existing
    stored_report = json.loads(json.dumps(report, default=str))
    snapshot = PilotClosureSnapshot(
        report_fingerprint=report["fingerprint_sha256"],
        report_schema_version=report["schema_version"],
        evidence_kind=report["evidence_kind"],
        date_from=payload.date_from,
        date_to=payload.date_to,
        status="prepared",
        recommendation=report["g4"]["recommendation"],
        report_data=stored_report,
        economics_scenarios=stored_report["economics_scenarios"],
        backlog_priorities=stored_report["backlog_priorities"],
        prepared_by=user.id,
    )
    db.add(snapshot)
    db.flush()
    for client_id in _closure_client_ids(db, payload.date_from, payload.date_to):
        record_event(
            db,
            client_id=client_id,
            event_type="pilot.closure_prepared",
            actor_type=ActorType.HUMAN,
            actor_id=user.id,
            payload={
                "closure_id": str(snapshot.id),
                "report_fingerprint": snapshot.report_fingerprint,
                "evidence_kind": snapshot.evidence_kind,
                "recommendation": snapshot.recommendation,
            },
        )
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post(
    "/closures/{closure_id}/decision",
    response_model=PilotClosureSnapshotView,
)
def decide_pilot_closure(
    closure_id: uuid.UUID,
    payload: PilotClosureDecision,
    user: Admin,
    db: Annotated[Session, Depends(get_db)],
) -> PilotClosureSnapshot:
    snapshot = db.scalar(
        select(PilotClosureSnapshot)
        .where(PilotClosureSnapshot.id == closure_id)
        .with_for_update()
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Cierre de piloto no encontrado")
    if snapshot.status != "prepared":
        raise HTTPException(status_code=409, detail="La decisión G4 ya fue registrada")
    if not snapshot.report_data.get("g4", {}).get("ready", False):
        raise HTTPException(
            status_code=409,
            detail="La evidencia del snapshot no cumple los mínimos para decidir G4",
        )
    assumptions = snapshot.report_data["assumptions"]
    privacy = snapshot.report_data["privacy"]
    current_report = _final_report(
        db,
        date_from=snapshot.date_from,
        date_to=snapshot.date_to,
        human_hourly_cost_clp=Decimal(assumptions["human_hourly_cost_clp"]),
        usd_clp_rate=Decimal(assumptions["usd_clp_rate"]),
        minimum_group_size=int(privacy["minimum_group_size"]),
        evidence_kind=snapshot.evidence_kind,
    )
    if current_report["fingerprint_sha256"] != snapshot.report_fingerprint:
        raise HTTPException(
            status_code=409,
            detail="La evidencia cambió desde el snapshot; debe preparar un cierre nuevo",
        )
    if snapshot.prepared_by == user.id:
        raise HTTPException(
            status_code=409,
            detail="La decisión debe aprobarla una persona distinta de quien preparó el cierre",
        )
    snapshot.status = "decided"
    snapshot.decision = payload.decision
    snapshot.decided_by = user.id
    snapshot.decided_at = datetime.now(timezone.utc)
    snapshot.decision_rationale = payload.rationale.strip()
    for client_id in _closure_client_ids(db, snapshot.date_from, snapshot.date_to):
        record_event(
            db,
            client_id=client_id,
            event_type="pilot.g4_decided",
            actor_type=ActorType.HUMAN,
            actor_id=user.id,
            payload={
                "closure_id": str(snapshot.id),
                "report_fingerprint": snapshot.report_fingerprint,
                "recommendation": snapshot.recommendation,
                "decision": snapshot.decision,
                "rationale": snapshot.decision_rationale,
            },
        )
    db.commit()
    db.refresh(snapshot)
    return snapshot
