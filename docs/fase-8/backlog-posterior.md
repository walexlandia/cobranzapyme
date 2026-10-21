# Backlog posterior priorizado por evidencia

> Estado: orden provisional para datos sintéticos. El snapshot decidido conserva el orden definitivo calculado con evidencia autorizada.

La ejecución de estas prioridades se rige por `docs/post-plan/plan-mejora-fases.md`. Una prioridad no autoriza por sí sola una funcionalidad: primero debe superar la regla de admisión y la puerta de su fase.

## Regla de orden

El informe asigna prioridad por riesgo de negocio, no por facilidad técnica:

1. reducir costo humano cuando el margen no está confirmado;
2. fortalecer comparables y atribución cuando el resultado no está confirmado;
3. profundizar pagabilidad si la hipótesis documental se confirma, o probar valor no documental si se rechaza;
4. diversificar pagadores cuando uno concentra 60% o más del monto;
5. endurecer producción solo cuando G4 recomienda escalar; en otro caso, diseñar una iteración acotada.

## Orden local actual

Con evidencia sintética, el desarrollo posterior queda ordenado así:

| Prioridad | Línea | Criterio de salida |
|---:|---|---|
| 1 | Reducir minutos humanos en excepciones y conciliación | Margen positivo en escenario observado y ruta creíble en conservador |
| 2 | Fortalecer línea base, comparables y atribución | Mejora defendible por pyme y trazabilidad entre gestión y pago |
| 3 | Automatizar bloqueos documentales de mayor frecuencia | Menos tiempo de resolución sin aumentar errores o contactos duplicados |
| 4 | Ampliar muestra de pagadores y rubros | Ningún pagador domina la conclusión por concentración de monto |
| 5 | Ejecutar una iteración acotada | Objetivo, responsable, duración y nueva puerta G4 definidos antes de iniciar |

No se inicia endurecimiento para escala hasta que un cierre autorizado termine en una decisión humana `scale`. El orden se vuelve a calcular en cada snapshot porque las hipótesis, costos y concentración pueden cambiar.
