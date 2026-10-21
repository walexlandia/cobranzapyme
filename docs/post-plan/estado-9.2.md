# Bloque post-plan 9.2 — observabilidad y resiliencia local

Fecha de corte: 2026-10-21.

Este bloque no crea una novena fase del plan original. Refuerza la operación local ya entregada y mantiene explícitamente bloqueadas las dependencias externas del piloto.

## Alcance completado

| Tarea | Estado | Evidencia |
|---|---|---|
| Telemetría HTTP acotada | Completo | Contadores por familia de estado y latencia, concurrencia y promedio; sin rutas, payloads ni identificadores |
| Diagnóstico administrativo | Completo | `GET /api/v1/operations/observability`, exclusivo para rol administrador |
| Alertas deterministas | Completo | Reglas puras y umbrales versionados para cola, worker, incidentes, cifrado, entregas y bandejas |
| Resiliencia del worker | Completo | Latido persistido, estado degradado, contador de fallos y backoff exponencial limitado a 300 segundos |
| Ensayo de degradación/recuperación | Completo | `python scripts/simulate_worker_resilience.py` |
| Runbook operativo | Completo | `docs/post-plan/runbook-observabilidad.md` |

## Validación ejecutada

- 30 comprobaciones offline aprobadas.
- 71 pruebas HTTP/ORM aprobadas sobre PostgreSQL 16, con aislamiento de datos entre casos.
- Cadena Alembic aplicada desde una base vacía hasta `0016`.
- Ciclo real del worker aprobado con latido `healthy` y cero fallos consecutivos.
- Build de producción Next.js y configuración Compose de piloto aprobados mediante la regresión unificada.

## Límites deliberados

- La telemetría reside en memoria por proceso y se reinicia con la API; el estado del worker sí se comparte mediante PostgreSQL.
- El endpoint entrega agregados y no expone clientes, usuarios, RUT, folios, correos, cuerpos de mensajes ni documentos.
- No se configuraron servicios externos de monitoreo, alertas, correo o mensajería por el bloqueo de red y la falta de infraestructura autorizada.
- Una alerta informa una condición; no ejecuta acciones financieras, comunicaciones ni cambios de datos.

## Criterio de cierre local

La migración `0016` debe estar aplicada, el worker debe registrar un ciclo saludable y las comprobaciones offline, el build web y la verificación de Compose deben terminar correctamente. Las alertas críticas abiertas se gestionan con el runbook y no se ocultan para obtener un estado artificialmente saludable.
