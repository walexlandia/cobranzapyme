# Contexto de desarrollo — Recupera

Lee antes de modificar el producto:

- `vision-producto.md`
- `backlog.md`
- `plan-trabajo-fases.md`

## Reglas técnicas obligatorias

- PostgreSQL en Docker siempre, incluso en tests. Nunca SQLite.
- Todo cambio de esquema requiere una migración Alembic.
- Todo el sistema debe levantarse con `docker compose`.
- Credenciales solamente mediante variables de entorno o secretos.
- `Pagador` y `FichaPagador` son globales por RUT. Facturas, montos, mensajes, contactos personales, pagos y conversaciones siempre pertenecen a una pyme y deben filtrarse por `client_id`.
- Todo cambio de estado, mensaje, documento, clasificación y decisión humana genera un evento inmutable.
- El modo manual y el automático dejan el mismo rastro de auditoría e identifican el modo.
- Cierra una historia vertical completa —backend, interfaz, migración y tests— antes de avanzar a la siguiente.

## Reglas de seguridad del agente

- No negocia fuera de los límites del contrato.
- No amenaza ni usa lenguaje coercitivo.
- No resuelve disputas comerciales: las escala.
- No promete nada en nombre de la pyme sin autorización.
- No ingresa a portales de proveedores con credenciales sin autorización explícita.
- Si faltan datos o la confianza es baja, deriva el caso a una persona.

## Tests críticos

- Aislamiento entre clientes, incluida la separación entre ficha global y datos privados.
- Validación de RUT e importación sin duplicados.
- Inmutabilidad de eventos.
- Cálculo de etapa y checklist.
- Horarios, frecuencia e idempotencia del worker.
- Atribución del resultado y comisión.

