import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import ServiceHeartbeat
from app.services.operational_health import worker_delay_seconds
from app.services.workflow_engine import process_due_jobs, run_scheduler_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("recupera.worker")


def record_worker_heartbeat(
    *,
    started_at: datetime,
    succeeded: bool,
    details: dict,
) -> int:
    moment = datetime.now(timezone.utc)
    with SessionLocal() as db:
        heartbeat = db.scalar(
            select(ServiceHeartbeat)
            .where(ServiceHeartbeat.service_name == "worker")
            .with_for_update()
        )
        if heartbeat is None:
            heartbeat = ServiceHeartbeat(
                service_name="worker",
                status="healthy" if succeeded else "degraded",
                last_started_at=started_at,
                consecutive_failures=0,
                last_cycle={},
            )
            db.add(heartbeat)
        heartbeat.last_started_at = started_at
        if succeeded:
            heartbeat.status = "healthy"
            heartbeat.last_success_at = moment
            heartbeat.consecutive_failures = 0
        else:
            heartbeat.status = "degraded"
            heartbeat.last_failure_at = moment
            heartbeat.consecutive_failures += 1
        heartbeat.last_cycle = details
        db.commit()
        return heartbeat.consecutive_failures


def run_worker_cycle() -> dict[str, int]:
    with SessionLocal() as db:
        scheduled = run_scheduler_cycle(db, mode="automatic")
        processed = process_due_jobs(db)
    return {
        "clients_processed": scheduled.clients_processed,
        "invoices_evaluated": scheduled.invoices_evaluated,
        "jobs_created": scheduled.jobs_created,
        "jobs_processed": processed,
    }


def run() -> None:
    logger.info("worker_started")
    started_at = datetime.now(timezone.utc)
    local_failures = 0
    while True:
        try:
            details = run_worker_cycle()
            record_worker_heartbeat(
                started_at=started_at,
                succeeded=True,
                details=details,
            )
            local_failures = 0
            logger.info(
                "worker_cycle clients=%s invoices=%s jobs_created=%s jobs_processed=%s",
                details["clients_processed"],
                details["invoices_evaluated"],
                details["jobs_created"],
                details["jobs_processed"],
            )
        except Exception as exc:
            local_failures += 1
            logger.exception("worker_database_unavailable")
            try:
                local_failures = record_worker_heartbeat(
                    started_at=started_at,
                    succeeded=False,
                    details={"error_type": type(exc).__name__},
                )
            except Exception:
                logger.exception("worker_heartbeat_unavailable")
        delay = worker_delay_seconds(local_failures)
        logger.info(
            "worker_next_cycle delay_seconds=%s failures=%s", delay, local_failures
        )
        time.sleep(delay)


if __name__ == "__main__":
    run()
