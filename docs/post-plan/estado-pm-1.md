# PM-1 — Diagnóstico del costo humano

Fecha de corte: 2026-10-21.

PM-1 mide y prioriza; no incorpora automatizaciones, acciones masivas ni cambios de decisión operativa. Su salida es una oportunidad única y cuantificada para PM-2, solo si PM-G1 queda aprobada con evidencia autorizada.

## Alcance implementado

| Tarea | Estado | Evidencia |
|---|---|---|
| Línea base agregada | Completa localmente | Minutos totales, por factura y por fuente |
| Segmentación | Completa localmente | Excepción, bitácora, conciliación, decisión, resultado, severidad y estado |
| Volumen y antigüedad | Completa localmente | Casos, cobertura, abiertos, resueltos, ciclo y edad máxima |
| Recurrencia y concentración | Parcial | Repetición por factura y concentración por cliente sin identificadores |
| Ranking de fricciones | Completa localmente | Orden determinista por minutos, volumen y clave estable |
| Ficha de oportunidad | Provisional | Un único candidato y objetivo de reducción de 20% |
| Medición de conciliación | Instrumentada | Migración `0017`, campo obligatorio en nuevas decisiones y auditoría |
| Reaperturas | Brecha conocida | El modelo actual no habilita ni registra una transición de reapertura |

## Entregables reproducibles

- `GET /api/v1/metrics/human-effort`: diagnóstico JSON exclusivo para administración.
- `GET /api/v1/metrics/human-effort.csv`: dataset agregado sin identificadores ni texto libre.
- `GET /api/v1/metrics/human-effort.md`: informe legible con huella SHA-256.
- `scripts/generate_pm1_diagnostic.py`: generación local con período y tipo de evidencia explícitos.
- `release/pm-1/`: snapshot sintético JSON, CSV y Markdown del período 2026-07-01 a 2026-10-21.

## Resultado sintético

| Posición | Flujo | Casos | Minutos | Participación |
|---:|---|---:|---:|---:|
| 1 | `pilot_log:manual_work` | 3 | 54,00 | 64,29% |
| 2 | `pilot_log:incident` | 3 | 18,00 | 21,43% |
| 3 | `pilot_log:decision` | 3 | 12,00 | 14,29% |
| 4 | `exception:low_confidence` | 3 | 0,00 | 0,00% |

La oportunidad única provisional es `pilot_log:manual_work`. Su línea base es 54 minutos, 18 por caso y 100% de cobertura declarada. El objetivo condicionado de PM-2 es no superar 43,20 minutos totales ni 14,40 minutos por caso en una muestra comparable, manteniendo cero duplicados y trazabilidad completa.

Estos valores verifican el instrumento, no demuestran un costo real. El título y detalle de la bitácora no se exportan y el ranking no contiene nombres, RUT, folios, UUID, mensajes ni notas libres.

## Brechas detectadas y respuesta

1. Las conciliaciones históricas no tenían minutos de revisión. PM-1 agrega captura obligatoria para toda decisión nueva; los registros heredados permanecen nulos y no se rellenan con estimaciones.
2. Un cero en excepciones o bitácora no distingue esfuerzo nulo de medición omitida. Debe resolverse antes de comparar esos casos con evidencia real.
3. La bitácora puede solaparse con trabajo ya registrado en una excepción. Falta una referencia estructurada o marca de trabajo adicional.
4. No existe historial de reaperturas porque el flujo actual no permite reabrir casos. La métrica se declara no disponible y no se inventa.

## Estado de PM-G1

Estado: **`provisional_synthetic`**.

- La línea base y el ranking son reproducibles.
- Existe un candidato material en el seed, pero es una categoría amplia de bitácora.
- La evidencia sintética no aprueba PM-G1.
- Declarar `authorized_pilot` tampoco basta: el diagnóstico exige contrato activo, autorización vigente y comprobante para cada cliente que sustenta la oportunidad.
- PM-2 permanece bloqueada hasta repetir el informe con datos autorizados y resolver las brechas que puedan alterar el ranking.

## Reproducción local

```powershell
python scripts/generate_pm1_diagnostic.py `
  --date-from 2026-07-01 `
  --date-to 2026-10-21 `
  --evidence-kind synthetic
```

El comando lee PostgreSQL, sobrescribe únicamente `release/pm-1/` y emite la huella del contenido estable. No realiza contactos, pagos, conciliaciones ni cambios de estado.

## Validación local

- 33 comprobaciones offline aprobadas.
- 73 pruebas HTTP/ORM aprobadas en PostgreSQL 16.
- Migración lineal verificada desde `0016` hasta `0017`.
- Build de producción Next.js aprobado con `Dockerfile.offline` y red deshabilitada.
- Huella del snapshot sintético: `6c174b95d9d845b51da5969296875b9c4d5eec84d6ab973aa887c6360a4ec9b3`.
