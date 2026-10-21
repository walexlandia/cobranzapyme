"""Validate the local release contract without exposing secret values."""

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release" / "phase-8.4.json"
REQUIRED_ENVIRONMENT_KEYS = (
    "APP_VERSION",
    "ENVIRONMENT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "JWT_SECRET",
    "DOCUMENT_ENCRYPTION_KEY",
    "REPORT_ANONYMIZATION_KEY",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "MINIO_ENDPOINT",
    "MINIO_BUCKET",
    "DEMO_ADMIN_EMAIL",
    "DEMO_ADMIN_PASSWORD",
)
SECRET_KEYS = (
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "DOCUMENT_ENCRYPTION_KEY",
    "REPORT_ANONYMIZATION_KEY",
    "MINIO_ROOT_PASSWORD",
    "DEMO_ADMIN_PASSWORD",
)
PLACEHOLDER_MARKERS = (
    "replace-with",
    "change-me",
    "changeme",
    "dev_only",
    "development-secret",
    "local-document-key",
    "local-report-key",
)


@dataclass(frozen=True)
class Check:
    key: str
    status: str
    detail: str


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _migration_chain() -> tuple[set[str], set[str]]:
    revisions: set[str] = set()
    parents: set[str] = set()
    for path in (ROOT / "backend" / "migrations" / "versions").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        values: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                if names and names[0] in {"revision", "down_revision"}:
                    values[names[0]] = ast.literal_eval(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in {"revision", "down_revision"}:
                    values[node.target.id] = ast.literal_eval(node.value)
        revision = values.get("revision")
        parent = values.get("down_revision")
        if isinstance(revision, str):
            revisions.add(revision)
        if isinstance(parent, str):
            parents.add(parent)
        elif isinstance(parent, (tuple, list)):
            parents.update(item for item in parent if isinstance(item, str))
    return revisions, parents


def repository_checks(manifest: dict) -> list[Check]:
    checks: list[Check] = []
    missing = [path for path in manifest["release_artifacts"] if not (ROOT / path).is_file()]
    checks.append(
        Check(
            "release_artifacts",
            "PASS" if not missing else "FAIL",
            "Todos los artefactos declarados existen."
            if not missing
            else f"Faltan: {', '.join(missing)}",
        )
    )
    revisions, parents = _migration_chain()
    heads = revisions - parents
    expected_head = manifest["database_migration_head"]
    checks.append(
        Check(
            "migration_head",
            "PASS" if heads == {expected_head} else "FAIL",
            f"Cabeza única {expected_head}."
            if heads == {expected_head}
            else f"Cabezas encontradas: {', '.join(sorted(heads)) or 'ninguna'}.",
        )
    )
    final_report = (ROOT / "backend" / "app" / "services" / "final_report.py").read_text(
        encoding="utf-8"
    )
    investor_package = (
        ROOT / "backend" / "app" / "services" / "investor_package.py"
    ).read_text(encoding="utf-8")
    schemas_match = (
        f'REPORT_SCHEMA_VERSION = "{manifest["report_schema_version"]}"' in final_report
        and f'PACKAGE_SCHEMA_VERSION = "{manifest["package_schema_version"]}"'
        in investor_package
    )
    checks.append(
        Check(
            "evidence_schemas",
            "PASS" if schemas_match else "FAIL",
            "Versiones de informe y paquete coinciden con el manifiesto."
            if schemas_match
            else "Las versiones de evidencia no coinciden con el manifiesto.",
        )
    )
    runtime_version = (ROOT / "backend" / "app" / "version.py").read_text(
        encoding="utf-8"
    )
    runtime_matches = (
        f'APP_VERSION = "{manifest["release"]}"' in runtime_version
        and f'DATABASE_MIGRATION_HEAD = "{expected_head}"' in runtime_version
    )
    checks.append(
        Check(
            "runtime_version",
            "PASS" if runtime_matches else "FAIL",
            "La versión publicada por la API coincide con release y migración."
            if runtime_matches
            else "La versión de runtime no coincide con el manifiesto.",
        )
    )
    external_gates_valid = all(
        gate.get("status") == "blocked" and gate.get("id") and gate.get("description")
        for gate in manifest["external_gates"]
    )
    checks.append(
        Check(
            "external_gates_declared",
            "PASS" if external_gates_valid else "FAIL",
            "Los bloqueos externos permanecen explícitos y no se declaran aprobados."
            if external_gates_valid
            else "El manifiesto contiene una puerta externa inválida o aprobada sin evidencia.",
        )
    )
    return checks


def environment_checks(path: Path | None, *, expected_release: str) -> list[Check]:
    if path is None:
        return [
            Check(
                "pilot_environment",
                "SKIP",
                "No se indicó --env-file; la configuración real no fue evaluada.",
            )
        ]
    if not path.is_file():
        return [Check("pilot_environment", "FAIL", "El archivo de entorno no existe.")]
    values = _load_env(path)
    missing = [key for key in REQUIRED_ENVIRONMENT_KEYS if not values.get(key)]
    placeholder_keys = [
        key
        for key in SECRET_KEYS
        if any(marker in values.get(key, "").lower() for marker in PLACEHOLDER_MARKERS)
    ]
    short_keys = [key for key in SECRET_KEYS if len(values.get(key, "")) < 16]
    independent_keys = (
        len(
            {
                values.get("JWT_SECRET"),
                values.get("DOCUMENT_ENCRYPTION_KEY"),
                values.get("REPORT_ANONYMIZATION_KEY"),
            }
        )
        == 3
    )
    release_matches = values.get("APP_VERSION") == expected_release
    environment_is_real = values.get("ENVIRONMENT") in {"pilot", "production"}
    safe = (
        not missing
        and not placeholder_keys
        and not short_keys
        and independent_keys
        and release_matches
        and environment_is_real
    )
    details = []
    if missing:
        details.append(f"faltan {', '.join(missing)}")
    if placeholder_keys:
        details.append(f"hay valores de ejemplo en {', '.join(placeholder_keys)}")
    if short_keys:
        details.append(f"secretos demasiado cortos en {', '.join(short_keys)}")
    if not independent_keys:
        details.append("JWT, cifrado documental y anonimización deben usar claves distintas")
    if not release_matches:
        details.append("APP_VERSION no coincide con el manifiesto de release")
    if not environment_is_real:
        details.append("ENVIRONMENT debe ser pilot o production")
    return [
        Check(
            "pilot_environment",
            "PASS" if safe else "FAIL",
            "Variables obligatorias presentes; secretos no se imprimen."
            if safe
            else "; ".join(details),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    checks = repository_checks(manifest) + environment_checks(
        args.env_file, expected_release=manifest["release"]
    )
    for gate in manifest["external_gates"]:
        checks.append(Check(gate["id"], "BLOCKED", gate["description"]))
    summary = {
        "release": manifest["release"],
        "ready_for_local_handoff": not any(item.status == "FAIL" for item in checks),
        "ready_for_real_pilot": not any(
            item.status in {"FAIL", "BLOCKED", "SKIP"} for item in checks
        ),
        "checks": [asdict(item) for item in checks],
    }
    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            print(f"{item.status:7} {item.key}: {item.detail}")
        print(
            "PASS local handoff" if summary["ready_for_local_handoff"] else "FAIL local handoff"
        )
        print(
            "PASS real pilot" if summary["ready_for_real_pilot"] else "BLOCKED real pilot"
        )
    failed = any(item.status == "FAIL" for item in checks)
    incomplete = any(item.status in {"BLOCKED", "SKIP"} for item in checks)
    return 1 if failed or (args.strict and incomplete) else 0


if __name__ == "__main__":
    raise SystemExit(main())
