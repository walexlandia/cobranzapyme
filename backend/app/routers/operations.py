from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Role
from app.models import (
    ClientDocumentSubmission,
    Document,
    ExceptionCase,
    Message,
    PilotLogEntry,
    ServiceHeartbeat,
    User,
    WorkflowJob,
)
from app.observability import runtime_telemetry
from app.schemas import OperationsSnapshotView
from app.security import require_roles
from app.services.operational_health import (
    THRESHOLDS,
    OperationalMetrics,
    evaluate_operational_health,
)

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]


def _count(db: Session, model: type, *criteria: object) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


def _age_seconds(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((now - value.astimezone(timezone.utc)).total_seconds()))


@router.get("/observability", response_model=OperationsSnapshotView)
def observability_snapshot(
    _: Admin,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    now = datetime.now(timezone.utc)
    oldest_pending = db.scalar(
        select(func.min(WorkflowJob.scheduled_for)).where(
            WorkflowJob.status == "pending"
        )
    )
    heartbeat = db.scalar(
        select(ServiceHeartbeat)
        .where(ServiceHeartbeat.service_name == "worker")
        .limit(1)
    )
    metrics = OperationalMetrics(
        pending_jobs=_count(db, WorkflowJob, WorkflowJob.status == "pending"),
        oldest_pending_job_age_seconds=_age_seconds(oldest_pending, now),
        open_exceptions=_count(db, ExceptionCase, ExceptionCase.status == "open"),
        open_critical_incidents=_count(
            db,
            PilotLogEntry,
            PilotLogEntry.entry_type == "incident",
            PilotLogEntry.severity == "critical",
            PilotLogEntry.status == "open",
        ),
        pending_documents=_count(
            db, ClientDocumentSubmission, ClientDocumentSubmission.status == "pending"
        ),
        failed_messages=_count(db, Message, Message.status == "failed"),
        legacy_plaintext_documents=_count(
            db,
            Document,
            Document.content.is_not(None),
            or_(
                Document.encryption_version.is_(None),
                Document.encryption_version != "aesgcm-v1",
            ),
        ),
        worker_observed=heartbeat is not None,
        worker_status=heartbeat.status if heartbeat else None,
        worker_stale_seconds=_age_seconds(heartbeat.updated_at, now)
        if heartbeat
        else None,
        worker_consecutive_failures=heartbeat.consecutive_failures if heartbeat else 0,
    )
    status, alerts = evaluate_operational_health(metrics)
    return {
        "generated_at": now,
        "overall_status": status,
        "alerts": alerts,
        "thresholds": THRESHOLDS,
        "runtime": runtime_telemetry.snapshot(),
        "workload": {
            "pending_jobs": metrics.pending_jobs,
            "oldest_pending_job_age_seconds": metrics.oldest_pending_job_age_seconds,
            "open_exceptions": metrics.open_exceptions,
            "open_critical_incidents": metrics.open_critical_incidents,
            "pending_documents": metrics.pending_documents,
            "failed_messages": metrics.failed_messages,
            "legacy_plaintext_documents": metrics.legacy_plaintext_documents,
        },
        "worker": {
            "observed": metrics.worker_observed,
            "status": metrics.worker_status,
            "stale_seconds": metrics.worker_stale_seconds,
            "consecutive_failures": metrics.worker_consecutive_failures,
            "last_started_at": heartbeat.last_started_at if heartbeat else None,
            "last_success_at": heartbeat.last_success_at if heartbeat else None,
            "last_failure_at": heartbeat.last_failure_at if heartbeat else None,
            "last_cycle": heartbeat.last_cycle if heartbeat else {},
        },
    }
