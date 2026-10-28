#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.comparables import (
    comparables_markdown,
    comparables_matrix_csv,
    compile_comparables_report,
)


def _load_fixture(path: Path) -> tuple[dict, list[dict]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != "pm-3-fixture-v1":
        raise ValueError("Versión de fixture PM-3 no soportada")
    if fixture.get("evidence_kind") != "synthetic":
        raise ValueError("El fixture versionado sólo puede contener evidencia sintética")
    cases = []
    for row in fixture.get("cases", []):
        cases.append(
            {
                **row,
                "baseline_dso": (
                    Decimal(row["baseline_dso"])
                    if row["baseline_dso"] is not None
                    else None
                ),
                "baseline_on_time_percent": (
                    Decimal(row["baseline_on_time_percent"])
                    if row["baseline_on_time_percent"] is not None
                    else None
                ),
                "amount": Decimal(row["amount"]),
            }
        )
    return fixture, cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "data" / "demo" / "pm3-comparables-fixture.json",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "release" / "pm-3"
    )
    args = parser.parse_args()
    fixture, cases = _load_fixture(args.fixture.resolve())
    report = compile_comparables_report(
        cases,
        date_from=date.fromisoformat(fixture["date_from"]),
        date_to=date.fromisoformat(fixture["date_to"]),
        minimum_group_size=int(fixture["minimum_group_size"]),
        evidence_kind="synthetic",
        anonymization_key="pm-3-synthetic-fixture-anonymization-key",
        authorization_complete=False,
    )
    if report["pm_g3"]["status"] != "passed_synthetic":
        print(json.dumps(report["pm_g3"], ensure_ascii=False), file=sys.stderr)
        return 2
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reporte.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "matriz-comparables.csv").write_bytes(
        comparables_matrix_csv(report)
    )
    (output_dir / "informe.md").write_bytes(comparables_markdown(report))
    print(
        json.dumps(
            {
                "pm_g3": report["pm_g3"]["status"],
                "included_payments": report["population"]["included_payments"],
                "excluded_payments": report["population"]["excluded_payments"],
                "fingerprint_sha256": report["fingerprint_sha256"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
