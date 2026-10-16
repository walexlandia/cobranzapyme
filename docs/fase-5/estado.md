# Estado de la Fase 5

> Inicio técnico: 15 de octubre de 2026  
> Restricción vigente: clasificación exclusivamente local, sin modelos ni servicios externos
> Estado: alcance técnico local completado; la puerta G2 productiva requiere respuestas reales anonimizadas

## Incremento 5.1 — Clasificación y excepciones supervisadas

| Historia | Estado | Evidencia |
|---|---|---|
| E6-02 Clasificar respuestas | Implementado localmente | Diez categorías operativas, reglas versionadas, confianza y frases coincidentes |
| E6-03 Extraer datos | Implementado en modo propuesto | Fechas, montos, OC, HES y comprobantes quedan disponibles para revisión; no actualizan estados automáticamente |
| E6-04 Baja confianza | Implementado | Respuestas de baja confianza, correlación incierta y categorías sensibles ingresan a excepción |
| E7-01 Cola priorizada | Implementado | Prioridad por categoría, confianza, correlación, vencimiento y monto |
| E7-02 Contexto completo | Implementado | Mensaje, factura, checklist, ficha del pagador, eventos e historial de clasificación |
| E7-03 Corrección | Completado en 5.2 | Permite confirmar o corregir categoría y extracción; el incremento 5.2 añadió cambios explícitos de checklist y etapa |
| E7-05 Tiempo humano | Implementado | Minutos registrados en la excepción y en el evento de decisión |

## Incremento 5.2 — Evaluación y aprendizaje controlado

| Historia | Estado | Evidencia |
|---|---|---|
| E6-07 / E7-06 Set de evaluación | Implementado localmente | Cada corrección humana agrega un ejemplo anonimizado a un set versionado; los ejemplos son inmutables y el set puede congelarse |
| E6-09 Política por categoría | Implementado como puerta de seguridad | Se muestra precisión y cantidad de muestras; el modo automático exige al menos 90% y 20 muestras |
| E7-03 Corrección operativa | Implementado | La decisión humana puede actualizar explícitamente checklist y etapa, con eventos separados |
| E7-04 Escalamiento a la pyme | Implementado localmente | La nota queda en la excepción y la bitácora con `external_delivery=false` |
| EP-09 Mejora de ficha del pagador | Implementado | La propuesta no modifica la ficha global hasta ser aprobada; aprobación y rechazo quedan auditados |
| E12-06 Anonimización | Implementado localmente | Se eliminan nombres conocidos, emails, teléfonos, RUT, folios y montos antes de persistir el texto de evaluación |

## Incremento 5.3 — Respuesta asistida y reporte G2

| Tarea | Estado | Evidencia |
|---|---|---|
| E7-03 Responder desde la excepción | Implementado | La consola propone una respuesta local editable y crea un único borrador idempotente en la bandeja de salida |
| Seguridad de respuesta | Implementado | El borrador respeta opt-out, remitente, destino y patrones prohibidos; una falla usa texto seguro o bloquea la salida |
| Reporte G2 | Implementado | API, panel y CSV con precisión, recall, errores, falsos negativos, casos y minutos humanos |
| Set ficticio balanceado | Implementado | 200 casos, 20 por categoría, con fuente `synthetic` y resultados reproducibles |
| Mejora de reglas | Implementado | La prueba detectó tres expresiones comunes no cubiertas; tras corregirlas, la exactitud sintética pasó de 81% a 90% |

## Decisiones de seguridad

- El clasificador es determinista (`local-rules-v1`) y no llama a ningún modelo externo.
- Todas las respuestas quedan en supervisión humana durante este incremento.
- Ninguna clasificación ejecuta mensajes, cambios de factura o compromisos automáticamente.
- Aunque una categoría sea elegible, este incremento solo habilita su política; la ejecución de acciones automáticas sigue desactivada.
- Los casos sintéticos nunca se insertan en el set de correcciones humanas ni habilitan la puerta G2.
- Una respuesta creada desde una excepción permanece como borrador manual con `external_delivery=false`.
- Cada clasificación y corrección se conserva como una versión inmutable.
- Una corrección humana crea una nueva revisión con referencia a la decisión reemplazada.
- Respuestas sin contacto, sin factura o con folios ambiguos se priorizan para revisión.

## Componentes entregados

- Tabla `message_classifications` con historial inmutable.
- Ampliación de `exception_cases` con mensaje, clasificación, responsable, tiempo y resolución.
- Migración Alembic `0006_supervised_classification.py`.
- Clasificación automática al registrar respuestas simuladas o manuales.
- API para listar, inspeccionar y resolver excepciones.
- Consola de excepciones con prioridad, confianza, extracción y formulario de decisión humana.
- Datos de demostración de Fase 4 clasificados automáticamente al ejecutar el `seed`.
- Tablas `evaluation_sets`, `evaluation_examples`, `classification_policies` y `payer_profile_proposals`.
- Migración Alembic `0007_evaluation_and_supervision.py`.
- Panel de precisión por categoría, sets versionados, correcciones operativas y propuestas de ficha.
- Preparación de respuestas seguras desde la excepción, integrada con la bandeja de salida de Fase 4.
- Reporte G2 JSON/CSV y panel de errores y esfuerzo humano.
- Generador reproducible `scripts/generate_phase5_evaluation_fixture.py`.
- Fixture `data/demo/evaluation/phase5-balanced.csv` y resultados en `outputs/`.

## Validación ejecutada

- Compilación Python sin errores.
- Diecisiete verificaciones offline aprobadas.
- Contrato OpenAPI compilado con las rutas de clasificación y excepciones.
- Build de producción Next.js aprobado sin red.
- Esquema completo recreado en PostgreSQL 16.
- Invariantes PostgreSQL aprobadas para inmutabilidad, unicidad de excepciones abiertas, sets abiertos y políticas por categoría.
- Tests integrales preparados para clasificación, extracción, priorización, revisión humana, anonimización, precisión y aprobación de propuestas.
- Contrato OpenAPI aprobado para sugerencias, borradores de respuesta y reporte G2.
- Regresión sintética aprobada con 200 casos balanceados y 90% de exactitud global; no habilita automatización.

## Próximo trabajo

1. Mantener toda la operación en modo supervisado hasta reunir respuestas reales anonimizadas y representativas.
2. Ejecutar la puerta G2 por categoría con datos reales; los resultados ficticios no cuentan para este umbral.
3. Cuando existan dependencias disponibles, ejecutar la suite integral preparada sobre PostgreSQL.
4. Continuar localmente con la Fase 6: pagos manuales, cartolas y propuestas de conciliación.

La integración con un modelo de IA real queda fuera de este incremento y requerirá evaluación, costos, privacidad y autorización explícita.
