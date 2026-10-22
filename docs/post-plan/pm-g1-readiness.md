# PM-G1 — Checklist de evidencia autorizada

Fecha de preparación local: 2026-10-22.

Este documento cierra la preparación de PM-1 y define cómo evaluar PM-G1 sin confundir datos sintéticos con evidencia real. No autoriza PM-2 por sí mismo.

## Condición de entrada

Para cada pyme que aporte casos al flujo seleccionado deben existir, durante todo el período medido:

| Evidencia | Criterio verificable | Estado local |
|---|---|---|
| Contrato | Contrato activo y versión identificable | Instrumentado |
| Mandato | Autorización `approved`, vigente y asociada al contrato activo | Instrumentado |
| Comprobante | Documento cifrado vinculado a la autorización | Instrumentado |
| Período | `valid_from` anterior o igual al inicio y `valid_until` posterior o igual al cierre | Instrumentado |
| Medición | Casos del flujo seleccionado con 100% de minutos confirmados | Instrumentado |
| Contabilización | Bitácora clasificada como adicional o incluida en una excepción | Instrumentado |
| Privacidad | Salida agregada sin nombres, RUT, folios, UUID ni texto libre | Verificado localmente |

La falta de un solo elemento deja el gate en `authorization_incomplete` o `measurement_gaps`. Sólo el estado `approved` puede establecer `pm2_authorized: true`.

## Secuencia operativa

1. Un administrador verifica contrato, responsables, período y alcance autorizado.
2. La autorización se registra en `POST /api/v1/pilot/authorizations` con el comprobante. El sistema cifra el documento y conserva su huella SHA-256.
3. Se confirma `ready: true` en `GET /api/v1/pilot/readiness?client_id=<uuid>` para cada pyme participante.
4. Se registra el esfuerzo real en cada revisión. Cero minutos debe ser una medición explícita; un valor heredado sin confirmación no se usa en la línea base.
5. Se ejecuta el diagnóstico fuera del repositorio, en una ubicación segura:

```powershell
python scripts/generate_pm1_diagnostic.py `
  --date-from AAAA-MM-DD `
  --date-to AAAA-MM-DD `
  --evidence-kind authorized_pilot `
  --output-dir C:\ruta-segura\pm-g1
```

6. Dos personas revisan el JSON, el CSV agregado y el informe Markdown. Se verifica una sola oportunidad material, ausencia de brechas y cobertura completa de autorización.
7. PM-G1 se considera aprobada únicamente si el reporte devuelve simultáneamente:

```text
pm_g1.status = approved
pm_g1.measurement_complete = true
pm_g1.authorization_coverage.complete = true
pm_g1.pm2_authorized = true
```

## Rechazo y reversión

- Si la autorización vence, cambia el contrato o se revoca, se repite el reporte y PM-2 vuelve a quedar bloqueada.
- Una autorización se revoca mediante `POST /api/v1/pilot/authorizations/{id}/revoke`; el historial no se elimina ni reescribe.
- Los registros heredados sin medición se excluyen; no se rellenan mediante estimaciones.
- Los minutos marcados `included_in_exception` no se suman nuevamente desde la bitácora.
- Si más de una fricción parece prioritaria o ninguna es material, no se elige por conveniencia: se amplía la medición.

## Evidencia que no debe guardarse en Git

- contratos o mandatos firmados;
- datos identificatorios de clientes, contactos o pagadores;
- mensajes, notas libres, documentos tributarios o comprobantes bancarios;
- secretos, claves de cifrado o archivos de entorno reales;
- reportes de PM-G1 que permitan reidentificar una muestra pequeña.

Git conserva solamente este procedimiento, las pruebas automatizadas y el snapshot sintético. La evidencia real queda en el repositorio documental autorizado por la organización.

## Estado

Preparación técnica: **completa localmente**.

Evidencia real: **pendiente de EXT-02 y EXT-03**.

PM-2: **bloqueada hasta que un reporte autorizado devuelva `approved`**.
