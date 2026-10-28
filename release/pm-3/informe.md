# PM-3 — Comparables y atribución defendible

Período: 2026-09-01 a 2026-10-28
Tipo de evidencia: synthetic
Huella SHA-256: `817425a84214c74f0db6f9aa4c8a220c87f3257258d55618e1b3b4383768f491`

> Una cadena temporal incompleta se declara correlación o incertidumbre; no se presenta como atribución.

## Cobertura

- Pagos verificados: 6.
- Pagos incluidos: 4.
- Pagos excluidos: 2.
- Cobertura trazable: 66.67%.
- Duplicados: 0.

## Matriz de comparables

| Dimensión | Segmento | Pagos | Monto | Base oportuno | Observado | Δ puntos |
|---|---|---:|---:|---:|---:|---:|
| amount_band | 500k_a_2m | 4 | 4000000.00 | 37.50% | 75.00% | 37.50 |
| cause | missing_document | 2 | 2000000.00 | 37.50% | 50.00% | 12.50 |
| cause | purchase_order | 2 | 2000000.00 | 37.50% | 100.00% | 62.50 |
| client | PYME-13F8D00AAB | 2 | 2000000.00 | 40.00% | 50.00% | 10.00 |
| client | PYME-7DE7739471 | 2 | 2000000.00 | 35.00% | 100.00% | 65.00 |
| industry | construccion | 2 | 2000000.00 | 35.00% | 100.00% | 65.00 |
| industry | servicios_empresariales | 2 | 2000000.00 | 40.00% | 50.00% | 10.00 |
| payer | PAGADOR-949C3860F4 | 2 | 2000000.00 | 37.50% | 50.00% | 12.50 |
| payer | PAGADOR-B168031A58 | 2 | 2000000.00 | 37.50% | 100.00% | 62.50 |

## Exclusiones

- `management_evidence_missing`: 1 pagos; CLP 800000.00. No existe evidencia de gestión previa elegible.
- `missing_client_baseline`: 1 pagos; CLP 600000.00. La pyme no tiene línea base completa.

## Puerta PM-G3

Estado: **passed_synthetic**.

Todos los resultados incluidos reconstruyen pago, evidencia, gestión y regla contractual; las exclusiones están declaradas.
