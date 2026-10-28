# Plan de mejora posterior al MVP

Fecha de definición: 2026-10-21.

Este plan comienza después del alcance técnico local de las ocho fases originales. Usa el backlog posterior como fuente, pero no convierte cada idea en una funcionalidad. Cada fase debe demostrar qué riesgo reduce o qué resultado mejora antes de autorizar desarrollo adicional.

La nomenclatura `PM` significa **Plan de Mejora** y evita confundir estas fases con las fases 1–8 del plan original.

## Estado general

| Fase | Propósito | Estado actual | Fuente principal |
|---|---|---|---|
| PM-0 | Base segura, observable y medible | Completa localmente | E12, métricas del piloto y bloques 9.1–9.3 |
| PM-1 | Diagnosticar el costo humano | Completa localmente; PM-G1 externo pendiente | Prioridad 1 del backlog posterior |
| PM-2 | Optimizar un flujo humano comprobado | Completa experimentalmente; PM-G2 real pendiente | E7, E8 y prioridad 1 |
| PM-3 | Fortalecer comparables y atribución | Bloqueada para producción por PM-G2 real | E9, E11 y prioridad 2 |
| PM-4 | Automatizar un bloqueo documental probado | Bloqueada por evidencia real | Épica P y prioridad 3 |
| PM-5 | Ejecutar una iteración real acotada | Bloqueada externamente | Prioridades 4–5 y puerta G4 |
| PM-6 | Preparar escala | Condicional a decisión `scale` | G4 y Épica 13 |

## Regla obligatoria de admisión

Una tarea de desarrollo solo entra a una fase cuando documenta:

1. el problema o evidencia que la origina;
2. el usuario o proceso que obtiene valor;
3. la métrica que debe cambiar;
4. el valor de referencia y el objetivo;
5. los riesgos de privacidad, duplicidad y acciones irreversibles;
6. el criterio verificable de salida y la forma de revertir el cambio.

Si falta cualquiera de estos elementos, la tarea permanece como hipótesis y no se desarrolla. Las integraciones externas siguen bloqueadas mientras no exista autorización, infraestructura y evidencia real.

## PM-0 — Base segura, observable y medible

**Objetivo:** asegurar que cualquier mejora posterior pueda medirse y operarse sin ocultar fallos ni exponer datos.

**Alcance completado:**

- configuración segura y regresión reproducible;
- telemetría agregada, alertas y latido del worker;
- panel administrativo de salud, actualización segura y control por rol;
- métricas de minutos humanos, automatización, costos, margen y causas de atraso ya disponibles.

**Valor aportado:** reduce el riesgo de optimizar a ciegas y permite detectar regresiones operativas.

**Puerta PM-G0:** regresión local aprobada, diagnóstico visible para administración y cero exposición identificatoria en la telemetría. Estado: **aprobada localmente**.

## PM-1 — Diagnóstico del costo humano

**Objetivo:** determinar con evidencia qué paso consume más tiempo antes de construir una solución.

**Trabajo autorizado:**

- establecer la línea base de minutos humanos por factura, excepción y conciliación;
- separar tiempos por tipo de excepción, causa, decisión y resultado;
- medir volumen, antigüedad, reincidencia y concentración de los casos;
- identificar un único cuello de botella prioritario mediante impacto y frecuencia;
- documentar el escenario actual y el objetivo cuantitativo de PM-2.

**Entregables:** informe reproducible, dataset agregado, ranking de fricciones y ficha de oportunidad seleccionada.

**Métricas:** minutos humanos por factura, minutos por caso, tiempo de resolución, porcentaje manual y cantidad de reaperturas.

**No autorizado en esta fase:** acciones masivas, nuevas automatizaciones o cambios al flujo operativo.

**Puerta PM-G1:** existe una línea base reproducible y un solo problema seleccionado que explica una parte material del costo humano. Si los datos no distinguen un cuello de botella, se mejora la medición y no se desarrolla una funcionalidad.

**Estado local al 2026-10-28:** PM-1 está completa en alcance técnico, documental y de ensayo. El instrumento reproducible se ejecutó sobre el seed y la muestra sintética registra 84 minutos: `pilot_log:manual_work` concentra 54 minutos (64,29%), seguido por incidentes con 18 y decisiones con 12. La oportunidad seleccionada tiene como objetivo condicionado reducir al menos 20%, de 54 a no más de 43,2 minutos en una muestra comparable. La migración `0017` incorpora minutos obligatorios en nuevas decisiones de conciliación y la `0018` distingue cero medido de dato omitido, vincula trabajo ya incluido en excepciones y evita doble conteo. Las reaperturas son cero por diseño porque un caso resuelto es inmutable y una recurrencia crea un caso nuevo. PM-G1.1 ensayó con tres pymes sintéticas la aprobación, revocación, bloqueo, cifrado, salida segura y destrucción del entorno. La muestra no presenta brechas internas, pero PM-G1 real permanece en `provisional_synthetic` porque falta evidencia autorizada; por ello PM-2 continúa bloqueada.

## PM-2 — Optimización del flujo seleccionado

**Objetivo:** reducir el costo del cuello de botella elegido en PM-1 sin aumentar errores ni acciones duplicadas.

**Trabajo autorizado como experimento local por decisión del responsable; condicionado a PM-G1 para uso real:**

- mapear el flujo actual y eliminar pasos sin valor;
- diseñar asistencia guiada para la decisión repetitiva seleccionada;
- incorporar agrupación o ejecución por lote solo si la acción es idempotente, reversible y auditable;
- mantener aprobación humana en pagos, comunicaciones, conciliaciones y cambios sensibles;
- ejecutar un benchmark controlado antes/después.

**Entregables:** flujo optimizado, pruebas de seguridad e idempotencia y comparación reproducible contra la línea base.

**Métricas:** reducción de minutos y tiempo de resolución, tasa de error, duplicados, reaperturas y porcentaje de casos resueltos sin pasos adicionales.

**Puerta PM-G2:** el benchmark reduce al menos 20% el tiempo del flujo seleccionado, mantiene cero duplicados y conserva trazabilidad completa. El resultado sintético autoriza evaluación, no demuestra rentabilidad real.

**Estado local al 2026-10-28:** PM-2 está completa experimentalmente. Se acotó `manual_work` a la revisión semanal de cartera y se implementó una sesión guiada de cinco pasos, idempotente, cancelable antes del cierre, inmutable después y sin acciones externas. El benchmark sintético comparable redujo 54 a 36 minutos, 33,33%, con tres casos, cero duplicados, cero reaperturas y trazabilidad completa. PM-G2 queda en `passed_synthetic`; la evidencia real continúa pendiente y PM-3 no está autorizada para producción.

## PM-3 — Comparables y atribución defendible

**Objetivo:** demostrar que el resultado observado puede relacionarse con la gestión y no solo con variaciones de cartera o del pagador.

**Trabajo condicionado a PM-G2:**

- revisar completitud y calidad de las líneas base por pyme;
- definir cohortes comparables y reglas explícitas de exclusión;
- reconstruir la cadena gestión, evidencia, pago verificado y regla contractual;
- identificar concentración por pagador, rubro, monto y causa;
- separar correlación, atribución defendible e incertidumbre.

**Entregables:** matriz de comparables, reporte de trazabilidad de atribución y listado de brechas de evidencia.

**Métricas:** cobertura de línea base, pagos con evidencia trazable, pagos excluidos, concentración y resultados por cohorte.

**Puerta PM-G3:** todo resultado incluido se reconstruye hasta un pago verificado y una regla contractual, sin doble conteo, y las comparaciones declaran sus exclusiones. La evidencia real sigue siendo necesaria para afirmar impacto comercial.

## PM-4 — Automatización documental basada en evidencia

**Objetivo:** automatizar únicamente el bloqueo documental que la evidencia real confirme como frecuente y costoso.

**Condición de entrada:** PM-G3 aprobada y datos autorizados que confirmen la hipótesis documental para una categoría concreta.

**Trabajo posible, sujeto a la evidencia:** detección, solicitud, seguimiento o actualización asistida del requisito seleccionado. No se habilitan integraciones con SII, ERP o portales solamente por conveniencia técnica.

**Métricas:** tiempo de resolución documental, precisión, contactos duplicados, intervención humana y porcentaje de facturas que alcanzan condición pagable.

**Puerta PM-G4:** mejora medible frente a casos comparables, precisión mínima de 90% para cualquier automatización y cero contactos duplicados o acciones irreversibles sin aprobación.

## PM-5 — Iteración real acotada

**Objetivo:** validar en 2–3 pymes y durante 6–8 semanas si las mejoras producen resultado y economía sostenibles.

**Trabajo:** cerrar autorizaciones e infraestructura, seleccionar muestra, fijar objetivos, operar el piloto, revisar incidentes y recalcular el informe final.

**Métricas:** pago oportuno, DSO, tiempo hasta pagabilidad, minutos humanos, costo por factura, margen, concentración e incidentes.

**Puerta PM-G5:** decisión humana documentada de escalar, iterar, pivotar o detener. Estado actual: **bloqueada por dependencias externas**.

## PM-6 — Escala condicionada

Esta fase solo existe si PM-G5 termina en `scale`. Recién entonces se priorizan endurecimiento de infraestructura, integraciones y elementos de la Épica 13 según retorno, riesgo y evidencia. Una decisión `iterate`, `pivot` o `stop` genera un plan diferente y no autoriza estas inversiones.

## Próximo trabajo autorizado

PM-2 está cerrada localmente en modalidad experimental. El trabajo productivo siguiente continúa siendo **PM-G1/PM-G2 — validación con evidencia real autorizada**. Cualquier avance local hacia PM-3 debe conservar la misma separación explícita entre prueba sintética y autorización productiva.
