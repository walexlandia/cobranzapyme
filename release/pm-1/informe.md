# PM-1 — Diagnóstico del costo humano

Período: 2026-07-01 a 2026-10-22 (114 días)
Tipo de evidencia: synthetic
Esquema: pm-1-v2
Huella reproducible SHA-256: `23c4667c2a933ae01b91bf270e12341d0a43eb3376c7834ec68f3c6b6af7f3ed`

> Evidencia sintética: permite verificar el instrumento, pero no aprueba PM-G1.

## Línea base

- Minutos humanos medidos: 84.00
- Minutos por factura gestionada: 0.93
- Minutos en excepciones: 0.00
- Minutos en bitácora: 84.00
- Minutos en conciliación: 0.00
- Porcentaje de acciones manuales observadas: 75.00%
- Reaperturas: 0 (not_applicable; los casos resueltos son inmutables).

## Ranking de fricciones

| # | Flujo | Casos | Cobertura | Minutos | Participación | Abiertos | Elegible |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | `pilot_log:manual_work` | 3 | 100.00% | 54.00 | 64.29% | 0 | sí |
| 2 | `pilot_log:incident` | 3 | 100.00% | 18.00 | 21.43% | 3 | sí |
| 3 | `pilot_log:decision` | 3 | 100.00% | 12.00 | 14.29% | 0 | sí |
| 4 | `exception:low_confidence` | 3 | 100.00% | 0.00 | 0.00% | 3 | no |

## Conciliación

- Propuestas: 0
- Decisiones: 0
- Ciclo medio de decisión: sin muestra horas
- Minutos humanos medidos: sin muestra. El tiempo de ciclo no se usa como sustituto.

## Oportunidad y puerta PM-G1

Estado: **provisional_synthetic**.

La medición distingue una oportunidad, pero la evidencia sintética no aprueba PM-G1 ni autoriza cambios operativos de PM-2.

Oportunidad única: `pilot_log:manual_work`.

El flujo pilot_log:manual_work concentra 64.29% de los minutos medidos.
Objetivo PM-2 condicionado: reducir 20% hasta un máximo de 43.20 minutos totales en una muestra comparable.

## Brechas de medición

- Sin brechas internas en la muestra analizada.

## Privacidad

El reporte y el CSV son agregados. No contienen nombres, RUT, folios, UUID, mensajes ni notas libres.
