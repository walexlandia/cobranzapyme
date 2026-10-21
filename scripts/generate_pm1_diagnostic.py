import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal  # noqa: E402
from app.services.human_effort import (  # noqa: E402
    build_human_effort_diagnostic,
    human_effort_dataset_csv,
    human_effort_markdown,
    human_effort_report_json,
)


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use una fecha ISO YYYY-MM-DD") from exc


def main() -> int:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Genera los entregables agregados y reproducibles de PM-1."
    )
    parser.add_argument("--date-to", type=_date, default=today)
    parser.add_argument("--date-from", type=_date)
    parser.add_argument(
        "--evidence-kind",
        choices=("synthetic", "authorized_pilot"),
        default="synthetic",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "release" / "pm-1",
    )
    args = parser.parse_args()
    date_from = args.date_from or (args.date_to - timedelta(days=83))

    with SessionLocal() as db:
        report = build_human_effort_diagnostic(
            db,
            date_from=date_from,
            date_to=args.date_to,
            evidence_kind=args.evidence_kind,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "diagnostico.json"
    csv_path = args.output_dir / "fricciones.csv"
    markdown_path = args.output_dir / "informe.md"
    json_path.write_text(human_effort_report_json(report) + "\n", encoding="utf-8")
    csv_path.write_bytes(human_effort_dataset_csv(report))
    markdown_path.write_bytes(human_effort_markdown(report))

    print(
        json.dumps(
            {
                "fingerprint_sha256": report["fingerprint_sha256"],
                "pm_g1": report["pm_g1"]["status"],
                "selected_opportunity": (
                    report["selected_opportunity"]["friction_key"]
                    if report["selected_opportunity"]
                    else None
                ),
                "files": [str(json_path), str(csv_path), str(markdown_path)],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
