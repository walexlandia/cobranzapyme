# Release 0.8.4 y procedimiento de rollback

## Identidad de release

- Versión de preparación: `0.8.4`.
- Contrato legible por máquina: `release/phase-8.4.json`.
- Cabeza de base de datos: `0016`.
- Esquema de informe: `fase-8.2-v1`.
- Esquema del paquete: `fase-8.3-v1`.

La versión identifica el cierre técnico local. No implica que las puertas externas estén aprobadas ni que exista una release pública desplegada.

## Preparación

1. Congelar nuevas funcionalidades y resolver únicamente defectos bloqueantes.
2. Registrar commit, imágenes inmutables y configuración, sin guardar secretos en Git.
3. Ejecutar compilación, checks offline, build web y pruebas PostgreSQL disponibles.
4. Generar un respaldo custom y restaurarlo en una base aislada.
5. Confirmar que la versión anterior de aplicación continúa disponible.
6. Pausar comunicaciones antes del cambio.

## Despliegue controlado

1. Desplegar primero base/migraciones con una copia reciente verificada.
2. Desplegar API y worker; comprobar `/health/live` y `/health/ready`.
3. Desplegar web y gateway; comprobar TLS y autenticación por rol.
4. Ejecutar un recorrido controlado sin entrega externa.
5. Habilitar una sola pyme y un canal, únicamente con las autorizaciones vigentes.
6. Observar duplicidad, errores, accesos, excepciones y cola antes de ampliar.

## Disparadores de rollback

- exposición o acceso cruzado de datos;
- mensajes o pagos duplicados;
- pérdida de auditoría, cifrado o aislamiento;
- migración incompleta o corrupción verificable;
- indisponibilidad sostenida sin mitigación segura;
- imposibilidad de pausar comunicaciones.

## Secuencia de rollback

1. Pausar todos los canales y workers; preservar logs, bitácora y hora del incidente.
2. Tomar un respaldo posterior al incidente para análisis, sin sustituir el respaldo previo.
3. Si el esquema sigue siendo compatible, reinstalar las imágenes inmutables anteriores sin revertir datos.
4. Si la versión anterior no puede leer el nuevo esquema, crear un entorno aislado y restaurar el respaldo previo verificado.
5. Nunca ejecutar un downgrade destructivo ni borrar eventos para acelerar la recuperación.
6. Verificar salud, conteos, aislamiento, accesos, pagos y marcador operativo antes de reabrir.
7. Registrar alcance, decisión, pérdida potencial de datos posteriores y aprobación humana.

La restauración no se ejecuta sobre la base activa. Primero se demuestra en una base o entorno paralelo; el cambio de tráfico se hace después de la validación.
