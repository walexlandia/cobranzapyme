# Estado de la Fase 4

> Inicio técnico: 15 de octubre de 2026  
> Restricción vigente: operación exclusivamente local, sin contactos externos
> Estado técnico local: completado; integraciones y validaciones externas pendientes

## Incremento 4.1 — Salida multicanal simulada

| Historia | Estado | Evidencia |
|---|---|---|
| E5-01 Email por cliente | Implementado en simulación | Remitente, destinatario, facturas agrupadas, adjuntos y datos de pago quedan materializados en la bandeja local |
| E5-03 WhatsApp | Parcial seguro | No existe envío automático; se genera únicamente un enlace para modo asistido |
| E5-06 Opt-out | Implementado | Preferencia por email/WhatsApp y bloqueo inmediato de borradores pendientes |
| E5-07 WhatsApp asistido | Implementado localmente | Texto y enlace preparados, nunca abiertos ni enviados por el sistema |
| E6-01 Redacción contextual | Implementado sin LLM | Plantillas deterministas según acción, etapa, destinatario, facturas y requisitos faltantes |
| E6-08 Seguridad | Implementado | Campos permitidos, detección de presión/amenazas/promesas y plantilla de respaldo |
| E8-01 Datos de transferencia | Implementado | Sólo se incluyen campos bancarios autorizados del cliente en acciones de pago |
| E11-01 Costos por factura | Implementado para simulación | Costo de LLM y mensajería, moneda y asignación por factura agrupada |

## Incremento 4.2 — Recepción y respuestas locales

| Historia | Estado | Evidencia |
|---|---|---|
| E5-02 Email entrante | Implementado en simulación | Webhook local idempotente, correlación por respuesta, contacto y folio, y adjuntos ficticios asociados |
| E5-04 WhatsApp entrante | Implementado en simulación | Asociación por clave externa, teléfono o hilo existente, sin conexión con Meta |
| E5-10 Respuesta por otro medio | Implementado | Registro de teléfono, correo personal u otro canal dentro del mismo historial auditable |
| E5-05 Entrega y lectura | Adelantado parcialmente | Transiciones locales `simulated → delivered → read` y falla, con evento inmutable; falta confirmación de proveedor real |

## Componentes entregados

- Plantillas por cliente, canal y acción, con versiones y una versión activa.
- Hilos por cliente, pagador, contacto y canal.
- Bandeja de mensajes con estados `draft`, `assisted_ready`, `blocked` y `simulated`.
- Idempotencia entre trabajo del motor y mensaje preparado.
- Asociación de un mensaje con múltiples facturas y documentos.
- Preparación automática cuando el worker procesa un trabajo vencido.
- Preparación manual desde la consola para validar trabajos existentes.
- Simulador local que nunca ejecuta una entrega externa.
- Datos ficticios de remitentes, cuentas bancarias, contactos y plantillas.
- Bandeja bidireccional con mensajes salientes, respuestas entrantes y registros manuales.
- Correlación entrante siempre limitada al cliente y pagador correspondientes.
- Folios inexistentes o ambiguos quedan visibles y sin asociación automática.
- Estados locales de entrega y lectura sin interpretar la simulación como confirmación real.
- Respuestas ficticias con acuses adjuntos creadas por el `seed` de demostración.

## Validación ejecutada

- Compilación Python sin errores.
- Quince verificaciones offline aprobadas.
- Contrato OpenAPI compilado con las rutas de comunicaciones.
- Build de producción Next.js aprobado con red deshabilitada.
- Esquema completo creado desde cero en PostgreSQL 16.
- Invariantes PostgreSQL aprobados para plantillas, mensajes y asociaciones.
- Tests integrales preparados para salida, entrada idempotente, adjuntos, correlación, respuestas manuales y estados de entrega.

## Próximo trabajo local

1. Ejecutar una prueba integral backend cuando exista una imagen local con las dependencias Python.
2. La entrada al flujo de clasificación supervisada fue entregada al incremento 5.1.

## Dependencias externas pendientes

- Proveedor y dominio de correo para envío, entregabilidad y webhooks reales.
- Cuenta y plantillas aprobadas de WhatsApp Business.
- Plantillas aprobadas por las pymes piloto.
- Contrato y autorización V-06, además del desbloqueo legal pendiente de Fase 3.

Ninguna comunicación real debe habilitarse hasta completar estas condiciones.
