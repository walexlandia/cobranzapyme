# Estado de la Fase 1

> Actualizado: 14 de octubre de 2026

## Alcance técnico

| Entregable | Estado | Evidencia |
|---|---|---|
| Estructura `api`, `worker`, `web`, `db`, `minio` | Implementado | `compose.yaml` |
| PostgreSQL 16 y modelo inicial | Implementado | `backend/app/models.py` y migración `0001` |
| Alembic | Implementado, ejecución integral pendiente | Configuración y migración inicial creadas |
| Tests contra PostgreSQL | Parcial | Esquema e invariantes probados en PostgreSQL local; suite API pendiente de imagen Python |
| Datos demo | Implementado | Seed local con 2 pymes y 60 facturas; dataset ampliado con 3 pymes y 120 facturas en `data/demo/imports` |
| Autenticación y roles | Implementado, ejecución pendiente | JWT, bcrypt y roles admin/operator/client |
| Importación CSV/XLSX | Implementado y probado offline | Facturas y contactos; mapeo, RUT, fechas, montos, roles y duplicados |
| Aislamiento multiempresa | Implementado en endpoints y tests | Suite preparada; ejecución API pendiente |
| Auditoría inmutable | Implementado y probado en PostgreSQL | Trigger rechaza `UPDATE` y `DELETE` |
| Consola web de operación | Implementada y compilada | Login, selector y alta de clientes, cartera, cambio de estado e importación con vista previa |

## Validaciones ejecutadas

- Compilación sintáctica de aplicación y tests Python.
- Parsing de CSV con separador `;` y montos en formato chileno.
- Parsing de XLSX.
- Parsing de contactos y normalización de roles.
- Validación y normalización de RUT.
- Compilación de las 15 tablas para dialecto PostgreSQL.
- Creación real del esquema en un PostgreSQL 16 local y aislado de la red.
- Rechazo real de modificación y borrado de eventos.
- Rechazo real de una factura duplicada por pyme, tipo y folio.
- Build de producción del frontend sin acceso de red.
- Validación visual de la consola web en un contenedor local, sin errores de navegador.
- Validación de los CSV ampliados con el importador real: 120 facturas y 15 contactos aceptados; 6 errores esperados en el archivo negativo.

## Restricción actual del entorno

El equipo tiene bloqueo de firewall y no dispone localmente de una imagen Python ni de la caché completa de `psycopg`, Alembic y pytest. Por eso no se han ejecutado todavía la API en contenedor ni los tests HTTP/ORM, aunque el código, la migración y la suite están preparados.

No se usó SQLite ni se sustituyó PostgreSQL por otra base.

## Trabajo de validación preparado

- Guion de entrevistas a pymes.
- Guion para cuentas por pagar.
- Diccionario y plantilla CSV del análisis retrospectivo.
- Checklist para seleccionar pymes piloto.

## Requiere insumos del equipo fundador

- Responsables de producto/operación, tecnología, comercial y legal.
- Lista inicial de pymes candidatas.
- Datos históricos anonimizados de al menos una pyme.
- Criterio final para continuar, acotar o cambiar la hipótesis documental.
- Revisión legal antes de contactar pagadores reales.

