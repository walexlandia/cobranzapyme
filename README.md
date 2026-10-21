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

El incremento 7.1 de la fase 7 agrega:

- portal de cliente de solo lectura con fecha de corte configurable;
- resumen de facturas pagables, en riesgo, pagadas, pendientes de la pyme y en disputa;
- saldos basados exclusivamente en pagos verificados;
- detalle de checklist y requisitos documentales pendientes por factura;
- reporte semanal visible y exportable a CSV;
- pagos y comprobantes sintéticos cifrados en el seed demostrativo.

El incremento 7.2 agrega:

- carga de documentos por el usuario cliente para requisitos pendientes;
- cifrado AES-256-GCM, hash SHA-256 y límite de 10 MB antes de almacenar;
- deduplicación por cliente, requisito y contenido;
- bandeja de revisión para operadores con aceptación o rechazo motivado;
- actualización del checklist solo después de aceptación humana;
- eventos auditables y una evidencia sintética pendiente por pyme en el seed.

El incremento 7.3 agrega:

- panel operativo con facturas gestionadas, recuperación, minutos humanos, costos, comisiones y margen;
- DSO y pago oportuno comparados con la línea base de cada pyme;
- tendencias semanales basadas únicamente en pagos verificados;
- desglose automático/manual para mensajes, clasificaciones y conciliaciones;
- causas de atraso y tiempo medio de resolución documental;
- exportación CSV y vista cliente limitada a resultados, sin economía interna;
- supuestos económicos editables y datos de prueba sintéticos con resultados verificables.

El incremento 7.4 cierra el alcance técnico local de la fase 7 con:

- bitácora por cliente para decisiones, incidencias, trabajo manual, cambios de reglas y aprendizajes;
- resolución trazable de incidentes y minutos humanos incorporados a las métricas;
- respuesta de la pyme a excepciones escaladas, aislada por cliente y sin acciones automáticas irreversibles;
- fecha controlada y recorrido demostrable de seis etapas sin manipular directamente la base de datos;
- datos sintéticos idempotentes para recorrer la operación;
- runbook, guion de demostración y checklist de preparación G4, manteniendo la decisión final pendiente de evidencia real.

El incremento 8.1 agrega el cierre medible del piloto:

- informe final V-10 reproducible en JSON y Markdown, con parámetros y huella SHA-256;
- dataset CSV agregado y anonimizado mediante alias HMAC-SHA256 y supresión de grupos pequeños;
- comparación de DSO, pago oportuno, costo humano y margen por pyme contra su línea base;
- análisis por pagador, causa y tramo de monto sin exponer nombres, RUT, folios ni IDs internos;
- clasificación explícita de hipótesis confirmadas, rechazadas e inciertas;
- matriz G4 para escalar, iterar, pivotar o detener, bloqueada como pendiente para evidencia sintética.

El incremento 8.2 formaliza la decisión:

- escenarios conservador, observado y eficiente para revisar unit economics;
- snapshots idempotentes e inmutables del informe anonimizado;
- separación entre quien prepara el cierre y el administrador que decide;
- bloqueo técnico de decisiones basadas en datos sintéticos o evidencia insuficiente;
- eventos auditables por pyme y justificación obligatoria de la decisión;
- backlog posterior priorizado automáticamente según las hipótesis y la concentración observada.

El incremento 8.3 prepara la entrega verificable:

- paquete ZIP determinista generado exclusivamente desde un snapshot inmutable;
- resumen ejecutivo y anexos separados de informe, dataset, unit economics, backlog y evidencia;
- manifiesto con huellas SHA-256 y tamaños para verificar cada archivo;
- marca visible de borrador cuando la evidencia es sintética;
- exclusión de datos identificatorios, UUID internos y texto libre de decisiones.

El incremento 8.4 cierra la preparación técnica local:

- contrato de release 0.8.4 y checklist estricto de go-live;
- verificador de artefactos, migraciones, esquemas y secretos sin exponer valores;
- ensayo desechable de respaldo y restauración con marcador de datos;
- procedimiento de rollback, handoff RACI y registro de bloqueos externos;
- regla explícita de NO-GO mientras falten infraestructura, autorizaciones, pymes y piloto real.

El bloque post-plan 9.1 agrega QA y endurecimiento sin declarar una novena fase del plan:

- configuración fail-fast para piloto/producción y CORS explícito;
- request ID universal y cabeceras HTTP defensivas;
- Compose de piloto sin seed, reload, bind mounts ni puertos directos de datos;
- lockfile web e inventario determinista de dependencias y contenedores;
- comando único de regresión local y modelo de amenazas con riesgos residuales.

El bloque post-plan 9.2 agrega observabilidad y resiliencia local:

- telemetría HTTP acotada y sin datos personales;
- diagnóstico agregado exclusivo para administradores;
- reglas deterministas de alerta con umbrales versionados;
- latido persistente y backoff exponencial del worker;
- ensayo offline de degradación/recuperación y runbook de incidentes.

El bloque post-plan 9.3 hace visible ese diagnóstico en el portal:

- panel de salud exclusivo para administradores, con alertas, cola, worker y telemetría agregada;
- actualización manual y automática cada 30 segundos, sin ejecutar acciones operativas;
- diseño adaptable y protección explícita contra exposición de datos identificatorios;
- cuentas demo con correos válidos y migración idempotente desde los valores `.local` heredados.

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
python scripts\release_readiness.py
python scripts\generate_dependency_inventory.py --check
python scripts\simulate_worker_resilience.py
python scripts\generate_phase5_evaluation_fixture.py
docker build --network=none -f web/Dockerfile.offline -t recupera-web:offline web
```

La regresión ampliada puede ejecutarse con `scripts\verify-local-release.ps1`; acepta una imagen web local y un ensayo opcional de restauración.

`Dockerfile.offline` reutiliza una imagen Next.js que ya existe en este equipo. Es un recurso local de desarrollo; el artefacto portable sigue siendo `web/Dockerfile`.

Las comprobaciones offline también validan que la cadena Alembic tenga una sola cabeza, que sus tablas y columnas coincidan con los modelos, que estén presentes las configuraciones operativas de Fase 6 y que los contratos del portal y las métricas de Fase 7 permanezcan completos.

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
- `docs/fase-7/estado.md`: cierre local de vista cliente, documentos, métricas y operación demostrable del piloto asistido.
- `docs/fase-8/estado.md`: informe final, decisión formal G4 y paquete verificable de postulación.
- `docs/post-plan/`: endurecimiento, observabilidad, runbook y panel administrativo posteriores al plan original.
- `examples/`: archivos de facturas y contactos para probar las importaciones.

