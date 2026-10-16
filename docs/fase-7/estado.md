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

## Validación local

- Compilación Python aprobada.
- Contrato OpenAPI del portal y sus tres rutas aprobado.
- 23 comprobaciones offline aprobadas, incluido el cálculo funcional del resumen con pago parcial.
- Build de producción Next.js aprobado con la imagen local `recupera-web:phase7`.
- Pruebas HTTP/PostgreSQL agregadas en `backend/tests/test_client_portal.py` y `backend/tests/test_client_documents.py`; su ejecución sigue pendiente porque el entorno local no contiene `pytest` ni la imagen backend con dependencias.

## Próximo incremento 7.3

1. Panel de métricas operativas y económicas del piloto.
2. Tendencias de pagabilidad, pagos, causas de atraso y tiempo humano.
3. Registro visible de decisiones e incidencias del piloto.
4. Recorrido demostrable de punta a punta sin acceso directo a la base de datos.
