# Plan de trabajo por fases — Recupera

> Basado en `vision-producto.md` y `backlog.md` v0.4  
> Horizonte recomendado: **20 semanas**  
> Construcción principal: semanas 1–16 · Piloto: semanas 12–20

---

## 1. Objetivo del plan

Construir y validar un servicio operado por IA que asegure la pagabilidad de facturas B2B desde su emisión, haga seguimiento hasta el pago, concilie el resultado y permita medir si la gestión documental mejora de manera relevante el pago a tiempo de las pymes.

El plan está diseñado para responder tres preguntas antes de escalar:

1. **Problema:** ¿una proporción relevante de los atrasos se explica por problemas documentales?
2. **Resultado:** ¿resolver esos problemas desde la emisión aumenta el pago a tiempo o reduce el DSO?
3. **Modelo:** ¿el servicio puede operar con margen positivo y una proporción creciente de automatización?

El objetivo no es completar el mayor número posible de funcionalidades, sino llegar a evidencia confiable con 2–3 pymes reales sin comprometer seguridad, trazabilidad ni relación comercial.

---

## 2. Estructura general

| Fase | Semanas | Resultado principal | Sprint de referencia |
|---|---:|---|---|
| 1. Validación inicial y base técnica | 1–2 | Datos reales disponibles y plataforma base funcionando | S1 |
| 2. Contrato y motor operativo | 3–4 | Reglas ejecutables y flujo auditable por factura | S2 |
| 3. Pagabilidad y decisión de enfoque | 5–6 | Checklist, ficha del pagador y validación de la hipótesis central | S3 |
| 4. Comunicaciones y operación multicanal | 7–8 | Envío y recepción reales con controles de contacto | S4 |
| 5. IA supervisada y excepciones | 9–10 | Clasificación medible con intervención humana segura | S5 |
| 6. Pagos, comisión y salida a producción | 11–12 | Sistema desplegado y primera pyme en piloto | S6 |
| 7. Piloto asistido y producto demostrable | 13–16 | Vista cliente, métricas y operación estable | S7–S8 |
| 8. Medición final y decisión de escala | 17–20 | Informe del piloto y decisión de producto | Operación del piloto |

Las tareas comerciales, legales y de validación no esperan a que termine el desarrollo. Corren en paralelo desde la primera semana.

---

## 3. Frentes de trabajo transversales

### Producto y tecnología

- Backend, frontend, worker, base de datos y almacenamiento.
- Flujos, comunicaciones, IA, conciliación y métricas.
- Seguridad, aislamiento multiempresa, auditoría y despliegue.

### Validación de problema y mercado

- Entrevistas con pymes y áreas de cuentas por pagar.
- Análisis retrospectivo de facturas atrasadas.
- Medición de causas, tiempos y comportamiento histórico.

### Comercial y operación

- Selección y onboarding de 2–3 pymes piloto.
- Creación de fichas de pagadores y ejecución manual de excepciones.
- Registro del tiempo humano y aprendizaje operativo.

### Legal y cumplimiento

- Alcance de la gestión B2B.
- Tratamiento de datos y ficha compartida de pagadores.
- Mandato para contactar pagadores y operar portales.
- Contrato de servicio, atribución y comisión.

### Proveedores externos

- Dominio y correo transaccional.
- WhatsApp Business y proveedor BSP.
- Proveedor de LLM.
- Infraestructura de demo y piloto.

---

## 4. Fases detalladas

### Fase 1 — Validación inicial y base técnica

**Semanas:** 1–2  
**Objetivo:** asegurar acceso a datos y candidatos de piloto mientras se construye una base técnica que no será descartada.

#### Trabajo de producto

- Crear la estructura del repositorio y documentación de desarrollo.
- Levantar `db`, `api`, `worker`, `web` y `minio` con `docker compose`.
- Configurar PostgreSQL 16, Alembic y tests contra PostgreSQL.
- Implementar el modelo de datos inicial y el aislamiento multiempresa.
- Crear clientes, importar facturas/contactos y validar RUT, fechas, montos y duplicados.
- Crear datos realistas de demostración.
- Implementar autenticación y roles iniciales.
- Establecer el registro inmutable de eventos desde el comienzo.

#### Trabajo de validación y operación

- Preparar el guion de entrevistas a pymes.
- Iniciar entrevistas y búsqueda de 2–3 pilotos.
- Conseguir acceso anonimizado a facturas y pagos históricos para el análisis retrospectivo.
- Iniciar entrevistas con cuentas por pagar de empresas grandes.
- Iniciar la verificación de WhatsApp Business y configurar el dominio de correo.
- Encargar la revisión legal.

#### Historias y tareas cubiertas

E0-01 a E0-04, E0-07, E1-01 a E1-04, E3-01 a E3-04, E12-01, V-01, inicio de V-02 a V-05, V-07 y V-08.

#### Entregables

- Plataforma local levantable con un comando.
- Migración inicial y suite de tests base.
- Importación funcional de facturas y contactos.
- Dataset demo con 50–100 facturas.
- Guion de entrevistas y primeras entrevistas realizadas.
- Al menos una pyme con datos históricos disponibles; idealmente dos.

#### Criterio de salida

- Se demuestra aislamiento entre dos clientes mediante tests.
- Toda factura importada queda asociada a un cliente y genera eventos auditables.
- Hay acceso suficiente a datos históricos para ejecutar V-03.
- Existen candidatos reales para el piloto; si no los hay, se pausa la expansión técnica y se prioriza adquisición.

---

### Fase 2 — Contrato y motor operativo

**Semanas:** 3–4  
**Objetivo:** convertir las reglas acordadas con cada pyme en un flujo ejecutable, seguro e idempotente.

#### Trabajo de producto

- Configurar tono, canales, horarios, frecuencia, secuencias y escalamiento.
- Configurar comisión y límites para acuerdos.
- Versionar el contrato y asociar cada ejecución a su versión.
- Implementar las etapas de la factura.
- Crear el worker con tabla de trabajos en PostgreSQL.
- Pausar y reanudar secuencias por respuestas, disputas, pagos o intervención manual.
- Agrupar facturas por pagador y destinatario.
- Permitir ejecución automática y ciclo manual con el mismo rastro de auditoría.

#### Trabajo de validación y operación

- Ejecutar el análisis retrospectivo V-03.
- Clasificar las causas de atraso por cantidad, monto y pagador.
- Continuar entrevistas y documentar requisitos recurrentes de los pagadores.
- Borrador inicial del contrato de piloto y de las reglas de atribución.

#### Historias y tareas cubiertas

E2-01 a E2-05, E4-01 a E4-09, continuación de V-02 a V-04 y V-06.

#### Entregables

- Contrato configurable y versionado.
- Simulación completa del avance de una factura por sus etapas.
- Worker idempotente probado.
- Primer informe del análisis retrospectivo.

#### Criterio de salida

- Reiniciar o ejecutar manualmente el worker no duplica acciones.
- Ningún contacto queda programado fuera del horario permitido.
- Cada decisión puede reconstruirse desde la bitácora.
- Las reglas de comisión y atribución tienen una definición preliminar verificable.

---

### Fase 3 — Pagabilidad y decisión de enfoque

**Semanas:** 5–6  
**Objetivo:** construir el diferenciador solo hasta el nivel respaldado por evidencia y tomar una decisión explícita sobre el enfoque documental.

#### Trabajo de producto

- Crear la ficha global del pagador por RUT, separando datos operativos globales de datos privados de cada pyme.
- Generar el checklist de pagabilidad por factura.
- Importar el estado de aceptación o reclamo desde CSV del SII.
- Registrar solicitudes de documentos, carga manual en portales y sus evidencias.
- Detectar facturas incompletas o en riesgo antes del vencimiento.
- Confirmar aprobación y programación de pago en la etapa preventiva.
- Registrar la causa de atraso.

#### Trabajo de validación y operación

- Completar V-03 y presentar resultados.
- Completar la consulta legal antes de contactar pagadores reales.
- Cerrar cartas de intención con las pymes piloto.
- Definir una línea base por pyme: DSO, porcentaje pagado a tiempo y distribución histórica de atrasos.

#### Historias y tareas cubiertas

EP-01 a EP-08, E11-06, V-03, V-05 y avance de V-07.

#### Entregables

- Fichas de pagadores y checklist funcionales.
- Panel inicial de facturas pagables, incompletas, en riesgo y reclamadas.
- Informe de causas históricas de atraso.
- Dictamen legal operativo y restricciones incorporadas al diseño.
- Decisión documentada: continuar, acotar o cambiar el enfoque.

#### Puerta de decisión G1 — Hipótesis documental

Antes de conocer los resultados se debe acordar un umbral para evitar sesgo de confirmación. Como regla inicial recomendada:

- **Continuar con la Épica P completa:** los problemas documentales explican al menos 20% de las facturas atrasadas por cantidad o monto, aparecen en más de una pyme y son operacionalmente resolubles.
- **Acotar a un segmento:** la señal es relevante solo en ciertos rubros, pagadores o tipos de factura. El piloto se concentra allí.
- **Cambiar el enfoque:** la incidencia es baja o los problemas no pueden resolverse desde el servicio. Recupera pasa a cobranza preventiva y de mora temprana, manteniendo solo el checklist esencial.

El porcentaje recomendado es una hipótesis de gestión, no una conclusión de mercado; debe revisarse también por monto, tiempo de atraso y costo de resolución.

#### Criterio de salida

- Toda factura tiene checklist y estado de pagabilidad desde su ingreso.
- No existen filtraciones de datos de una pyme a otra a través de la ficha global.
- La causa de atraso puede registrarse y agregarse.
- La dirección del producto después de la semana 6 está decidida por evidencia.

---

### Fase 4 — Comunicaciones y operación multicanal

**Semanas:** 7–8  
**Objetivo:** ejecutar comunicaciones reales y trazables sin depender de que WhatsApp esté totalmente aprobado.

#### Trabajo de producto

- Enviar correos con remitente por cliente, adjuntos y datos de pago.
- Recibir respuestas y adjuntos por webhook.
- Enviar y recibir mensajes por WhatsApp Business cuando esté disponible.
- Implementar modo asistido de WhatsApp como respaldo.
- Registrar respuestas recibidas por teléfono u otros canales.
- Implementar opt-out por canal.
- Generar mensajes según etapa, destinatario, tono y documentos faltantes.
- Aplicar validaciones de seguridad y plantilla de respaldo.
- Registrar costos de LLM y mensajería por factura.

#### Trabajo de validación y operación

- Aprobar plantillas con las pymes piloto.
- Probar entregabilidad de correo y asociación correcta de respuestas.
- Probar los flujos en un entorno controlado antes de contactar pagadores.
- Finalizar contrato y autorización de operación del piloto.

#### Historias y tareas cubiertas

E5-01 a E5-04, E5-06, E5-07, E5-10, E6-01, E6-08, E8-01, E11-01 y V-06.

#### Entregables

- Flujo bidireccional real por correo.
- WhatsApp automático o modo asistido listo.
- Plantillas aprobadas y versionadas.
- Costos por interacción registrados.

#### Criterio de salida

- Una respuesta se asocia sin ambigüedad a su cliente, pagador y factura o queda en excepción.
- Los opt-outs y horarios se respetan en todos los modos.
- Ningún texto fuera de reglas se envía automáticamente.
- Hay trazabilidad del canal, modo, plantilla y costo.

---

### Fase 5 — IA supervisada y excepciones

**Semanas:** 9–10  
**Objetivo:** automatizar clasificación y extracción gradualmente, manteniendo control humano donde la precisión sea insuficiente.

#### Trabajo de producto

- Clasificar respuestas en las categorías del backlog.
- Extraer fechas, montos, OC, HES y comprobantes.
- Derivar baja confianza, disputas y casos ambiguos a la bandeja.
- Crear la bandeja priorizada de excepciones.
- Permitir corrección de clasificación, checklist, etapa y respuesta.
- Registrar minutos humanos por caso.
- Construir un set de evaluación anonimizado.
- Medir precisión por categoría y permitir automatización selectiva.
- Proponer cambios a la ficha del pagador sujetos a aprobación humana.

#### Historias cubiertas

E6-02 a E6-04, E6-07, E6-09, E7-01 a E7-06, EP-09 y E12-06.

#### Entregables

- Bandeja de excepciones operativa.
- Set de evaluación versionado.
- Reporte de precisión por categoría.
- Registro de tiempo humano y correcciones.

#### Puerta de decisión G2 — Automatización por categoría

- Una categoría solo puede ejecutar acciones automáticas con precisión igual o superior a 90% en un conjunto representativo.
- Las categorías que no alcanzan el umbral permanecen en revisión humana.
- Disputas, datos contradictorios y solicitudes fuera del contrato siempre se escalan, aunque el clasificador tenga confianza alta.

#### Criterio de salida

- Toda clasificación conserva entrada, salida, versión del prompt/modelo, confianza y decisión humana.
- Las correcciones se incorporan al proceso de evaluación sin exponer datos personales.
- Puede operarse el sistema completamente en modo supervisado si la automatización aún no es segura.

---

### Fase 6 — Pagos, comisión y salida a producción

**Semanas:** 11–12  
**Objetivo:** cerrar el ciclo económico y poner la primera pyme en producción.

#### Trabajo de producto

- Registrar pagos manuales con evidencia.
- Importar cartolas bancarias.
- Proponer coincidencias por RUT, monto, suma de facturas y ventana de fechas.
- Confirmar o rechazar coincidencias sin contar pagos dos veces.
- Verificar resultados y aplicar reglas de atribución.
- Generar el resumen mensual de comisión.
- Desplegar entornos separados de demo y piloto con HTTPS.
- Configurar y probar respaldos y restauración.
- Completar cifrado y registro de accesos.

#### Trabajo de operación

- Onboarding de la primera pyme.
- Carga inicial de facturas, contactos, contrato y fichas conocidas.
- Capacitación breve al operador y al contacto de la pyme.
- Prueba de punta a punta con contactos controlados.
- Inicio de V-09 al final de la semana 12.

#### Historias y tareas cubiertas

E8-02 a E8-05, E9-01 a E9-03, E0-05, E0-06, E12-02, E12-03 y comienzo de V-09.

#### Entregables

- Entornos demo y piloto desplegados.
- Conciliación y cálculo de comisión funcionales.
- Respaldo restaurado exitosamente en una prueba.
- Primera pyme operando con facturas reales.

#### Puerta de decisión G3 — Preparación para producción

El piloto empieza únicamente si:

- Los tests críticos pasan contra PostgreSQL.
- Se probó la restauración de un respaldo.
- El aislamiento multiempresa está verificado.
- Los webhooks e idempotencia no duplican mensajes ni pagos.
- El contrato, las plantillas y la autorización de contacto están aprobados.
- Existe un procedimiento claro para pausar toda comunicación.

---

### Fase 7 — Piloto asistido y producto demostrable

**Semanas:** 13–16  
**Objetivo:** operar con datos reales, reducir fricción para la pyme y terminar un producto demostrable sin ampliar el alcance.

#### Trabajo de producto

- Enviar reporte semanal a la pyme.
- Crear vista web de solo lectura con estado y checklist.
- Permitir carga de documentos solicitados.
- Crear panel de métricas operativas y económicas.
- Incorporar fecha de operación configurable en demo.
- Completar aprobaciones, vista de tendencias y mejoras de valor comprobado.
- Corregir defectos observados durante la operación.

#### Trabajo de operación y aprendizaje

- Incorporar las pymes piloto restantes de manera escalonada.
- Revisar diariamente excepciones y semanalmente métricas.
- Medir causas, tiempo de resolución, contactos por factura y resultado.
- Registrar todo trabajo manual, incluido el realizado fuera del sistema.
- Mantener un registro de decisiones y cambios de reglas.

#### Historias cubiertas

E10-01 a E10-05, E11-02 a E11-05, E11-07, E0-08, E2-06, E5-05, E6-05, E6-06, EP-10 y ajustes derivados de V-09.

#### Entregables

- Vista cliente y reporte semanal.
- Panel de métricas con datos reales.
- Entorno demo reproducible.
- Registro de incidencias y aprendizaje del piloto.
- Operación activa de 2–3 pymes, si el onboarding escalonado lo permite.

#### Criterio de salida

- El sistema puede demostrarse de punta a punta sin manipulación directa de la base de datos.
- Los datos de operación permiten calcular costo y margen por cliente.
- Las métricas distinguen claramente acciones manuales y automáticas.
- No hay incidentes graves de privacidad, duplicidad de mensajes o tono.

---

### Fase 8 — Medición final y decisión de escala

**Semanas:** 17–20  
**Objetivo:** completar 6–8 semanas de piloto y transformar los resultados en una decisión empresarial verificable.

#### Trabajo principal

- Mantener la operación estable y corregir solo defectos o bloqueos.
- Evitar nuevas funcionalidades que no sean necesarias para medir el piloto.
- Comparar cada pyme contra su línea base.
- Analizar resultados por pyme, pagador, rubro, monto y causa.
- Calcular margen incluyendo tecnología y minutos humanos.
- Documentar hipótesis confirmadas, rechazadas e inciertas.
- Preparar el informe del piloto y el material para fondos o inversionistas.
- Priorizar el backlog posterior según evidencia.

#### Entregables

- Informe final V-10.
- Dataset agregado y anonimizado de métricas del piloto.
- Revisión de unit economics.
- Decisión de continuidad y alcance de la siguiente versión.
- Backlog reordenado para la fase de producto.

#### Puerta de decisión G4 — Escalar, iterar o pivotar

Se recomienda decidir entre:

1. **Escalar:** la gestión mejora el pago a tiempo o DSO, el problema documental es relevante y existe una ruta creíble a margen positivo.
2. **Iterar el segmento o la operación:** hay resultado, pero está concentrado en ciertos pagadores/rubros o el costo humano sigue alto.
3. **Pivotar el producto:** la hipótesis documental no explica suficiente valor o la atribución del resultado no puede demostrarse.
4. **Detener:** no hay mejora medible, aceptación del cliente ni economía viable después de corregir problemas operativos básicos.

---

## 5. Camino crítico

Las dependencias que pueden retrasar el piloto son:

1. Acceso a datos históricos y selección de pymes piloto.
2. Revisión legal y mandato de contacto.
3. Dominio de correo, entregabilidad y recepción por webhook.
4. Aprobación de WhatsApp Business; el modo asistido evita que bloquee el piloto.
5. Modelo multiempresa y auditoría antes de usar datos reales.
6. Idempotencia de mensajes y pagos.
7. Reglas de atribución acordadas antes de observar los resultados.
8. Disponibilidad del operador humano durante el piloto.

La adquisición de pilotos, el frente legal y los proveedores externos deben administrarse como parte del camino crítico, no como actividades administrativas secundarias.

---

## 6. Métricas y tablero de control

### Resultado para la pyme

- Porcentaje de facturas pagadas dentro del plazo pactado.
- DSO de la cartera gestionada frente a la línea base.
- Monto pagado a tiempo y monto recuperado.
- Tiempo desde emisión hasta condición de pagable.

### Validación de la hipótesis

- Distribución de causas de atraso por cantidad y monto.
- Porcentaje con problemas de aceptación, OC, HES, portal o datos.
- Tiempo de resolución por tipo de problema documental.
- Resultado de facturas con problema resuelto frente a casos comparables.

### Operación y automatización

- Porcentaje de facturas sin intervención humana.
- Proporción manual/automática por envío, clasificación y conciliación.
- Minutos humanos por factura y por excepción.
- Precisión por categoría de clasificación.
- Mensajes, excepciones y documentos solicitados por factura.

### Economía

- Costo de LLM y mensajería por factura.
- Costo humano por cliente.
- Ingreso por fee y comisión.
- Margen operativo por cliente.
- Tiempo desde pago verificado hasta cobro de la comisión.

### Seguridad y calidad

- Incidentes de aislamiento o acceso indebido: objetivo 0.
- Mensajes o pagos duplicados: objetivo 0.
- Quejas escaladas por tono: objetivo 0.
- Restauraciones de respaldo probadas.
- Precisión de conciliaciones propuestas.

---

## 7. Cadencia de gestión

### Diario durante desarrollo

- Revisión breve de bloqueos y dependencias.
- Cierre de una historia completa antes de iniciar otra cuando sea posible.
- Revisión de tests, migración, auditoría y aislamiento en cada cambio.

### Diario durante el piloto

- Revisión de mensajes fallidos, excepciones y facturas en riesgo.
- Control de comunicaciones pendientes y promesas incumplidas.
- Registro del tiempo humano invertido.

### Semanal

- Revisión de métricas por pyme.
- Revisión de precisión de IA y categorías habilitadas.
- Seguimiento de entrevistas, onboarding, legal y proveedores.
- Decisiones de alcance y riesgos documentadas.
- Reporte a cada pyme piloto.

### Al final de cada fase

- Demostración con datos realistas o reales según corresponda.
- Verificación de criterios de salida.
- Decisión explícita de continuar, corregir o reducir alcance.
- Actualización del backlog sin alterar retrospectivamente los datos del piloto.

---

## 8. Regla de control de alcance

Durante las primeras 20 semanas no se incorporan, salvo bloqueo comprobado del piloto:

- Integración automática con el SII o ERP.
- Automatización de portales de proveedores.
- Enlace de pago.
- Conexión bancaria automática.
- SMS.
- Onboarding autoservicio.
- Predicción de fecha de pago.
- Segundo país.
- Migración a Temporal.

Cada solicitud nueva debe responder una pregunta: **¿es imprescindible para operar el piloto o medir una hipótesis crítica?** Si la respuesta es no, queda para la siguiente etapa.

---

## 9. Definición de éxito al cierre

El plan se considera completado cuando:

- 2–3 pymes fueron operadas en producción durante al menos 6 semanas.
- Existe evidencia de las causas de atraso y del efecto de la gestión.
- Se puede comparar pago a tiempo y DSO contra una línea base.
- Se conoce el costo tecnológico y humano por factura y cliente.
- La precisión de IA está medida, no estimada subjetivamente.
- La comisión se calcula únicamente sobre pagos verificados y atribuibles.
- El producto puede demostrarse de punta a punta.
- Se documentó una decisión de escala, iteración, pivote o detención.

---

## 10. Próximas acciones inmediatas

1. Confirmar responsables para tecnología, producto/operación, comercial y legal.
2. Preacordar el criterio de decisión de la hipótesis documental.
3. Identificar las primeras pymes y solicitar datos históricos anonimizados.
4. Preparar el guion y comenzar entrevistas.
5. Iniciar revisión legal, dominio de correo y verificación de WhatsApp.
6. Crear el repositorio de aplicación y ejecutar la Fase 1.

