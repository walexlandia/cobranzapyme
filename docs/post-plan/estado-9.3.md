# Bloque post-plan 9.3 — panel operativo administrativo

Fecha de corte: 2026-10-21.

Este bloque no crea una novena fase del plan original. Expone en la interfaz administrativa el diagnóstico local construido en 9.2 y mantiene bloqueadas las integraciones e infraestructura externas.

## Alcance completado

| Tarea | Estado | Evidencia |
|---|---|---|
| Vista administrativa | Completo | Navegación `13 Salud`, disponible únicamente para rol `admin` |
| Estado y alertas | Completo | Estado global, alertas priorizadas y valores frente a umbrales configurados |
| Worker y carga | Completo | Latido, fallos, último ciclo, cola y bandejas agregadas |
| Telemetría API | Completo | Solicitudes por familia HTTP, latencias, concurrencia y uptime |
| Actualización segura | Completo | Actualización manual y automática cada 30 segundos; solo lectura |
| Privacidad | Completo | Sin clientes, usuarios, RUT, folios, correos, mensajes ni documentos |
| Adaptación visual | Completo | Panel de dos columnas en escritorio y una columna en pantallas angostas |
| Datos demo válidos | Completo | Correos `example.com` y migración idempotente de cuentas `.local` heredadas |
| Regresión web reproducible | Completo | El verificador detecta el directorio de trabajo real de la imagen y monta allí el código actual con caché limpia |

## Validación ejecutada

- Navegación y panel comprobados en un navegador real contra API, PostgreSQL 16 y worker locales.
- El administrador visualizó estado saludable, cero alertas, worker disponible y telemetría agregada.
- El botón `Actualizar ahora` aumentó el contador de solicitudes de 40 a 41.
- Un usuario cliente autenticado no recibió la opción `Salud`.
- 32 comprobaciones offline aprobadas, incluido el control estructural del plan de mejora posterior.
- 71 pruebas HTTP/ORM aprobadas sobre PostgreSQL 16.
- Build de producción Next.js aprobado sin descargar dependencias.

## Límites deliberados

- La vista es de solo lectura: no reinicia servicios, no descarta alertas y no altera registros.
- La actualización automática ocurre mientras la vista está montada y se detiene al abandonarla.
- La telemetría HTTP permanece en memoria por proceso; el latido del worker se conserva en PostgreSQL.
- No se agregó monitoreo externo, publicación, mensajería ni infraestructura por el bloqueo de red y las autorizaciones pendientes.

## Criterio de cierre local

El acceso administrativo debe mostrar el diagnóstico 9.2, la actualización manual debe recuperar una nueva instantánea, el rol cliente no debe ver la navegación ni acceder al endpoint, y la regresión local debe aprobar sin depender de servicios externos.
