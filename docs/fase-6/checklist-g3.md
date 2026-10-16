# Puerta G3 — Preparación para producción

| Criterio | Estado | Evidencia / bloqueo |
|---|---|---|
| Tests críticos contra PostgreSQL | Aprobado a nivel esquema/invariantes | PostgreSQL 16 recreado y checks SQL aprobados; suite HTTP completa preparada pero no ejecutable sin dependencias backend |
| Restauración de respaldo | Aprobado localmente | Dump final custom restaurado en base aislada; 34 tablas verificadas |
| Aislamiento multiempresa | Aprobado localmente | `client_id`, autorización y pruebas preparadas; invariantes estructurales aprobadas |
| Idempotencia sin pagos/mensajes duplicados | Aprobado localmente | Claves únicas y conciliación única en PostgreSQL |
| Contrato, plantillas y contacto aprobados | Control implementado; requiere pyme real | La puerta G3 valida contrato, canales, plantillas, contactos y evidencia cifrada; no existe contraparte real autorizante |
| Pausa total de comunicaciones | Aprobado localmente | Control por cliente/factura y procedimiento documentado |
| HTTPS público y secretos gestionados | Requiere infraestructura | TLS local preparado; falta dominio, CA y gestor de secretos externos |
| Primer caso real V-09 | Bloqueado externamente | Requiere pyme, contrato, datos y autorización reales |

## Decisión

La implementación local de Fase 6 está preparada. La puerta G3 no puede declararse abierta para producción hasta completar los cuatro controles externos: infraestructura pública separada, secretos administrados, aprobaciones de la pyme y V-09 con datos reales.
