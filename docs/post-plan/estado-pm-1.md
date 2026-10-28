# PM-1 — Diagnóstico del costo humano

Fecha de corte: 2026-10-28.

PM-1 está **completa localmente**. Mide y prioriza; no incorpora automatizaciones, acciones masivas ni cambios de decisión operativa. Su salida es una oportunidad única y cuantificada para PM-2. La autorización de PM-2 sigue condicionada a que PM-G1 se repita y apruebe con evidencia real autorizada.

## Alcance implementado

| Tarea | Estado | Evidencia |
|---|---|---|
| Línea base agregada | Completa localmente | Minutos totales, por factura y por fuente |
| Segmentación | Completa localmente | Excepción, bitácora, conciliación, decisión, resultado, severidad y estado |
| Volumen y antigüedad | Completa localmente | Casos, cobertura, abiertos, resueltos, ciclo y edad máxima |
| Recurrencia y concentración | Completa localmente | Repetición real por factura y concentración por cliente sin identificadores |
| Ranking de fricciones | Completa localmente | Orden determinista por minutos, volumen y clave estable |
| Ficha de oportunidad | Completa localmente | Un único candidato y objetivo de reducción de 20%; pendiente de validación real |
| Medición de conciliación | Instrumentada | Migración `0017`, campo obligatorio en nuevas decisiones y auditoría |
| Integridad de medición | Completa localmente | Migración `0018`: cero explícito, dato omitido y contabilización adicional/incluida |
| Reaperturas | Completa localmente | Cero por política: casos resueltos inmutables; recurrencias crean casos nuevos |
| Ensayo integral PM-G1.1 | Completo localmente | Tres pymes sintéticas, aprobación, revocación, bloqueo y limpieza total |

## Entregables reproducibles

- `GET /api/v1/metrics/human-effort`: diagnóstico JSON exclusivo para administración.
- `GET /api/v1/metrics/human-effort.csv`: dataset agregado sin identificadores ni texto libre.
- `GET /api/v1/metrics/human-effort.md`: informe legible con huella SHA-256.
- `scripts/generate_pm1_diagnostic.py`: generación local con período y tipo de evidencia explícitos; exige salida externa segura para evidencia autorizada.
- `release/pm-1/`: snapshot sintético JSON, CSV y Markdown del período 2026-07-01 a 2026-10-22.
- `docs/post-plan/pm-g1-readiness.md`: criterios, secuencia, rechazo y custodia de evidencia para ejecutar el gate real.
- `compose.pm-g1-rehearsal.yaml`, `scripts/rehearse-pm-g1.ps1` y `backend/tests/test_pm_g1_rehearsal.py`: ensayo desechable del ciclo completo.
- `docs/post-plan/ensayo-pm-g1.md`: resultado, límites y forma de reproducción del ensayo.

## Resultado sintético

| Posición | Flujo | Casos | Minutos | Participación |
|---:|---|---:|---:|---:|
| 1 | `pilot_log:manual_work` | 3 | 54,00 | 64,29% |
| 2 | `pilot_log:incident` | 3 | 18,00 | 21,43% |
| 3 | `pilot_log:decision` | 3 | 12,00 | 14,29% |
| 4 | `exception:low_confidence` | 3 | 0,00 | 0,00% |

La oportunidad única seleccionada es `pilot_log:manual_work`. Su línea base es 54 minutos, 18 por caso y 100% de cobertura declarada. El objetivo condicionado de PM-2 es no superar 43,20 minutos totales ni 14,40 minutos por caso en una muestra comparable, manteniendo cero duplicados y trazabilidad completa.

Estos valores verifican el instrumento, no demuestran un costo real. El título y detalle de la bitácora no se exportan y el ranking no contiene nombres, RUT, folios, UUID, mensajes ni notas libres.

## Brechas internas cerradas

1. Las conciliaciones históricas no tenían minutos de revisión. PM-1 exige minutos en toda decisión nueva; los registros heredados permanecen nulos y no se rellenan con estimaciones.
2. La migración `0018` agrega `human_minutes_measured` a excepciones y bitácora. Un cero confirmado ahora es medible y un dato heredado omitido queda excluido y señalado.
3. Cada registro nuevo de bitácora declara `additional` o `included_in_exception`. El segundo requiere vínculo a una excepción y sus minutos no vuelven a sumarse.
4. Las reaperturas se reportan como cero y `not_applicable`: el flujo rechaza modificar casos resueltos y representa la recurrencia mediante un caso nuevo auditable.

El snapshot sintético v2 no contiene brechas de medición y declara `measurement_complete: true`. La única limitación restante es externa al instrumento: todavía no existe una muestra real autorizada.

## Estado de PM-G1

Estado: **`provisional_synthetic`**.

- La línea base y el ranking son reproducibles.
- Existe un candidato material en el seed, pero es una categoría amplia de bitácora.
- La evidencia sintética no aprueba PM-G1.
- Declarar `authorized_pilot` tampoco basta: el diagnóstico exige contrato activo, autorización vigente y comprobante para cada cliente que sustenta la oportunidad.
- PM-2 productiva permanece bloqueada hasta repetir el informe con datos reales autorizados y aprobar PM-G1; el responsable autorizó por separado un experimento sintético local.
- El ensayo sintético de PM-G1.1 verificó `approved -> revoked -> authorization_incomplete`, los códigos de salida `0/2`, el cifrado documental y la destrucción del entorno. No cambia el estado externo del gate.

## Reproducción local

```powershell
python scripts/generate_pm1_diagnostic.py `
  --date-from 2026-07-01 `
  --date-to 2026-10-22 `
  --evidence-kind synthetic
```

El comando lee PostgreSQL, sobrescribe únicamente `release/pm-1/` y emite la huella del contenido estable. No realiza contactos, pagos, conciliaciones ni cambios de estado.

## Validación local

- 33 comprobaciones offline aprobadas.
- 74 pruebas HTTP/ORM aprobadas en PostgreSQL 16, incluido el ensayo integral PM-G1.1.
- Migración lineal verificada desde `0016` hasta `0018`.
- Build de producción Next.js aprobado con `Dockerfile.offline` y red deshabilitada.
- Huella del snapshot sintético: `23c4667c2a933ae01b91bf270e12341d0a43eb3376c7834ec68f3c6b6af7f3ed`.
- Ensayo desechable PM-G1.1 aprobado y sin contenedores, redes ni volúmenes residuales.
