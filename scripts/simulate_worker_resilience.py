"""Deterministic offline rehearsal of worker degradation and recovery."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.operational_health import (  # noqa: E402
    OperationalMetrics,
    evaluate_operational_health,
    worker_delay_seconds,
)


def main() -> None:
    failures = 0
    delays: list[int] = []
    statuses: list[str] = []
    for succeeded in (False, False, True):
        failures = 0 if succeeded else failures + 1
        delays.append(worker_delay_seconds(failures))
        status, _ = evaluate_operational_health(
            OperationalMetrics(
                worker_observed=True,
                worker_status="healthy" if succeeded else "degraded",
                worker_stale_seconds=0,
                worker_consecutive_failures=failures,
            )
        )
        statuses.append(status)
    assert delays == [60, 120, 30]
    assert statuses == ["warning", "warning", "healthy"]
    print("PASS worker degradation/recovery: delays=60,120,30 status=warning,warning,healthy")


if __name__ == "__main__":
    main()
