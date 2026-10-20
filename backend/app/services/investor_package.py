import csv
import hashlib
import io
import json
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from app.services.final_report import anonymized_dataset_csv, final_report_markdown


PACKAGE_SCHEMA_VERSION = "fase-8.3-v1"
PACKAGE_FILES = (
    "resumen-ejecutivo.md",
    "informe-final-v10.md",
    "dataset-anonimizado.csv",
    "unit-economics.csv",
    "backlog-priorizado.csv",
    "anexo-evidencia.md",
)


def _label(value: str | None) -> str:
    labels = {
        "pending": "Pendiente",
        "scale": "Escalar",
        "iterate": "Iterar",
        "pivot": "Pivotar",
        "stop": "Detener",
        "prepared": "Preparado para revisión",
        "decided": "Decidido",
        "synthetic": "Sintética / demostración",
        "authorized_pilot": "Piloto autorizado",
    }
    return labels.get(value or "", value or "No registrada")


def _markdown_bytes(lines: list[str]) -> bytes:
    return "\n".join(lines).encode("utf-8-sig")


def _csv_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def _executive_summary(
    report: dict[str, Any], *, closure_status: str, decision: str | None
) -> bytes:
    synthetic = report["evidence_kind"] == "synthetic"
    portfolio = report["portfolio"]
    observed = next(
        (
            item
            for item in report["economics_scenarios"]
            if item["key"] == "observed"
        ),
        report["economics_scenarios"][0],
    )
    lines = [
        "# Resumen ejecutivo — Piloto Recupera",
        "",
        (
            "> **BORRADOR — EVIDENCIA SINTÉTICA.** Este material sirve para "
            "demostración y no acredita resultados reales ni habilita una decisión G4."
            if synthetic
            else (
                "> **EVIDENCIA DE PILOTO AUTORIZADO.** La procedencia declarada y "
                "la decisión requieren revisión humana y documental."
            )
        ),
        "",
        "## Propuesta",
        "",
        (
            "Recupera acompaña facturas B2B desde su emisión hasta el pago y la "
            "conciliación, con controles humanos para documentos, excepciones y decisiones."
        ),
        "",
        "## Alcance medido",
        "",
        f"- Período: {report['date_from']} a {report['date_to']} ({report['period_days']} días).",
        f"- Pymes participantes: {portfolio['client_count']}.",
        f"- Facturas gestionadas: {portfolio['managed_invoices']}.",
        f"- Facturas saldadas: {portfolio['settled_invoices']}.",
        f"- Monto verificado: CLP {portfolio['verified_amount_clp']}.",
        "",
        "## Resultados y economía",
        "",
        f"- DSO agregado: {portfolio['average_dso'] or 'sin muestra'} días.",
        f"- Pago oportuno: {portfolio['on_time_percent'] or 'sin muestra'}%.",
        f"- Minutos humanos: {portfolio['human_minutes']}.",
        f"- Margen observado estimado: CLP {observed['margin_clp']} "
        f"({observed['margin_percent'] if observed['margin_percent'] is not None else 'sin muestra'}%).",
        "",
        "## Cierre y siguiente paso",
        "",
        f"- Estado del cierre: {_label(closure_status)}.",
        f"- Recomendación del modelo: {_label(report['g4']['recommendation'])}.",
        f"- Decisión humana: {_label(decision)}.",
        f"- Motivo G4: {report['g4']['reason']}",
        "",
        "El backlog priorizado, la sensibilidad económica, el dataset agregado y la "
        "trazabilidad de evidencia se incluyen como anexos verificables.",
        "",
        "## Salvaguardas",
        "",
        "El paquete excluye nombres, RUT, folios, contactos, UUID internos y la "
        "justificación libre de la decisión. Cada archivo está inventariado con SHA-256.",
        "",
    ]
    return _markdown_bytes(lines)


def _economics_csv(report: dict[str, Any]) -> bytes:
    headers = [
        "scenario",
        "label",
        "commission_clp",
        "human_cost_clp",
        "technology_cost_clp",
        "total_cost_clp",
        "cost_per_managed_invoice_clp",
        "margin_clp",
        "margin_percent",
        "human_minutes_factor",
        "technology_cost_factor",
    ]
    rows = [
        [
            item.get("key", ""),
            item.get("label", ""),
            item.get("commission_clp", ""),
            item.get("human_cost_clp", ""),
            item.get("technology_cost_clp", ""),
            item.get("total_cost_clp", ""),
            item.get("cost_per_managed_invoice_clp", ""),
            item.get("margin_clp", ""),
            item.get("margin_percent", ""),
            item.get("human_minutes_factor", ""),
            item.get("technology_cost_factor", ""),
        ]
        for item in report["economics_scenarios"]
    ]
    return _csv_bytes(headers, rows)


def _backlog_csv(report: dict[str, Any]) -> bytes:
    headers = ["priority", "key", "action", "rationale"]
    rows = [
        [item["priority"], item["key"], item["action"], item["rationale"]]
        for item in report["backlog_priorities"]
    ]
    return _csv_bytes(headers, rows)


def _evidence_appendix(
    report: dict[str, Any], *, closure_status: str, decision: str | None
) -> bytes:
    authorization = report["authorization_coverage"]
    lines = [
        "# Anexo de evidencia y reproducibilidad",
        "",
        f"- Esquema del paquete: `{PACKAGE_SCHEMA_VERSION}`.",
        f"- Esquema del informe: `{report['schema_version']}`.",
        f"- Huella del informe: `{report['fingerprint_sha256']}`.",
        f"- Tipo de evidencia: {_label(report['evidence_kind'])}.",
        f"- Estado del cierre: {_label(closure_status)}.",
        f"- Decisión registrada: {_label(decision)}.",
        f"- Método de privacidad: {report['privacy']['method']}.",
        f"- Umbral mínimo por grupo: {report['privacy']['minimum_group_size']}.",
        f"- Grupos suprimidos: {sum(item['groups'] for item in report['suppressed_groups'])}.",
        "",
        "## Cobertura de autorización",
        "",
        f"- Participantes: {authorization['participating_clients']}.",
        f"- Autorizados: {authorization['authorized_clients']}.",
        f"- Cobertura completa: {'sí' if authorization['complete'] else 'no'}.",
        "",
        "## Controles G4",
        "",
    ]
    for check in report["g4"]["readiness_checks"]:
        lines.append(f"- {'Cumple' if check['passed'] else 'Pendiente'}: `{check['key']}`.")
    lines.extend(["", "## Hipótesis", ""])
    for hypothesis in report["hypotheses"]:
        lines.append(
            f"- **{hypothesis['state']}** — {hypothesis['statement']} {hypothesis['evidence']}"
        )
    lines.extend(
        [
            "",
            "## Exclusiones",
            "",
            "No se exportan nombres, RUT, folios, contactos, identificadores internos "
            "ni texto libre de la decisión. El manifiesto permite verificar integridad, "
            "pero no reemplaza la revisión de las fuentes autorizadas.",
            "",
        ]
    )
    return _markdown_bytes(lines)


def _zip_info(filename: str) -> ZipInfo:
    info = ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def build_investor_package(
    report: dict[str, Any], *, closure_status: str, decision: str | None
) -> tuple[bytes, dict[str, Any]]:
    """Build a deterministic, privacy-minimized package from an immutable report."""
    artifacts = {
        "resumen-ejecutivo.md": _executive_summary(
            report, closure_status=closure_status, decision=decision
        ),
        "informe-final-v10.md": final_report_markdown(report),
        "dataset-anonimizado.csv": anonymized_dataset_csv(report),
        "unit-economics.csv": _economics_csv(report),
        "backlog-priorizado.csv": _backlog_csv(report),
        "anexo-evidencia.md": _evidence_appendix(
            report, closure_status=closure_status, decision=decision
        ),
    }
    manifest = {
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "report_schema_version": report["schema_version"],
        "report_fingerprint_sha256": report["fingerprint_sha256"],
        "evidence_kind": report["evidence_kind"],
        "draft": report["evidence_kind"] == "synthetic",
        "closure_status": closure_status,
        "recommendation": report["g4"]["recommendation"],
        "decision": decision,
        "files": [
            {
                "path": filename,
                "sha256": hashlib.sha256(artifacts[filename]).hexdigest(),
                "size_bytes": len(artifacts[filename]),
            }
            for filename in PACKAGE_FILES
        ],
    }
    manifest_bytes = json.dumps(
        manifest, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8")
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for filename in PACKAGE_FILES:
            archive.writestr(_zip_info(filename), artifacts[filename])
        archive.writestr(_zip_info("manifest.json"), manifest_bytes)
    return output.getvalue(), manifest
