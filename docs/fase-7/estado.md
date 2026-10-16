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

## Validación local

- Compilación Python aprobada.
- Contrato OpenAPI del portal y sus tres rutas aprobado.
- 23 comprobaciones offline aprobadas, incluido el cálculo funcional del resumen con pago parcial.
- Build de producción Next.js aprobado con la imagen local `recupera-web:phase7`.
- Pruebas HTTP/PostgreSQL agregadas en `backend/tests/test_client_portal.py`; su ejecución sigue pendiente porque el entorno local no contiene `pytest` ni la imagen backend con dependencias.

## Próximo incremento 7.2

1. Carga de documentos solicitados desde la vista cliente.
2. Cifrado, hash, asociación al requisito y evento inmutable.
3. Revisión del operador antes de aceptar la evidencia y cerrar el requisito.
4. Prevención de duplicados y pruebas de aislamiento por pyme.
