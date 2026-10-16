import logging
import time

from app.database import SessionLocal
from app.services.workflow_engine import process_due_jobs, run_scheduler_cycle


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("recupera.worker")


def run() -> None:
    logger.info("worker_started")
    while True:
        try:
            with SessionLocal() as db:
                scheduled = run_scheduler_cycle(db, mode="automatic")
                processed = process_due_jobs(db)
            logger.info(
                "worker_cycle clients=%s invoices=%s jobs_created=%s jobs_processed=%s",
                scheduled.clients_processed,
                scheduled.invoices_evaluated,
                scheduled.jobs_created,
                processed,
            )
        except Exception:
            logger.exception("worker_database_unavailable")
        time.sleep(30)


if __name__ == "__main__":
    run()

