# Estado de la Fase 8

> Inicio técnico: 19 de octubre de 2026
>
> Modalidad actual: cierre local con datos sintéticos; decisión G4 real pendiente

## Incremento 8.1 — Medición final y matriz de decisión

| Entregable | Estado local | Evidencia |
|---|---|---|
| Dataset agregado y anonimizado | Completo localmente | CSV por cliente, pagador, causa y tramo de monto; alias HMAC-SHA256 y supresión configurable de grupos pequeños |
| Informe final V-10 | Completo localmente | JSON para el portal y documento Markdown descargable con versión, parámetros y huella SHA-256 |
| Comparación por cliente | Completo localmente | DSO y pago oportuno frente a línea base, facturas, minutos humanos y margen usando solo alias |
| Análisis de segmentos | Completo localmente | Cantidad, monto nominal, monto verificado, liquidación y pago oportuno por pagador, causa y monto |
| Hipótesis | Completo como instrumento | Estados confirmada, rechazada o incierta para resultado, relevancia documental y economía |
| Matriz G4 | Completo como instrumento | Escalar, iterar, pivotar o detener con controles mínimos; el seed solo puede producir una decisión pendiente |

## Incremento 8.2 — Unit economics y cierre formal G4

| Entregable | Estado local | Evidencia |
|---|---|---|
| Sensibilidad económica | Completo localmente | Escenarios conservador, observado y eficiente con comisión, costo humano, tecnología, costo por factura y margen |
| Snapshot reproducible | Completo localmente | Informe completo persistido por huella única; reintentos devuelven el mismo snapshot |
| Separación de funciones | Completo | Operador o administrador prepara; solo otro administrador puede registrar la decisión |
| Bloqueo sintético | Completo | Un snapshot sin evidencia autorizada o mínimos G4 nunca acepta una decisión |
| Decisión inmutable | Completo | Una vez decidida no puede reemplazarse por API; registra responsable, fecha y justificación |
| Evidencia vigente | Completo | Antes de decidir se recalcula la huella; cualquier cambio exige preparar un snapshot nuevo |
| Auditoría por pyme | Completo | Eventos `pilot.closure_prepared` y `pilot.g4_decided` para cada cliente activo incluido |
| Backlog por evidencia | Completo localmente | Prioridades deterministas según resultado, hipótesis documental, economía, concentración y recomendación G4 |

La migración `0015` agrega `pilot_closure_snapshots`. El snapshot conserva exclusivamente el informe agregado y anonimizado, los escenarios económicos y el backlog priorizado; no almacena nombres, RUT, folios, contactos ni UUID de clientes o pagadores.

## Incremento 8.3 — Paquete de postulación e inversionistas

| Entregable | Estado local | Evidencia |
|---|---|---|
| Resumen ejecutivo | Completo localmente | Propuesta, alcance, resultados, economía y cierre derivados del snapshot |
| Anexos separados | Completo localmente | Informe V-10, dataset anonimizado, unit economics, backlog y anexo de evidencia |
| ZIP consolidado | Completo localmente | Orden y metadatos internos fijos para producir bytes deterministas |
| Manifiesto verificable | Completo localmente | Versión, huella del informe y SHA-256/tamaño por archivo |
| Control de privacidad | Completo | Excluye datos identificatorios, UUID y justificación libre de la decisión |
| Rotulado sintético | Completo | Resumen y manifiesto marcan inequívocamente el paquete como borrador |

Guía de uso y verificación: `docs/fase-8/paquete-postulacion.md`.

Documento de continuidad: `docs/fase-8/backlog-posterior.md`.

## Límites deliberados

- No se agregaron tablas ni datos de resultado inventados: el cierre se calcula desde los registros auditables existentes.
- La segmentación usa facturas emitidas dentro del período y resultados derivados de pagos verificados.
- El dataset no contiene nombres, RUT, folios, contactos ni UUID internos.
- Un grupo se publica solo si alcanza `minimum_group_size`; el valor predeterminado es 2.
- Los seudónimos son deterministas dentro de la instalación mediante una clave independiente, pero no son reversibles desde el exportado.
- Declarar `authorized_pilot` identifica la procedencia informada por el operador; no reemplaza mandato, autorización ni revisión de evidencia.
- La decisión G4 exige evidencia autorizada, al menos 42 días, 2 pymes y 10 facturas saldadas.

## Trabajo externo pendiente

La funcionalidad permite cerrar el informe, pero los datos sintéticos no validan el negocio. Continúan pendientes la operación real de 6–8 semanas, la aceptación de las pymes, la revisión de incidentes y la aprobación humana de la decisión de continuidad.

## Validación local

- Compilación Python aprobada para aplicación, pruebas y scripts.
- 27 comprobaciones offline aprobadas, incluidas migración `0015`, escenarios económicos, backlog, contratos de cierre G4 y contenido determinista del paquete de postulación.
- Build de producción Next.js aprobado usando la imagen local `recupera-web:phase7-4` y los archivos de Fase 8.3 montados sin red.
- Esquema completo de 37 tablas creado en PostgreSQL 16 dentro de una base desechable.
- Trigger de cierre probado en PostgreSQL: bloquea cambios de evidencia, segunda decisión y borrado; permite únicamente la primera transición válida a `decided`.
- Prueba HTTP/PostgreSQL preparada en `backend/tests/test_final_report.py` para privacidad, exportaciones, snapshot idempotente, evidencia obsoleta, bloqueo sintético, separación de funciones e inmutabilidad.
- La ejecución integral de `pytest` queda pendiente: el runtime backend no está disponible localmente y Docker no puede descargar dependencias por el firewall.
