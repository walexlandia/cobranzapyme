# Registro de pendientes externos

> Este registro evita confundir preparación local con evidencia real. El estado solo cambia cuando existe un documento o resultado verificable.

| ID | Dependencia | Dueño requerido | Evidencia de cierre | Estado actual | Bloquea |
|---|---|---|---|---|---|
| EXT-01 | Infraestructura pública y secretos | Infraestructura / seguridad | Dominio, TLS emitido, gestor de secretos, cifrado de volúmenes y restauración | Bloqueado | Go-live |
| EXT-02 | Marco legal y mandato | Legal + representante de pyme | Dictamen, contrato, tratamiento de datos y mandato firmados | Bloqueado | Contacto real |
| EXT-03 | Pymes y datos reales | Comercial + responsable del piloto | 2–3 pymes, responsables, históricos y línea base aceptada | Bloqueado | Piloto |
| EXT-04 | Correo y WhatsApp | Infraestructura + operaciones | Remitente autenticado, plantillas aprobadas y prueba controlada | Bloqueado | Multicanal real |
| EXT-05 | Pruebas backend integrales | Tecnología | Suite HTTP/ORM aprobada contra PostgreSQL con dependencias disponibles | Completo localmente: 73/73 al 2026-10-22 | — |
| EXT-06 | Operación de 6–8 semanas | Operaciones + pymes | Bitácora, métricas semanales, incidentes y aceptación | No iniciada | G4 |
| EXT-07 | Decisión G4 | Administrador independiente + sponsor | Snapshot autorizado, revisión y decisión firmada | No iniciada | Escala |

## Política de actualización

- No reemplazar `Bloqueado` por `Completo` basándose en datos sintéticos.
- Adjuntar ubicación, responsable, vigencia y fecha de revisión de la evidencia.
- Si una autorización vence o cambia el alcance, reabrir el pendiente.
- No guardar secretos, datos personales ni documentos legales sensibles en este repositorio.
- Revisar este registro en cada hito de release y en la reunión semanal del piloto.
