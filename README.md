# Recupera

Servicio B2B operado por IA para asegurar que las facturas de pymes sean pagables desde su emisión y acompañarlas hasta su pago y conciliación.

## Inicio rápido

1. Copiar `.env.example` a `.env` y reemplazar los secretos.
2. Ejecutar `docker compose up --build`.
3. Abrir:
   - Aplicación: http://localhost:3000
   - API: http://localhost:8000/docs
   - MinIO: http://localhost:9001

La API aplica migraciones y carga datos demo idempotentes al iniciar. Las credenciales iniciales se configuran con `DEMO_ADMIN_EMAIL` y `DEMO_ADMIN_PASSWORD`.

La aplicación web incluye la consola de la fase 1:

- autenticación de operadores y clientes;
- selección y creación de pymes;
- resumen y listado de la cartera;
- cambio manual de estado con auditoría;
- importación de facturas y contactos con validación previa por fila.

El primer incremento de la fase 2 agrega:

- contratos versionados por pyme con horario, frecuencia, canales, tono y comisión;
- cálculo de etapa por factura;
- cola de trabajos idempotente ligada a la versión del contrato;
- ejecución automática por worker y ciclo manual desde la consola;
- pausa automática para facturas pagadas, anuladas, reclamadas o en disputa.
- pausa y reanudación manual por factura o pagador;
- reanudación automática al vencer una fecha programada;
- agrupación de facturas por pagador y destinatario para evitar contactos duplicados;
- vista de los trabajos recientes y su trazabilidad.
- historial cronológico auditable por factura;
- simulación del motor con una fecha controlada, sin modificar estados ni crear trabajos;
- pausas programadas desde la consola y control masivo por pagador.

La fase 3 agrega:

- ficha operativa global y versionada por pagador;
- checklist por factura con responsables y evidencia;
- estados pagable, incompleta, en riesgo y reclamada en la cartera;
- importación asistida del estado SII desde CSV/XLSX;
- registro de carga en portal y confirmación estructurada de aprobación/programación de pago;
- causas de atraso y línea base por pyme;
- análisis retrospectivo y decisión G1 documentados con datos ficticios.

Los incrementos locales 4.1 y 4.2 de la fase 4 agregan:

- plantillas de comunicación versionadas por cliente y canal;
- bandeja de salida simulada, integrada con los trabajos del motor;
- mensajes agrupados con adjuntos, requisitos pendientes y datos de transferencia;
- WhatsApp asistido sin envío automático;
- recepción simulada e idempotente de email y WhatsApp, correlacionada por hilo, contacto y factura;
- adjuntos entrantes ficticios asociados al mensaje y a la factura;
- registro manual de respuestas recibidas por teléfono, correo personal u otros medios;
- estados locales de entrega, lectura y falla con eventos auditables;
- opt-out por canal y bloqueo de borradores pendientes;
- reglas de seguridad con plantilla de respaldo;
- costos simulados de LLM y mensajería asignados por factura.

Los incrementos 5.1 y 5.2 de la fase 5 agregan:

- clasificación local y determinista en las diez categorías operativas del backlog;
- extracción de fechas, montos, números de OC/HES y comprobantes adjuntos;
- confianza, evidencia de reglas y versión del clasificador en cada decisión;
- bandeja priorizada de excepciones con mensaje, factura, checklist, ficha y eventos;
- revisión humana que crea una nueva clasificación inmutable;
- registro de minutos humanos y resolución, sin ejecutar acciones automáticas;
- correcciones explícitas de checklist y etapa desde la revisión humana;
- set de evaluación versionado, inmutable y anonimizado;
- precisión y política supervisada/automática por categoría, con umbral mínimo de 90% y 20 muestras;
- escalamiento local y auditable a la pyme, sin entrega externa;
- propuestas de mejora de la ficha global del pagador que solo se aplican tras aprobación humana.

El incremento 5.3 completa el alcance técnico local de la fase 5 con:

- respuestas asistidas preparadas desde una excepción y guardadas en la bandeja de salida;
- revisión humana obligatoria, opt-out, controles de seguridad e idempotencia antes de cualquier entrega;
- reporte G2 de precisión, recall, errores y minutos humanos, visible y exportable a CSV;
- un set sintético balanceado de 200 casos para regresión local;
- mejoras de reglas detectadas por ese set, manteniendo los datos sintéticos fuera de la puerta de automatización.

El incremento 6.1 de la fase 6 agrega:

- registro manual de pagos con comprobante almacenado en PostgreSQL y hash SHA-256;
- importación local e idempotente de cartolas CSV/XLSX;
- propuestas explicables por RUT, monto y fecha, incluyendo pagos agrupados;
- confirmación o rechazo humano con protección contra doble conteo;
- actualización de la factura solo cuando los pagos verificados cubren su monto;
- consola de pagos y cartola ficticia lista para pruebas.
- atribución contractual inmutable y reporte mensual de comisiones en CSV;
- cifrado AES-GCM de comprobantes y bitácora inmutable de accesos;
- respaldo diario con restauración verificable y gateway TLS local.
- puerta G3 con autorización operativa versionada, evidencia cifrada y revocación auditable.

## Servicios

- `db`: PostgreSQL 16.
- `api`: FastAPI y Alembic.
- `worker`: proceso separado para trabajos programados.
- `web`: Next.js.
- `minio`: almacenamiento S3 compatible para documentos y evidencia.

## Tests

Los tests nunca usan SQLite:

```powershell
docker compose --profile test run --rm test
```

El servicio de tests utiliza una instancia PostgreSQL separada y desechable.

## Trabajo sin acceso a internet

El repositorio incluye un camino explícito para equipos con firewall restrictivo. No sustituye la verificación integral del backend, pero permite avanzar sin descargar paquetes:

```powershell
python scripts\offline_checks.py
python scripts\generate_phase5_evaluation_fixture.py
docker build --network=none -f web/Dockerfile.offline -t recupera-web:offline web
```

`Dockerfile.offline` reutiliza una imagen Next.js que ya existe en este equipo. Es un recurso local de desarrollo; el artefacto portable sigue siendo `web/Dockerfile`.

Las comprobaciones offline también validan que la cadena Alembic tenga una sola cabeza, que sus tablas y columnas coincidan con los modelos y que estén presentes las configuraciones de TLS, respaldo y restauración de Fase 6.

La preparación segura de Fase 6, incluyendo entornos separados, TLS local y respaldo/restauración, está documentada en `docs/fase-6/runbook-piloto.md`.

El esquema PostgreSQL puede validarse contra la imagen local `postgres:16-alpine` usando:

```powershell
python scripts\render_schema_sql.py
```

El script emite DDL PostgreSQL a salida estándar. `scripts/postgres_invariant_checks.sql` comprueba inmutabilidad de eventos y rechazo de facturas duplicadas.

## Datos de demostración ampliados

Los CSV listos para importar están en `data/demo/imports`. Incluyen tres pymes ficticias, 120 facturas, 15 contactos y un archivo de casos inválidos para comprobar los mensajes de error. El libro de control y análisis está en `outputs/recupera-datos-prueba.xlsx`.



## Documentación

- `vision-producto.md`: visión y tesis de producto.
- `backlog.md`: historias y criterios del MVP piloto.
- `plan-trabajo-fases.md`: ejecución por fases y puertas de decisión.
- `docs/validacion/`: instrumentos para entrevistas y análisis retrospectivo.
- `docs/fase-2/estado.md`: alcance y evidencia del motor operativo.
- `docs/fase-3/`: estado, checklist de cierre, paquete de validación externa, análisis retrospectivo, decisión G1 y restricciones operativas.
- `docs/fase-4/estado.md`: avance y límites de la operación multicanal simulada.
- `docs/fase-5/estado.md`: clasificación supervisada, evaluación y puerta de automatización.
- `docs/fase-6/estado.md`: pagos manuales, cartolas y conciliación supervisada.
- `examples/`: archivos de facturas y contactos para probar las importaciones.

