# Runbook de operación del piloto asistido

> Procedimiento local con datos sintéticos. No habilita contactos externos ni reemplaza las autorizaciones de la puerta G3.

## Inicio de jornada

1. Confirmar en **Contrato y flujo** que el contrato, las plantillas y la autorización aparecen listos.
2. Abrir **Piloto**, fijar la fecha de operación y revisar las seis etapas del recorrido.
3. Revisar facturas en riesgo, documentos pendientes, mensajes fallidos y excepciones abiertas.
4. Confirmar que no existan pagos o mensajes duplicados antes de ejecutar una acción manual.

## Registro obligatorio

Todo trabajo fuera de un flujo automático se registra en la bitácora del piloto:

- `decision`: criterio operativo o de producto adoptado;
- `incident`: privacidad, duplicidad, tono, disponibilidad o error funcional;
- `manual_work`: trabajo humano efectuado dentro o fuera de la aplicación;
- `rule_change`: cambio de contrato, plantilla, clasificación o procedimiento;
- `learning`: observación que debe alimentar el cierre del piloto.

Se debe indicar cliente, fecha efectiva, factura cuando corresponda, detalle y minutos humanos. Los incidentes quedan abiertos hasta documentar su resolución; las demás entradas representan hechos ya completados. Cada alta y resolución genera además un evento auditable.

## Excepciones escaladas a la pyme

1. El operador escala desde **Excepciones** e incluye una pregunta concreta.
2. La pyme responde en **Mi resumen** con aprobar, entregar información o rechazar.
3. La respuesta no ejecuta una acción irreversible ni cierra automáticamente el caso.
4. El operador revisa la respuesta, aplica la corrección necesaria y resuelve la excepción desde su bandeja.

## Incidentes

| Severidad | Ejemplos | Acción local |
|---|---|---|
| Crítica | acceso cruzado entre clientes, dato sensible expuesto, envío no autorizado | pausar operación, preservar evidencia y registrar inmediatamente |
| Advertencia | duplicidad bloqueada, mensaje con tono rechazado, conciliación dudosa | mantener en supervisión y resolver antes del siguiente ciclo |
| Informativa | fricción de uso o mejora sin riesgo inmediato | registrar como aprendizaje y priorizar semanalmente |

No se debe borrar ni reescribir evidencia para ocultar un incidente. La resolución debe describir la corrección, el alcance revisado y el control preventivo.

## Cierre diario

- Verificar que todo incidente crítico o de advertencia tenga responsable y estado.
- Registrar los minutos humanos que todavía no estén en una excepción.
- Revisar pagos verificados y conciliaciones pendientes.
- Confirmar que el recorrido no muestre regresiones en etapas antes completas.

## Revisión semanal

- Exportar las métricas del piloto.
- Comparar DSO y pago oportuno con la línea base.
- Revisar automatización, minutos humanos, costo por factura y margen.
- Agrupar causas documentales y tiempos de resolución.
- Revisar decisiones, cambios de reglas, incidentes y aprendizajes.
- Entregar el reporte semanal a la pyme únicamente por un canal autorizado; mientras exista bloqueo externo, conservarlo como CSV local.
