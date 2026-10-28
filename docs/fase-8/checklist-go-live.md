# Checklist definitivo de go-live

> Estado al 21 de octubre de 2026: preparación técnica local completa; salida real bloqueada. Ningún dato sintético constituye aprobación.

## Regla de decisión

El responsable de release solo puede declarar **GO** cuando todos los controles técnicos estén en `PASS`, todas las puertas externas tengan evidencia adjunta y no exista un incidente crítico abierto. Un `SKIP`, `BLOCKED` o evidencia vencida equivale a **NO-GO**.

## Controles técnicos

| ID | Control | Evidencia requerida | Estado local |
|---|---|---|---|
| GL-01 | Commit y versión identificados | Commit de release y `release/phase-8.4.json` | PASS |
| GL-02 | Migraciones lineales | Una sola cabeza Alembic, actualmente `0019` | PASS |
| GL-03 | Compilación y checks offline | `compileall`, checks vigentes y build web | PASS |
| GL-04 | PostgreSQL recuperable | Respaldo portable, restauración aislada, tablas y marcador verificados | PASS |
| GL-05 | Aislamiento y auditoría | Pruebas preparadas e invariantes PostgreSQL | PASS local |
| GL-06 | Cifrado y anonimización | Claves independientes, documentos AES-GCM y reportes anonimizados | PASS local |
| GL-07 | Pausa operativa | Procedimiento probado antes de cualquier contacto | PASS local |
| GL-08 | Observabilidad mínima | `/health/live`, `/health/ready`, accesos y bitácora | PASS local |
| GL-09 | Rollback ensayable | Versión previa disponible y respaldo previo verificado | PASS como procedimiento |
| GL-10 | Configuración real | `release_readiness.py --env-file ... --strict` sin fallos | PENDIENTE |

## Puertas externas obligatorias

| ID | Evidencia de salida | Estado |
|---|---|---|
| EXT-01 | Infraestructura pública separada, dominio, TLS emitido, volúmenes cifrados y gestor de secretos | BLOQUEADO |
| EXT-02 | Dictamen legal, contrato y mandato de contacto firmados | BLOQUEADO |
| EXT-03 | Dos o tres pymes, datos históricos, responsables y línea base aceptada | BLOQUEADO |
| EXT-04 | Remitente de correo y WhatsApp Business probados con contactos controlados | BLOQUEADO |
| EXT-05 | Operación real de 6–8 semanas, revisión de incidentes y decisión G4 independiente | BLOQUEADO |

## Secuencia de autorización

1. Operaciones reúne evidencia y ejecuta el verificador estricto sin copiar secretos a tickets o documentos.
2. Tecnología confirma versión, migración, respaldo restaurable, salud y posibilidad de pausa.
3. Legal confirma alcance, mandato, tratamiento de datos y plantillas.
4. El representante de cada pyme aprueba contrato, contactos, canales y datos iniciales.
5. El responsable de release registra GO/NO-GO, fecha, versión y responsables en la bitácora.
6. Ante NO-GO, se mantiene toda entrega externa deshabilitada y se asigna dueño y fecha a cada bloqueo.

## Comandos de evidencia local

```powershell
python scripts\release_readiness.py
.\scripts\rehearse-release.ps1
python scripts\release_readiness.py --env-file .env.pilot --strict
```

El último comando debe ejecutarse únicamente cuando exista un entorno piloto real. El verificador informa nombres de variables problemáticas, nunca sus valores.
