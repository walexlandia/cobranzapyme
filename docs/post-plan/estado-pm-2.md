# PM-2 — Optimización experimental de la revisión semanal

Fecha de cierre local: 2026-10-28.

PM-2 está **completa en alcance experimental local**. La decisión del responsable del proyecto autorizó avanzar con datos sintéticos sin convertir el resultado en evidencia productiva. La fase reduce y mide un flujo concreto; no automatiza contactos, pagos, conciliaciones ni cambios operativos.

## Admisión de la mejora

| Criterio | Definición |
|---|---|
| Problema | La revisión semanal de cartera concentraba 54 minutos en 3 casos sintéticos, 18 por caso |
| Usuario | Operador que revisa cartera, pagabilidad y excepciones antes de decidir un seguimiento |
| Métrica | Minutos humanos por revisión; línea base 18, objetivo máximo 14,4 |
| Riesgos | Duplicados, decisiones irreversibles, contactos no autorizados y pérdida de trazabilidad |
| Salida | 3 casos comparables, reducción mínima de 20%, cero duplicados y trazabilidad completa |
| Reversión | Una sesión abierta puede cancelarse; una completada queda inmutable y la guía no ejecuta acciones externas |

## Flujo implementado

La guía `weekly_portfolio_review` ordena cinco pasos:

1. revisar saldos y vencimientos;
2. verificar bloqueos de pagabilidad;
3. revisar excepciones abiertas;
4. elegir humanamente el siguiente paso;
5. registrar resultado y minutos reales.

El portal muestra la línea base, el objetivo, el checklist y el avance del benchmark. Iniciar una sesión exige una clave idempotente. Completarla exige confirmar exactamente los cinco pasos, medir minutos y registrar una decisión humana. El cierre crea una sola entrada `manual_work` y eventos de inicio y término; repetir la misma solicitud devuelve la misma sesión.

## Controles de seguridad

- roles limitados a administración y operación;
- ninguna comunicación, pago o conciliación se ejecuta desde la guía;
- ninguna factura, contrato, regla de pagabilidad o excepción cambia automáticamente;
- una sesión abierta se puede cancelar sin contabilizar trabajo;
- una sesión completada es inmutable;
- la base impide duplicar claves idempotentes y vínculos con la bitácora;
- cada cierre declara `external_action_executed: false` en la auditoría.

## Benchmark sintético

| Métrica | Antes | Después |
|---|---:|---:|
| Casos | 3 | 3 |
| Minutos por caso | 18,00 | 12,00 |
| Minutos totales | 54,00 | 36,00 |
| Reducción | — | 33,33% |
| Duplicados | — | 0 |
| Reaperturas | — | 0 |
| Acciones externas | — | 0 |

La reducción supera el objetivo de 20% y conserva trazabilidad completa. La huella del reporte es `dc92f00037524ba8cec4b0f53977f71ebb0a11210b1b16f9c9e86dfd6367a167`.

## Entregables

- migración `0019` y modelo `GuidedWorkSession`;
- API `/api/v1/optimizations/weekly-portfolio-review/*`;
- guía visible en la vista Piloto del portal;
- `scripts/generate_pm2_benchmark.py` y fixture agregado sin identificadores;
- `release/pm-2/benchmark.json` y `release/pm-2/informe.md`;
- pruebas HTTP/PostgreSQL de permisos, idempotencia, cancelación, inmutabilidad, auditoría y benchmark.

## Puerta PM-G2

Estado local: **`passed_synthetic`**.

PM-2 queda cerrada localmente. El resultado permite evaluar la solución y demuestra el contrato técnico, pero no demuestra ahorro real ni autoriza PM-3 productiva. La validación real requiere repetir el benchmark con PM-G1 autorizada y una muestra comparable.

## Validación local

- 77 pruebas HTTP/ORM aprobadas en PostgreSQL 16.
- 34 comprobaciones offline aprobadas.
- migración lineal y correspondencia modelo/esquema verificadas hasta `0019`;
- build de producción Next.js aprobado sin acceso de red;
- verificación integral de release aprobada, con bloqueos externos todavía explícitos.

## Reproducción

```powershell
python scripts\generate_pm2_benchmark.py
docker compose --profile test run --rm test
```
