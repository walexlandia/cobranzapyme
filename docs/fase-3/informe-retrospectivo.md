# Informe retrospectivo de prueba — Fase 3

> Fecha de corte: 14 de octubre de 2026  
> Fuente: `outputs/recupera-datos-prueba.xlsx`  
> Naturaleza de los datos: completamente sintéticos

## Resultado general

El conjunto contiene 120 facturas por $323.820.000, distribuidas en tres pymes ficticias. Noventa facturas tienen una causa de atraso informada, por un monto de $245.900.000.

Las causas documentales explican:

- 46 de las 90 facturas atrasadas: 51,11% por cantidad.
- $129.168.000 de los $245.900.000 atrasados: 52,53% por monto.
- Casos en las tres pymes incluidas en la prueba.

## Causas documentales

| Causa | Facturas | Monto |
|---|---:|---:|
| Aceptación o reclamo SII | 12 | $28.712.000 |
| Orden de compra | 10 | $27.524.000 |
| HES o conformidad | 12 | $38.128.000 |
| Portal de proveedores | 12 | $34.804.000 |
| **Total documental** | **46** | **$129.168.000** |

## Otras causas

| Causa | Facturas | Monto |
|---|---:|---:|
| Liquidez del pagador | 12 | $31.344.000 |
| Disputa comercial | 12 | $29.268.000 |
| Proceso interno del pagador | 20 | $56.120.000 |

## Línea base por pyme

| Pyme | Facturas | Monto facturado | DSO declarado | DSO observado en pagos | Pagado a tiempo | Distribución de pagos observados |
|---|---:|---:|---:|---:|---:|---|
| Servicios Cordillera SpA | 40 | $106.940.000 | 51,4 días | 44,40 días | 46,67% | 7 a tiempo, 6 con 1–15 días y 2 con 16–30 días de atraso |
| Ingeniería del Sur Ltda. | 40 | $107.940.000 | 46,2 días | 42,00 días | 42,86% | 6 a tiempo, 5 con 1–15 días y 3 con 16–30 días de atraso |
| Montajes Atacama SpA | 40 | $108.940.000 | 57,8 días | 41,94 días | 43,75% | 7 a tiempo, 6 con 1–15 días y 3 con 16–30 días de atraso |

El DSO declarado pertenece a la ficha ficticia de cada pyme. El DSO observado se calcula solo sobre las 45 facturas con pago registrado. No deben tratarse como la misma métrica ni reemplazarse entre sí.

## Lectura para el producto

Los datos de prueba justifican técnicamente mantener cuatro requisitos bloqueantes: aceptación SII, orden de compra, HES o conformidad y carga en portal. También justifican separar el estado de pagabilidad del estado de cobranza, porque una factura emitida puede seguir incompleta antes de vencer.

Este análisis sirve para probar cálculos, interfaz y umbrales. No demuestra prevalencia en empresas reales. La misma metodología debe repetirse con datos autorizados de las pymes piloto antes de confirmar la hipótesis documental.

## Reproducción

Ejecutar con el Python incluido en las dependencias de trabajo:

```powershell
python scripts/analyze_retrospective.py
```

El script lee el libro sin modificarlo y entrega el detalle calculado en JSON.
Para repetir V-03 con un libro real autorizado se debe usar `--workbook` junto con la declaración explícita `--authorized-real-data`, siguiendo el procedimiento de `paquete-validacion-externa.md`.
