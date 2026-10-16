"""Generate and score a balanced, synthetic Phase 5 evaluation fixture.

The fixture is intentionally separate from the human-reviewed evaluation tables:
synthetic results are useful for regression testing but never unlock automation.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.classification import _classification_result  # noqa: E402


CLEAR_CASES = {
    "paid": [
        "La transferencia ya fue realizada y adjunto el comprobante.",
        "El pago fue efectuado esta mañana.",
        "La factura ya está pagada.",
    ],
    "payment_scheduled": [
        "El pago quedó programado para el 24/10/2026.",
        "La transferencia está programada para el 24/10/2026.",
        "La fecha de pago es el 24/10/2026.",
    ],
    "missing_oc_hes": [
        "Falta la OC para procesar la factura.",
        "La factura continúa sin HES.",
        "La orden de compra está pendiente.",
    ],
    "supplier_data_issue": [
        "El proveedor no está registrado.",
        "Los datos bancarios están incorrectos.",
        "Se deben actualizar los datos del proveedor.",
    ],
    "invoice_disputed": [
        "La factura fue reclamada por recepción.",
        "La factura está rechazada.",
        "Existe rechazo de la factura.",
    ],
    "payment_promise": [
        "Pagaremos el 24/10/2026.",
        "Tenemos un compromiso de pago para el viernes.",
        "Nos comprometemos a pagar durante esta semana.",
    ],
    "dispute": [
        "El monto no corresponde al servicio recibido.",
        "Existe una discrepancia comercial.",
        "No reconocemos la deuda informada.",
    ],
    "document_request": [
        "Necesitamos que envíe la factura en PDF.",
        "Solicitamos la HES asociada.",
        "Por favor adjuntar el certificado requerido.",
    ],
    "wrong_contact": [
        "Este es un contacto equivocado.",
        "Este correo no corresponde a este contacto.",
        "Contacte a la casilla central de proveedores.",
    ],
    "other": [
        "Gracias, revisaremos internamente y volveremos con información.",
        "El caso fue recibido por nuestro equipo.",
        "Por ahora no tenemos nuevos antecedentes.",
    ],
}

CHALLENGE_CASES = {
    "paid": ["Tesorería cerró el saldo ayer.", "La obligación quedó cancelada."],
    "payment_scheduled": ["Tesorería lo dejó para el próximo viernes.", "Entrará en la siguiente corrida."],
    "missing_oc_hes": ["Requerimos la orden interna antes de contabilizar.", "Aún no emiten la hoja de servicio."],
    "supplier_data_issue": ["La ficha maestra requiere corrección.", "No encontramos al emisor en el maestro."],
    "invoice_disputed": ["El documento tributario presenta reparos.", "Contabilidad devolvió el documento."],
    "payment_promise": ["La cancelaremos durante la próxima semana.", "Quedó el compromiso para el viernes."],
    "dispute": ["Tenemos diferencias con lo facturado.", "El valor informado debe revisarse."],
    "document_request": ["¿Nos comparten el respaldo asociado?", "Requerimos los antecedentes del servicio."],
    "wrong_contact": ["Esta casilla no gestiona pagos.", "Debe verlo otra unidad."],
    "other": [
        "Adjunto el comprobante solo como referencia histórica.",
        "La fecha de pago del contrato no aplica a esta consulta.",
    ],
}


def main() -> None:
    fixture_dir = ROOT / "data" / "demo" / "evaluation"
    output_dir = ROOT / "outputs"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_rows: list[dict] = []
    result_rows: list[dict] = []
    for category, clear_texts in CLEAR_CASES.items():
        texts = [
            f"{clear_texts[index % len(clear_texts)]} Caso sintético {index + 1}."
            for index in range(18)
        ] + CHALLENGE_CASES[category]
        for index, message in enumerate(texts, start=1):
            case_id = f"{category}-{index:02d}"
            predicted, confidence, evidence = _classification_result(message)
            source_rows.append(
                {
                    "case_id": case_id,
                    "source_kind": "synthetic",
                    "actual_category": category,
                    "text": message,
                }
            )
            result_rows.append(
                {
                    "case_id": case_id,
                    "source_kind": "synthetic",
                    "actual_category": category,
                    "predicted_category": predicted,
                    "correct": predicted == category,
                    "confidence": str(confidence),
                    "ambiguous": bool(evidence.get("ambiguous")),
                    "text": message,
                }
            )
    source_path = fixture_dir / "phase5-balanced.csv"
    result_path = output_dir / "phase5-balanced-results.csv"
    with source_path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=source_rows[0].keys())
        writer.writeheader()
        writer.writerows(source_rows)
    with result_path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=result_rows[0].keys())
        writer.writeheader()
        writer.writerows(result_rows)
    categories: list[dict] = []
    for category in CLEAR_CASES:
        actual = [row for row in result_rows if row["actual_category"] == category]
        predicted = [row for row in result_rows if row["predicted_category"] == category]
        true_positive = sum(1 for row in actual if row["predicted_category"] == category)
        categories.append(
            {
                "category": category,
                "actual_count": len(actual),
                "predicted_count": len(predicted),
                "correct_count": true_positive,
                "precision": round(true_positive / len(predicted), 4) if predicted else None,
                "recall": round(true_positive / len(actual), 4) if actual else None,
            }
        )
    confusion = Counter(
        (row["actual_category"], row["predicted_category"])
        for row in result_rows
        if not row["correct"]
    )
    report = {
        "dataset": "phase5-balanced",
        "source_kind": "synthetic",
        "sample_count": len(result_rows),
        "samples_per_category": 20,
        "correct_count": sum(1 for row in result_rows if row["correct"]),
        "accuracy": round(
            sum(1 for row in result_rows if row["correct"]) / len(result_rows), 4
        ),
        "eligible_for_automation": False,
        "reason": "Los datos sintéticos sirven para regresión y no habilitan la puerta G2.",
        "categories": categories,
        "confusion_errors": [
            {"actual": actual, "predicted": predicted, "count": count}
            for (actual, predicted), count in sorted(confusion.items())
        ],
    }
    report_path = output_dir / "phase5-g2-synthetic-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"PASS synthetic evaluation: {report['sample_count']} samples, "
        f"accuracy={report['accuracy']:.2%}, automation=false"
    )
    print(source_path)
    print(result_path)
    print(report_path)


if __name__ == "__main__":
    main()
