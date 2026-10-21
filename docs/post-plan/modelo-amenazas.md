# Modelo de amenazas local

## Alcance y activos

Este modelo cubre la API, portal, worker, PostgreSQL, almacenamiento documental, gateway y artefactos de cierre. Los activos prioritarios son datos de pymes y pagadores, documentos cifrados, credenciales, reglas contractuales, pagos, bitácoras, respaldos y decisiones G4.

## Límites de confianza

1. Navegador del operador o cliente → gateway HTTPS.
2. Gateway → web y API en red privada.
3. API/worker → PostgreSQL y MinIO.
4. Integraciones externas → webhooks y canales todavía bloqueados.
5. Operador humano → acciones supervisadas y excepciones.
6. Release/backup → almacenamiento y custodia fuera del runtime.

## Amenazas y controles

| Amenaza | Impacto | Controles actuales | Riesgo residual / salida |
|---|---|---|---|
| Acceso cruzado entre pymes | Crítico | Roles, `client_id`, consultas acotadas, pruebas de aislamiento y auditoría | Ejecutar suite integral contra PostgreSQL antes del piloto |
| Robo o reutilización de secretos | Crítico | Validación de placeholders, claves separadas y `.env` fuera de Git | Gestor externo, rotación y custodia de recuperación |
| Exposición de documentos | Crítico | AES-256-GCM, hash, control de acceso y bitácora | Cifrado de volumen/backup y prueba con infraestructura real |
| Mensajes no autorizados o duplicados | Alto | G3, opt-out, horarios, idempotencia, pausa y supervisión | Probar proveedores y contactos controlados |
| Manipulación de eventos o cierres | Alto | Triggers inmutables, hashes y separación de funciones | Monitoreo externo y retención protegida |
| Conciliación o comisión incorrecta | Alto | Confirmación humana, claves únicas y atribución inmutable | Muestreo financiero real y doble revisión inicial |
| Inyección o contenido malicioso | Alto | Validaciones, plantillas, clasificación supervisada y no ejecución de adjuntos | Antivirus/sandbox externo antes de abrir archivos reales |
| Clickjacking, MIME sniffing o cache sensible | Medio | `DENY`, `nosniff`, `no-referrer`, Permissions Policy y `no-store` para API | CSP del portal y pruebas dinámicas en dominio real |
| Falta de trazabilidad entre capas | Medio | `X-Request-ID` para toda respuesta y reutilización en accesos autenticados | Centralizar logs y alertas sin almacenar tokens/cuerpos |
| Dependencia vulnerable o mutable | Alto | Lockfile npm, inventario determinista y fuentes con hash | Lock Python, imágenes por digest y escaneo actualizado |
| Respaldo inutilizable | Crítico | Dump custom, restauración desechable y marcador de datos | Custodia cifrada, retención y restauración periódica externa |
| Denegación de servicio | Medio/alto | Límites de documentos y health checks | Rate limiting, límites de proxy y capacidad medidos en infraestructura |

## Reglas de aceptación

- Un riesgo crítico sin control probado impide GO.
- Los logs nunca conservan tokens, cuerpos ni IP sin seudonimizar.
- HSTS solo se activa en `pilot/production`, detrás del gateway HTTPS.
- Una cabecera enviada por el cliente solo se reutiliza como request ID si es un UUID válido.
- Toda dependencia mutable permanece como riesgo explícito hasta fijar versión/digest y escanearla.
- Este análisis se revisa después de cada incidente, cambio de integración o nueva categoría de datos.
