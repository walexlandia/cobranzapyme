# Estado de la Fase 7

> Inicio técnico: 16 de octubre de 2026
> Modalidad actual: piloto local con datos sintéticos y sin entregas externas

## Incremento 7.1 — Vista cliente y reporte semanal

| Historia | Estado local | Evidencia |
|---|---|---|
| E10-01 Reporte semanal | Completo localmente | Resumen JSON y CSV con período, cartera, pagos verificados, saldos y pendientes de la pyme |
| E10-02 Vista web de solo lectura | Completo localmente | Panel por rol cliente y previsualización para operador, con fecha de corte configurable |
| Aislamiento multiempresa | Verificado por contrato y prueba preparada | El cliente ignora cualquier `client_id` externo y el operador debe indicar uno |
| Datos demostrables | Completo | El seed genera pagos verificados y comprobantes sintéticos cifrados para tres pymes ficticias |

## Comportamiento entregado

- La vista calcula el estado a una fecha de corte sin modificar facturas, flujos ni checklists.
- Muestra facturas pagables, en riesgo, pagadas, pendientes de la pyme y en disputa.
- Los montos pagados consideran únicamente pagos verificados hasta la fecha de corte.
- Cada factura expone total, pagado, saldo, pagabilidad, avance del checklist y requisitos pendientes de la pyme.
- El reporte semanal informa los pagos verificados en los últimos siete días y exporta el detalle en CSV UTF-8.
- Todas las consultas autenticadas siguen entrando al ledger de accesos de Fase 6.
- La entrega por email permanece deshabilitada mientras no exista infraestructura externa autorizada.

## Incremento 7.2 — Documentos solicitados

| Historia | Estado local | Evidencia |
|---|---|---|
| E10-03 Carga desde la vista cliente | Completo localmente | Selector de requisito, formatos permitidos, máximo 10 MB y confirmación de envío |
| Cifrado y trazabilidad | Completo | AES-256-GCM, SHA-256, documento asociado a factura/requisito y eventos inmutables |
| Prevención de duplicados | Completo | Restricción única por cliente, requisito y hash; reintentos devuelven el envío existente |
| Revisión del operador | Completo | Bandeja pendiente, aceptación o rechazo motivado; solo la aceptación completa el requisito |
| Datos demostrables | Completo | Una evidencia ficticia pendiente de revisión por cada pyme del seed |

La tabla `client_document_submissions` separa el archivo cifrado de su decisión de revisión. La interfaz nunca expone el contenido ni permite que un cliente complete directamente su checklist.

## Incremento 7.3 — Métricas del piloto

| Historia | Estado local | Evidencia |
|---|---|---|
| E10-05 Evolución para el cliente | Completo localmente | DSO y pago oportuno actuales comparados con la línea base, más tendencia semanal sin exponer costos internos |
| E11-02 Resultados y economía | Completo localmente | Facturas gestionadas, recuperación, minutos humanos, costos, costo por factura, comisiones y margen |
| E11-03 Línea base y evolución | Completo localmente | Serie semanal de facturas saldadas, DSO, pago oportuno y monto verificado |
| E11-04 Exportación | Completo localmente | CSV UTF-8 con resumen, supuestos, causas y tendencia |
| E11-05 Automatización | Completo localmente | Desglose automático/manual para mensajes, clasificaciones y actividades de conciliación |
| E11-06 Causas de atraso | Completo localmente | Cantidad de facturas y monto nominal agrupados por causa registrada en el período |
| E11-07 Resolución documental | Completo localmente | Tiempo promedio en horas por tipo de requisito completado |

Los indicadores usan exclusivamente pagos verificados. El DSO se calcula cuando los pagos acumulados cubren el total de la factura, y el pago oportuno compara esa fecha de liquidación con el vencimiento. Los supuestos de costo humano y conversión USD/CLP son visibles, editables y quedan separados de los hechos almacenados. El rango máximo por consulta es de 366 días.

La prueba de integración `backend/tests/test_pilot_metrics.py` construye dos facturas ficticias —una pagada a tiempo y otra atrasada— junto con costos, comisión, intervención humana y requisito documental. Verifica los resultados exactos, el CSV y el aislamiento por rol.

## Validación local

- Compilación Python aprobada.
- Contrato OpenAPI del portal, documentos y métricas aprobado.
- 25 comprobaciones offline aprobadas, incluidos los contratos del panel y un cálculo completo con datos sintéticos.
- Build de producción Next.js aprobado con la imagen local `recupera-web:phase7-3`.
- Pruebas HTTP/PostgreSQL agregadas en `backend/tests/test_client_portal.py`, `backend/tests/test_client_documents.py` y `backend/tests/test_pilot_metrics.py`; su ejecución integral sigue pendiente porque el entorno local no contiene `pytest` ni la imagen backend con dependencias.

## Próximo incremento 7.4

1. Registro visible de decisiones e incidencias del piloto.
2. Recorrido demostrable de punta a punta sin acceso directo a la base de datos.
3. Guion de operación, cierre y evaluación de la puerta G4.
