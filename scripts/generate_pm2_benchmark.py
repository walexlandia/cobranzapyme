#!/usr/bin/env python3

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.guided_work import (
    build_pm2_benchmark,
    pm2_benchmark_markdown,
)


def _fixture_records(path: Path) -> tuple[list[SimpleNamespace], list[SimpleNamespace]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != "pm-2-fixture-v1":
        raise ValueError("Versión de fixture PM-2 no soportada")
    if fixture.get("evidence_kind") != "synthetic":
        raise ValueError("El fixture versionado sólo puede contener evidencia sintética")
    sessions: list[SimpleNamespace] = []
    events: list[SimpleNamespace] = []
    for row in fixture.get("sessions", []):
        session_id = uuid.UUID(row["id"])
        sessions.append(
            SimpleNamespace(
                id=session_id,
                status="completed",
                baseline_minutes=Decimal(row["baseline_minutes"]),
                human_minutes=Decimal(row["human_minutes"]),
                idempotency_key=row["idempotency_key"],
                pilot_log_entry_id=uuid.uuid5(session_id, "pilot-log"),
                completed_by=uuid.uuid5(session_id, "operator"),
                completed_at=datetime(2026, 10, 28, 12, tzinfo=timezone.utc),  # noqa: UP017
            )
        )
        for event_type in (
            "optimization.guided_work_started",
            "optimization.guided_work_completed",
        ):
            events.append(
                SimpleNamespace(
                    event_type=event_type,
                    payload={"guided_work_session_id": str(session_id)},
                )
            )
    return sessions, events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "data" / "demo" / "pm2-guided-review-benchmark.json",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "release" / "pm-2"
    )
    args = parser.parse_args()
    sessions, events = _fixture_records(args.fixture.resolve())
    report = build_pm2_benchmark(sessions, events)
    if report["pm_g2"]["status"] != "passed_synthetic":
        print(json.dumps(report["pm_g2"], ensure_ascii=False), file=sys.stderr)
        return 2
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "informe.md").write_bytes(pm2_benchmark_markdown(report))
    print(
        json.dumps(
            {
                "pm_g2": report["pm_g2"]["status"],
                "reduction_percent": report["reduction_percent"],
                "fingerprint_sha256": report["fingerprint_sha256"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
