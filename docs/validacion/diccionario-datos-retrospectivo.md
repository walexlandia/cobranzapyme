# Diccionario de datos — Análisis retrospectivo

Solicitar únicamente los campos necesarios. La pyme debe reemplazar nombres, correos y teléfonos de personas por identificadores antes de entregar el archivo.

| Campo | Obligatorio | Descripción |
|---|---|---|
| `invoice_id` | Sí | Identificador interno anonimizado |
| `payer_rut` | Sí | RUT del pagador; permite detectar pagadores repetidos |
| `payer_name` | Sí | Razón social del pagador |
| `issued_on` | Sí | Fecha de emisión |
| `due_on` | Sí | Fecha pactada de pago |
| `paid_on` | No | Fecha real; vacío si sigue impaga |
| `total_amount` | Sí | Monto total de la factura |
| `accepted_on` | No | Fecha de aceptación en SII si está disponible |
| `claimed_on` | No | Fecha de reclamo si corresponde |
| `purchase_order_required` | No | Sí / No / Desconocido |
| `purchase_order_available_on` | No | Fecha desde que estuvo disponible |
| `hes_required` | No | Sí / No / Desconocido |
| `hes_available_on` | No | Fecha desde que estuvo disponible |
| `portal_required` | No | Sí / No / Desconocido |
| `portal_uploaded_on` | No | Fecha de carga confirmada |
| `first_problem_known_on` | No | Cuándo la pyme supo del bloqueo |
| `delay_cause` | No | A completar durante el análisis |
| `cause_evidence` | No | Evidencia breve y anonimizada |
| `commercial_dispute` | No | Sí / No |
| `payment_promise_on` | No | Primera fecha prometida |

## Taxonomía de causa principal

- `documental_sii`
- `documental_oc`
- `documental_hes_conformidad`
- `documental_portal`
- `documental_datos_proveedor`
- `liquidez_pagador`
- `disputa_comercial`
- `proceso_interno_pagador`
- `causa_pyme`
- `otra`
- `desconocida`

Registrar una causa principal y, si hace falta, causas secundarias. No inferir la causa solo porque falte un dato: debe existir evidencia en correos, portal, registros o entrevista.

