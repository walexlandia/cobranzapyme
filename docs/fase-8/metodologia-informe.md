# Metodología reproducible del informe V-10

## Parámetros de entrada

Cada ejecución registra en el resultado:

- fecha inicial y final, con máximo 366 días;
- costo humano por hora y tipo de cambio USD/CLP;
- umbral mínimo de facturas por grupo;
- tipo de evidencia: `synthetic` o `authorized_pilot`;
- versión del esquema `fase-8.2-v1`.

La huella SHA-256 se calcula sobre esos parámetros y todos los resultados estables. La hora de generación queda fuera de la huella, por lo que dos ejecuciones sobre los mismos registros y supuestos producen el mismo identificador.

## Cohortes y cálculos

El resumen de resultado mantiene la metodología de Fase 7: una factura queda saldada cuando los pagos verificados acumulados cubren su total; DSO son los días entre emisión y liquidación; pago oportuno compara liquidación y vencimiento.

La comparación por pyme calcula:

- `DSO actual - DSO base`: un valor negativo es mejora;
- `pago oportuno actual - pago oportuno base`: un valor positivo es mejora;
- lectura `improved`, `declined`, `mixed` o `insufficient_data`.

La segmentación toma facturas emitidas dentro del período. Para cada dimensión publica cantidad, monto nominal, pagos verificados dentro del período, facturas saldadas, pago oportuno y días medios hasta liquidación. Las dimensiones no se cruzan entre sí para reducir el riesgo de reidentificación.

## Privacidad

Los alias de pyme y pagador se generan con HMAC-SHA256 y `REPORT_ANONYMIZATION_KEY`. Esta clave debe ser independiente del JWT y del cifrado documental. El modo seguro exige configurarla explícitamente.

Antes de exportar se eliminan nombres, RUT, folios, contactos e identificadores internos. Los grupos bajo el umbral no se publican; solo se informa cuántos grupos y facturas fueron suprimidos por dimensión.

## Interpretación

Las reglas automáticas preparan una recomendación, no sustituyen la decisión de negocio. El informe debe revisarse junto con calidad, incidentes, aceptación del cliente y trazabilidad del piloto. Una ejecución sintética siempre mantiene G4 pendiente.

## Sensibilidad económica

El informe conserva tres escenarios calculados desde la misma comisión y costos observados:

| Escenario | Comisión | Minutos humanos | Tecnología |
|---|---:|---:|---:|
| Conservador | 85% | 125% | 120% |
| Observado | 100% | 100% | 100% |
| Operación eficiente | 100% | 70% | 85% |

Cada escenario recalcula costo humano, costo tecnológico, costo total, costo por factura, margen absoluto y porcentaje de margen. Los multiplicadores quedan dentro de la huella reproducible.

## Snapshot y decisión

Preparar el cierre persiste el informe agregado completo bajo su huella SHA-256. La huella es única, por lo que repetir exactamente el mismo cálculo no genera versiones divergentes.

La decisión requiere:

1. evidencia declarada como piloto autorizado;
2. contrato activo y autorización vigente durante todo el período para cada pyme con facturas gestionadas;
3. todos los mínimos G4 cumplidos;
4. un administrador distinto de quien preparó el snapshot;
5. decisión explícita y justificación de al menos 20 caracteres.

Una decisión registrada no puede editarse ni reemplazarse mediante la API.
Antes de aceptar la decisión, el sistema recalcula el informe con los mismos parámetros y compara su huella. Si pagos, costos, líneas base, autorizaciones u otra evidencia cambiaron, el snapshot queda obsoleto y debe prepararse uno nuevo.
