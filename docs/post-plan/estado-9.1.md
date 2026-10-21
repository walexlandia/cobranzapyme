# Bloque post-plan 9.1 — QA y endurecimiento local

> Este bloque no modifica el plan original de ocho fases. Reduce riesgo técnico mientras las actividades externas continúan bloqueadas.

| Entregable | Estado | Evidencia |
|---|---|---|
| Configuración segura | Completo localmente | `pilot/production` rechaza secretos de ejemplo, claves criptográficas repetidas y CORS localhost |
| Cabeceras defensivas | Completo localmente | Request ID, `nosniff`, `DENY`, `no-referrer`, Permissions Policy, no-store y HSTS condicionado |
| Correlación | Completo | Toda respuesta obtiene UUID; la bitácora autenticada reutiliza el mismo identificador |
| Compose de piloto | Completo como configuración | Sin puertos directos de DB/MinIO, sin bind mounts, sin seed y sin reload |
| Lockfile web | Completo | Dependencias directas fijadas a las versiones de la imagen local y `package-lock.json` v3 |
| Inventario | Completo | Python directo, árbol npm, imágenes, hashes de fuentes y riesgos no resueltos |
| Regresión local | Completo | Un comando orquesta compilación, readiness, inventario, 29 checks, Compose, build y restauración opcionales |
| Modelo de amenazas | Completo como revisión local | Activos, límites, controles y riesgos residuales documentados |

## Límites

- La suite HTTP/PostgreSQL completa permanece preparada pero no ejecutada por falta del runtime backend local.
- La caché no contiene todos los tarballs del árbol npm; el build se valida contra una imagen local cuyas dependencias directas se comparan con el lockfile.
- Los rangos Python todavía no constituyen un lock reproducible con hashes.
- Las imágenes `latest` o sin digest deben fijarse y escanearse al habilitar acceso externo.
- No se realizaron pruebas dinámicas contra un dominio público ni proveedores reales.
