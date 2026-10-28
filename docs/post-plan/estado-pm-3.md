# Estado de PM-3 — Comparables y atribución defendible

Fecha de cierre local: 2026-10-28.

## Resultado

PM-3 queda **completa en modalidad experimental local**. La puerta PM-G3 alcanza `passed_synthetic`: el contrato técnico y la trazabilidad se verifican con datos inventados, pero la evidencia real autorizada sigue pendiente y **PM-4 no queda autorizada para producción**.

## Ficha de admisión

- **Problema:** un pago posterior a una gestión puede coincidir temporalmente sin que exista una cadena suficiente para atribuir el resultado.
- **Usuario y proceso:** operador o administrador que revisa el piloto, sus métricas y una futura decisión de inversión.
- **Métrica:** cobertura de pagos trazables, completitud de línea base, exclusiones reconciliadas, duplicados y concentración por cohorte.
- **Referencia:** PM-2 podía demostrar un flujo más corto, pero no reconstruía pago, evidencia, gestión y regla contractual en una sola unidad comparable.
- **Objetivo local:** incluir al menos tres pagos con cadena completa, cero duplicados, 100% de exclusiones declaradas y cohortes agregadas publicables.
- **Riesgos:** doble conteo, atribución causal excesiva, grupos pequeños, identificadores expuestos y uso productivo de evidencia sintética.
- **Salida:** reporte reproducible, matriz CSV, pruebas de roles y privacidad, y PM-G3 sintética aprobada sin habilitar PM-4.
- **Reversión:** retirar el panel y los endpoints PM-3; la migración `0020` solo agrega el rubro opcional de la pyme y puede revertirse sin alterar pagos, eventos o atribuciones.

## PM-3.1 — Cohortes y exclusiones

La unidad de análisis es un **pago verificado**. Un pago solo ingresa al conjunto comparable cuando conserva:

1. pyme activa con línea base DSO y pago oportuno;
2. factura en CLP;
3. responsable y fecha de verificación;
4. comprobante cifrado AES-GCM o movimiento bancario asociado;
5. atribución única que coincide con pyme, factura y monto;
6. contrato de la pyme, versión y regla congeladas;
7. uno o más eventos de gestión elegibles, anteriores al pago y asociados a la misma factura.

Se declaran diez exclusiones explícitas: línea base ausente, moneda no soportada, metadatos de verificación ausentes, evidencia de pago ausente, atribución ausente o inconsistente, contrato ausente, regla contractual ausente y evidencia de gestión ausente o inválida.

## PM-3.2 — Cadena de atribución

El reporte reconstruye la cadena `gestión → evidencia → pago verificado → regla contractual`. La fecha por sí sola no se considera causalidad: una cadena incompleta se clasifica como correlación o incertidumbre y no integra los resultados atribuidos.

Cada pago puede aparecer una sola vez. Los pagos parciales se mantienen como unidades distintas y sus montos no se duplican. El resultado público no contiene nombres, RUT, folios, identificadores de pagos o eventos ni texto libre.

## PM-3.3 — Cobertura y concentración

La matriz agrega cinco dimensiones:

- pyme con alias HMAC estable;
- pagador con alias HMAC estable;
- rubro de la pyme;
- tramo del monto;
- causa del atraso.

Los grupos menores al umbral configurado se suprimen. La muestra sintética versionada contiene seis pagos verificados, cuatro incluidos y dos excluidos, para una cobertura trazable de 66,67%. Los incluidos tienen cadena completa y cero duplicados. Las dos exclusiones —gestión ausente y línea base ausente— concilian exactamente con la población.

La concentración máxima observada es 50% por pyme, pagador, rubro y causa; el tramo de monto concentra 100%. Este último valor se conserva como señal de limitación de la muestra y no se presenta como representatividad comercial.

## PM-3.4 — Artefactos y controles

- servicio reproducible `pm-3-v1` y endpoints de reporte JSON, matriz CSV e informe Markdown;
- panel de operador/administrador con cobertura, trazabilidad, cohortes, concentración y exclusiones;
- rubro opcional de la pyme, incorporado por la migración lineal `0020`;
- fixture sintético versionado y generador determinista;
- artefactos en `release/pm-3/`, con huella SHA-256 `817425a84214c74f0db6f9aa4c8a220c87f3257258d55618e1b3b4383768f491`;
- acceso denegado al rol cliente y garantía de que indicar `authorized_pilot` no evita la validación de autorizaciones reales.

La regresión final ejecutó 79 pruebas backend sobre PostgreSQL, 35 comprobaciones offline, el build web sin red y el verificador local de release. Todos terminaron correctamente; permanecen bloqueadas únicamente las dependencias externas ya declaradas en el manifiesto.

## Puerta PM-G3

| Control | Resultado local |
|---|---|
| Muestra mínima | PASS — 4 pagos incluidos |
| Línea base completa en incluidos | PASS |
| Cadena completa en incluidos | PASS |
| Duplicados | PASS — 0 |
| Exclusiones reconciliadas | PASS |
| Cohortes publicables | PASS — 5 dimensiones |
| Evidencia real autorizada | PENDIENTE EXTERNO |
| PM-4 productiva autorizada | NO |

La evidencia sintética permite evaluar y mantener el producto, pero no demuestra impacto comercial. El siguiente trabajo productivo sigue siendo obtener autorizaciones y repetir PM-G1, PM-G2 y PM-G3 con evidencia real.
