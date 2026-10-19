# Guion de demostración de punta a punta

> Duración objetivo: 10–15 minutos. Usar exclusivamente clientes y documentos ficticios mientras no exista autorización para datos reales.

## Preparación

1. Iniciar la aplicación y seleccionar una pyme demo.
2. Abrir **Piloto** y fijar una fecha con evidencia en las seis etapas.
3. Confirmar que la bitácora incluye al menos una decisión, un trabajo manual y una incidencia.
4. No abrir PostgreSQL ni modificar datos desde una consola durante la demostración.

## Recorrido

1. **Cliente, contrato y cartera.** Mostrar datos de la pyme, reglas versionadas y autorización. Explicar que los canales externos siguen bloqueados si G3 no está completa.
2. **Checklist de pagabilidad.** Abrir una factura, mostrar requisitos SII/OC/HES/portal, responsables y estado de riesgo.
3. **Comunicación trazable.** Mostrar un mensaje simulado, su factura, modo, costo y controles de seguridad.
4. **Excepción supervisada.** Mostrar clasificación, evidencia y escalamiento. Entrar como cliente, responder la excepción y volver al operador para demostrar que no se ejecuta automáticamente.
5. **Documento del cliente.** Cargar una evidencia ficticia, mostrar hash/cifrado y aceptar o rechazar como operador.
6. **Pago y conciliación.** Mostrar un pago verificado o una propuesta supervisada, su atribución contractual y la protección contra doble conteo.
7. **Métricas.** Comparar DSO y pago oportuno con la línea base, mostrar automatización, minutos humanos, costos y margen; exportar CSV.
8. **Aprendizaje.** Abrir la bitácora, resolver la incidencia ficticia y mostrar el evento resultante.

## Evidencia de cierre

- Las seis etapas del panel aparecen con evidencia para la fecha seleccionada.
- El cliente solo ve su propia cartera, tendencias, documentos y excepciones escaladas.
- El operador puede completar el recorrido sin escrituras directas en la base.
- Toda acción humana relevante deja actor, fecha, cliente, modo y contenido suficiente para auditoría.
- Se explicitan las partes simuladas y las integraciones externas pendientes; no se presentan como producción real.
