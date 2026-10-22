import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

def resolve_output_dir(
    *, evidence_kind: str, output_dir: Path | None
) -> Path:
    """Keep authorized evidence out of the source repository."""
    if output_dir is None:
        if evidence_kind == "authorized_pilot":
            raise ValueError(
                "authorized_pilot exige --output-dir en una ubicación segura fuera del repositorio"
            )
        return ROOT / "release" / "pm-1"
    resolved = output_dir.expanduser().resolve()
    if evidence_kind == "authorized_pilot" and resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(
            "La salida authorized_pilot no puede guardarse dentro del repositorio"
        )
    return resolved


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
        help=(
            "Directorio de salida. Es obligatorio y debe estar fuera del repositorio "
            "para authorized_pilot."
        ),
    )
    parser.add_argument(
        "--require-approved",
        action="store_true",
        help="Retorna código 2 si PM-G1 no queda approved.",
    )
    args = parser.parse_args()
    date_from = args.date_from or (args.date_to - timedelta(days=83))
    try:
        output_dir = resolve_output_dir(
            evidence_kind=args.evidence_kind,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))

    # Import database-dependent modules only after validating the output boundary.
    # This lets privacy guards run even on a workstation without backend dependencies.
    from app.database import SessionLocal
    from app.services.human_effort import (
        build_human_effort_diagnostic,
        human_effort_dataset_csv,
        human_effort_markdown,
        human_effort_report_json,
    )

    with SessionLocal() as db:
        report = build_human_effort_diagnostic(
            db,
            date_from=date_from,
            date_to=args.date_to,
            evidence_kind=args.evidence_kind,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "diagnostico.json"
    csv_path = output_dir / "fricciones.csv"
    markdown_path = output_dir / "informe.md"
    json_path.write_text(human_effort_report_json(report) + "\n", encoding="utf-8")
    csv_path.write_bytes(human_effort_dataset_csv(report))
    markdown_path.write_bytes(human_effort_markdown(report))

    print(
        json.dumps(
            {
                "fingerprint_sha256": report["fingerprint_sha256"],
                "pm_g1": report["pm_g1"]["status"],
                "approved": report["pm_g1"]["status"] == "approved",
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
    if args.require_approved and report["pm_g1"]["status"] != "approved":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
