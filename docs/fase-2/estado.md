# Estado de la Fase 2

> Inicio técnico: 14 de octubre de 2026

## Incrementos implementados — contrato y motor operativo

| Entregable | Estado | Evidencia |
|---|---|---|
| Contratos versionados por pyme | Implementado | API `contracts`, reglas tipadas y una sola versión activa por cliente |
| Horarios y frecuencia | Implementado | Ventana en `America/Santiago`, días permitidos y máximo semanal |
| Etapas de factura | Implementado | Emisión, documental, preventiva, vencimiento, mora temprana, escalamiento y cierre |
| Pausa por estado | Implementado | Pagada, anulada, reclamada y en disputa no generan acciones |
| Cola idempotente | Implementado | Clave única por cliente, contrato, pagador, destinatario y fecha local |
| Worker | Implementado | Programa y procesa trabajos vencidos con bloqueo `SKIP LOCKED` |
| Ciclo manual | Implementado | Endpoint y control en la consola web, con el mismo rastro de auditoría |
| Interfaz de contrato | Implementada | Horarios, frecuencia, tono, canales, etapas, comisión y versiones |
| Pausa y reanudación | Implementada | Control manual por factura o pagador, con motivo y reanudación opcional |
| Promesas y fechas futuras | Implementada | El worker reactiva controles al cumplirse `resume_at` |
| Agrupación de facturas | Implementada | Un trabajo por pyme, pagador, destinatario y fecha local |
| Vista de trabajos | Implementada | Estado, etapa, modo y cantidad de facturas agrupadas |
| Historial por factura | Implementado | Línea de tiempo cronológica con actor, modo y payload de cada evento |
| Simulación con fecha controlada | Implementada | Evalúa etapa, pausa, acción, ventana y versión contractual sin escribir en base de datos |
| Pausa programada en consola | Implementada | Motivo y fecha/hora opcional de reanudación desde la cartera |
| Control masivo por pagador | Implementado | Pausa o reanuda todas las facturas asociadas al pagador |
| Reconstrucción de decisiones | Cubierta por tests | Estado, programación y acción quedan enlazados mediante eventos por factura |
| Migraciones | Implementadas | `0002_workflow_engine.py` y `0003_workflow_controls_and_groups.py` |

## Validaciones ejecutadas

- Compilación sintáctica del backend.
- Siete comprobaciones offline, incluidas la transición de etapas, sus ventanas completas y el próximo horario permitido.
- Build de producción del frontend sin acceso a internet.
- Creación del esquema completo en PostgreSQL 16 local.
- Rechazo en PostgreSQL de trabajos con la misma clave de idempotencia.
- Rechazo de controles duplicados para el mismo alcance.
- Agrupación cubierta por tests preparados contra PostgreSQL.
- Tests preparados para simulación sin escrituras, aislamiento del historial, control masivo y reconstrucción de decisiones.
- Inmutabilidad de eventos y unicidad de facturas comprobadas nuevamente.

La suite HTTP/ORM completa queda preparada pero no ejecutada en este equipo: no están disponibles localmente `pytest`, `psycopg` ni `alembic`, y la construcción offline del backend no puede instalar esos paquetes sin acceso al índice. No se abrió acceso externo para resolverlo.

## Alcance deliberado de este incremento

Los trabajos procesados producen el evento `workflow.action_ready`; todavía no envían correos ni mensajes. La comunicación externa pertenece a la fase 4 y no debe activarse mientras falten proveedor, plantillas aprobadas y autorización de contacto.

## Estado de cierre técnico

Las historias técnicas E4-01 a E4-09 ya tienen una primera implementación funcional y auditable. La fase 2 queda pendiente de la evidencia externa V-02 a V-04 y V-06, bloqueada deliberadamente mientras no exista acceso y autorización para gestiones externas.

## Siguiente incremento interno recomendado — Fase 3

- Crear la ficha operativa global del pagador, separada de los datos privados de cada pyme.
- Generar el checklist de pagabilidad por factura.
- Registrar cambios de cada ítem del checklist como eventos inmutables.
- Mostrar estado de pagabilidad y requisitos faltantes en la cartera.
- Inventar casos de prueba de OC, HES, aceptación SII y portal de proveedores.
