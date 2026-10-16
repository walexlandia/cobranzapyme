# Estado de la Fase 6

> Ejecución local: 16 de octubre de 2026  
> Restricción vigente: firewall sin gestiones bancarias, hosting, certificados públicos ni onboarding de una pyme real

## Incremento 6.1 — Pagos y conciliación supervisada

| Historia | Estado local | Evidencia |
|---|---|---|
| E8-02 Pago manual con evidencia | Completo | Monto, fecha, referencia, comprobante cifrado y SHA-256 |
| E8-03 Importación de cartola | Completo | Vista previa y carga CSV/XLSX idempotente por cliente e identificador externo |
| E8-04 Propuesta de coincidencias | Completo | Puntaje por RUT, monto y fecha; una factura, parcial o suma de hasta tres facturas |
| E8-05 Decisión humana | Completo | Confirmar crea pagos; rechazar no altera saldos; ambas decisiones se auditan |
| E9-01 Pago verificado | Completo | Solo comprobante manual o conciliación humana confirmada |

## Incremento 6.2 — Atribución, comisión y métricas

| Historia | Estado local | Evidencia |
|---|---|---|
| E9-02 Atribución contractual | Completo | Ledger inmutable por pago, contrato, regla preventiva/recuperación, evidencia y porcentaje |
| E9-03 Comisión mensual | Completo | API, consola y CSV detallado por factura y pago |
| Métricas operativas de apoyo | Completo | Montos, facturas gestionadas, puntualidad, minutos humanos, automatización y costos USD separados de comisión CLP |

La atribución se congela al verificar el pago. Un pago a tiempo exige gestión preventiva documentada; un pago vencido exige gestión de recuperación documentada. Sin contrato activo o evidencia elegible queda como `not_attributable` y comisión cero.

## Incremento 6.3 — Preparación local de piloto y seguridad

| Historia | Estado local | Evidencia |
|---|---|---|
| E0-05 Entornos demo/piloto | Preparado, no publicado | Configuración separada, gateway TLS y secretos distintos; falta infraestructura/dominio externo |
| E0-06 Respaldo diario/restauración | Completo localmente | Servicio diario, scripts operativos y restauración real en base desechable con 33 tablas |
| E12-02 Cifrado | Completo en aplicación local | AES-256-GCM para nuevos comprobantes, migrador idempotente de documentos legados y TLS local |
| E12-03 Registro de accesos | Completo | Middleware para toda ruta autenticada, `X-Request-ID`, origen seudonimizado, ledger inmutable y vista administrativa **08 Accesos** |
| Autorización y puerta G3 | Completo localmente | Ledger inmutable con evidencia cifrada, revocación append-only y verificador de contrato, canales, plantillas, contactos y documentos |
| V-09 Primera pyme | Preparación completa | Datos ficticios, carga y runbook listos; ejecución real bloqueada por falta de pyme/datos/autorización externa |

## Reglas de seguridad e integridad

- Ninguna propuesta se confirma automáticamente.
- Un movimiento bancario solo puede tener una conciliación confirmada.
- La combinación movimiento/factura y la clave de idempotencia del pago son únicas.
- Un pago debe ser positivo y no superar el saldo pendiente.
- Una propuesta obsoleta se rechaza si el saldo cambió.
- El ledger de atribución, los eventos y los accesos son inmutables en PostgreSQL.
- Los comprobantes se cifran con AES-GCM y una clave separada del JWT; no se persisten tokens ni cuerpos en el log de acceso.
- Los costos USD no se mezclan con comisiones CLP sin un tipo de cambio auditado.
- La cartola y las empresas demo son ficticias y no implican conexión bancaria.

## Validación ejecutada

- Compilación Python sin errores.
- 21 comprobaciones offline aprobadas, incluido OpenAPI, DDL PostgreSQL, cadena Alembic completa, paridad migraciones/modelos y activos operativos de seguridad.
- Esquema de 34 tablas recreado en PostgreSQL 16.
- Invariantes aprobadas: aislamiento estructural, inmutabilidad, monto positivo, conciliación única, doble conteo, atribución y acceso.
- Cifrado/descifrado AES-GCM probado localmente.
- Respaldo final en formato custom de PostgreSQL restaurado con éxito en una base aislada; se verificaron las 34 tablas del esquema actual.
- Los scripts entregados `backup-postgres.ps1` y `verify-backup-restore.ps1` se ejecutaron de punta a punta contra un proyecto Compose aislado; la restauración informó `PASS restore verified: 34 public tables`.
- Configuración segura de Docker Compose validada.
- Build de producción Next.js aprobado sin acceso de red.

## Pendientes que requieren gestión externa

1. Publicar demo y piloto en infraestructura separada, emitir certificado de una CA y configurar DNS.
2. Custodiar secretos en un gestor externo y confirmar cifrado de disco/volumen del proveedor.
3. Incorporar una pyme real, firmar condiciones, cargar datos reales y capacitar usuarios.
4. Ejecutar V-09 y comenzar la ventana real de 6–8 semanas.
5. Ejecutar la suite HTTP/ORM completa cuando exista una imagen backend con sus dependencias; hoy el firewall impide construirla.

Estos puntos no se declaran realizados con datos ficticios. El detalle operativo y la puerta G3 están en `runbook-piloto.md` y `checklist-g3.md`.
