# Runbook local de demo y piloto

## 1. Separación de entornos

Use archivos de secretos distintos basados en `.env.demo.example` y `.env.pilot.example`. Nunca reutilice base, volúmenes, JWT ni clave documental entre entornos. `COMPOSE_PROJECT_NAME` separa redes y volúmenes.

```powershell
python scripts\generate-local-tls.py
docker compose --env-file .env.demo -f compose.yaml -f compose.secure.yaml --profile backup up -d
```

El acceso local queda en `https://localhost:8443`. El certificado generado es deliberadamente autofirmado y solo sirve para ensayo local. En un despliegue real debe reemplazarse por uno emitido para el dominio del entorno.

## 2. Carga y capacitación

1. Crear la pyme y usuario con alcance de cliente.
2. Importar primero una muestra y corregir los errores antes de cargar el lote completo.
3. Revisar ficha de pagador, contrato y porcentajes de comisión.
4. Aprobar explícitamente plantillas y autorización de contacto.
5. Enseñar cartera, checklist, pausa, excepciones, pagos y reporte de comisión.
6. Ejecutar un caso controlado de punta a punta sin envío externo.
7. Guardar la aprobación humana y la evidencia del caso en el historial.

La sección **Contrato** de la consola muestra la puerta G3. El mandato se registra allí como evidencia cifrada y puede revocarse sin alterar el registro original. La puerta solo aparece abierta cuando el contrato activo, los canales autorizados, las plantillas, los contactos y el cifrado documental son coherentes.

Los archivos ficticios para el ensayo están en `data/demo/imports`. No deben mezclarse con el entorno piloto real.

## 3. Pausa de comunicaciones

Antes de cualquier incidente, el operador debe poder:

1. Pausar el cliente completo desde los controles de workflow.
2. Verificar que no se generan nuevas acciones listas.
3. Mantener las comunicaciones externas deshabilitadas hasta una revisión humana.
4. Registrar causa, responsable y decisión de reanudación.

Ante privacidad, destinatario incorrecto, duplicidad o tono, la pausa es inmediata. La reanudación requiere revisión del caso y evento auditable.

## 4. Respaldo y restauración

El perfil `backup` ejecuta un `pg_dump` custom al iniciar y luego cada 24 horas, con retención configurable. Para una copia manual:

```powershell
$backup = .\scripts\backup-postgres.ps1
.\scripts\verify-backup-restore.ps1 -BackupPath $backup
```

La verificación crea una base cuyo nombre comienza por `recupera_restore_verify_`, restaura, valida el esquema y elimina solo esa base temporal. No reemplaza la base activa.

Para probar el procedimiento sin exponer puertos ni tocar la base de desarrollo, puede levantarse un proyecto Compose distinto usando `compose.verify.yaml` y un `COMPOSE_PROJECT_NAME` exclusivo.

## 5. Documentos y claves

- Definir `DOCUMENT_ENCRYPTION_KEY` con un secreto distinto por entorno.
- Ejecutar `python -m app.encrypt_documents` después de migrar para cifrar documentos legados.
- Respaldar la clave fuera del servidor; perderla vuelve irrecuperables los comprobantes.
- Rotar la clave requiere un procedimiento explícito de descifrado/re-cifrado, no una edición directa en base.
- El cifrado del volumen y de los respaldos debe configurarse en la infraestructura real.

## 6. Revisión diaria

- Salud API y espacio de disco.
- Último respaldo y prueba periódica de restauración.
- Excepciones abiertas y minutos humanos.
- Accesos inusuales por usuario, ruta o estado HTTP.
- Mensajes duplicados, pagos duplicados y propuestas pendientes.
- Documentos `legacy_plaintext`; el conteo esperado es cero.

## 7. Cierre o rollback

Pausar comunicaciones, conservar eventos y accesos, exportar reportes, tomar respaldo y documentar la causa. Nunca borrar eventos, atribuciones ni bitácoras para “limpiar” un piloto.
