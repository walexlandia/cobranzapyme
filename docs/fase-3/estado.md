# Estado de la Fase 3

> Inicio técnico: 15 de octubre de 2026

## Producto

| Historia | Estado | Evidencia |
|---|---|---|
| EP-01 Ficha global del pagador | Implementada | API y consola para requisitos, portal, canales y ciclo de pago |
| EP-02 Aislamiento entre pymes | Implementado | El perfil global no contiene facturas, montos, contactos privados ni notas por cliente; tests preparados |
| EP-03 Checklist por factura | Implementado | Generación automática en importación y semilla, con estados y responsables |
| EP-04 Importación SII | Implementada | CSV/XLSX con validación previa, aceptación, reclamo, rechazo y plazo |
| EP-05 Solicitud de faltantes | Implementada localmente | El motor crea acciones según requisito y responsable; no envía comunicaciones externas |
| EP-06 Evidencia de portal | Implementada | Número de ingreso, fecha y referencia de custodia auditados |
| EP-07 Riesgo antes del vencimiento | Implementado | Regla configurable por pagador y prioridad visible en cartera |
| EP-08 Confirmación preventiva | Implementada | Registro estructurado de aprobación/rechazo, fecha programada y referencia; dos eventos auditables y acción preventiva del motor |
| E11-06 Causa de atraso | Implementada | Registro por factura y resumen por cantidad y monto |

## Entregables

- Fichas globales versionadas, con historial inmutable.
- Checklist funcional con estados pagable, incompleta, en riesgo y reclamada.
- Consola de operación y vista cliente del estado de pagabilidad.
- Importación local de estados SII.
- Evidencia asistida de carga en portales.
- Línea base por pyme y reporte de causas de atraso.
- Decisión G1 documentada con datos sintéticos.
- Restricciones legales provisionales incorporadas al diseño.
- Borradores de carta de intención y mandato operativo listos para revisión externa.
- Paquete de ejecución externa preparado para V-03, V-05 y V-07, sin atribuir validaciones ni firmas inexistentes.

## Validación ejecutada

- Trece comprobaciones offline, incluidas reglas de plazo SII, confirmación preventiva, contrato público de la ficha global y compilación OpenAPI de 29 rutas.
- Compilación sintáctica del backend.
- Build de producción del frontend dentro de Docker.
- Esquema PostgreSQL 16 creado desde cero.
- Inmutabilidad de eventos y revisiones de perfiles comprobada en PostgreSQL.
- Unicidad de requisito por factura comprobada en PostgreSQL.
- Dataset ficticio ampliado con ocho perfiles y 24 estados SII.
- Informe retrospectivo reproducible sobre 120 facturas ficticias.

La suite integral del backend queda preparada, incluyendo los casos de vencimiento SII, aislamiento entre pymes y confirmación preventiva. No pudo ejecutarse en este equipo: se revisaron el entorno virtual del proyecto, el runtime de trabajo, la instalación Python 3.10, las imágenes Docker y la caché de BuildKit. La imagen base `python:3.12-slim` existe localmente, pero no la capa con dependencias de Recupera; la construcción offline falla al resolver `fastapi`. Ningún entorno disponible reúne `pytest`, `psycopg` y `alembic`, y la imagen `faenafix-app:latest` es una imagen Node sin Python. No se descargaron paquetes debido al bloqueo de red indicado para el proyecto.

## Dependencias externas pendientes

- V-03 con información real autorizada.
- V-05 con asesoría jurídica competente.
- V-07 con cartas de intención de 2–3 pymes.

Estas dependencias no bloquean el desarrollo local, pero sí impiden habilitar contactos reales y declarar validada la hipótesis de mercado.
