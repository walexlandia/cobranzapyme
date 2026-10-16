# Backlog de Producto — Recupera (MVP piloto)

> Versión: 0.4 · Octubre 2026
> Ver contexto en `vision-producto.md`
> Cambios v0.4: tras el análisis de mercado, el producto se enfoca en **la pagabilidad de la factura desde su emisión** además del seguimiento hasta el pago. Se agregan la Épica P (pagabilidad y ficha del pagador), la medición de causas de atraso y nuevas tareas de validación. "Deudor" pasa a llamarse **pagador**.
> Se mantienen de v0.3: el MVP es el piloto; PostgreSQL en Docker siempre, nunca SQLite; doble modo solo donde agrega valor.

**Priorización:** MoSCoW — **M** (Must, imprescindible para el piloto) · **S** (Should) · **C** (Could) · **W** (Won't por ahora)
**Estimación:** XS (<0,5 día) · S (1–2 días) · M (3–5 días) · L (1–2 semanas) · XL (requiere dividir)

---

## Objetivo del MVP piloto

Construir un producto **sólido, en producción y demostrable** que gestione extremo a extremo las facturas de **2–3 pymes piloto** que le facturan a empresas medianas y grandes: importar facturas, asegurar su pagabilidad (aceptación en el SII, OC, HES, portal de proveedores), hacer seguimiento preventivo y de mora temprana por email y WhatsApp, clasificar respuestas con IA, derivar excepciones a un operador, conciliar pagos y calcular la comisión por resultado.

El piloto debe producir además **el dato que sostiene la innovación**: qué proporción de los atrasos se explica por problemas documentales y cuánto mejora el pago a tiempo al resolverlos desde la emisión.

Lo que se construye no se tira: el piloto corre sobre la misma base que después escala.

**Fuera del MVP piloto:** cobranza extrajudicial o judicial, publicación en boletines, carga automatizada en portales de proveedores, integración directa con el SII o ERPs, scoring entre clientes, link de pago, multipaís, autoservicio.

### Qué significa "sólido para mostrar"

Al cierre del MVP piloto debe poder mostrarse a evaluadores de CORFO / Start-Up Chile, a inversionistas y a nuevas pymes:

- La aplicación desplegada en una URL con HTTPS.
- Envío y **recepción** real de emails y WhatsApp.
- El **checklist de pagabilidad** de cada factura y las **fichas de los pagadores** con lo aprendido.
- Una **vista cliente** donde la pyme ve el estado de sus facturas, lo pendiente de su parte, lo pagado y las excepciones.
- Un **panel de métricas** con datos reales: causas de atraso, % pagado a tiempo, monto recuperado, % sin intervención humana, minutos humanos y costo por factura, margen, DSO vs. línea base.
- Un **entorno de demostración** con una pyme ficticia y datos realistas.
- Bitácora de auditoría completa.
- Tests automáticos pasando y respaldos diarios de la base de datos.

### Principio: modo manual y modo automático donde agrega valor

El doble modo se incluye **solo donde resuelve un problema real del piloto**. Ambos modos dejan el mismo rastro de auditoría, con el modo registrado en cada evento.

| Operación | Modo manual | Modo automático | Por qué ambos | Historias |
|---|---|---|---|---|
| Ejecución de los flujos | Botón "ejecutar ciclo ahora" | Worker programado según el contrato | Cuesta poco y sirve para probar, recuperar fallas y demostrar | E4-02, E4-09 |
| Envío por WhatsApp | Modo asistido: texto generado + link | WhatsApp Business API con plantillas aprobadas | La aprobación de Meta puede tardar | E5-03, E5-07 |
| Respuestas del pagador | Registrar una respuesta recibida por otro medio (teléfono, correo personal) | Recepción por webhook de email y WhatsApp | Muchos pagadores llamarán a la pyme | E5-02, E5-04, E5-10 |
| Clasificación de respuestas | El operador revisa y confirma o corrige | Acción automática por categoría con precisión ≥90% | Núcleo del modelo: de aquí sale el % sin intervención humana | E6-02, E6-04, E6-09 |
| Conciliación de pagos | Registro manual con comprobante | Coincidencias propuestas contra la cartola, que el operador confirma | Ninguna fuente sola basta | E8-02, E8-04, E8-05 |
| Carga en portales de proveedores | El operador carga y registra la evidencia | — (fuera del piloto) | Requiere credenciales de la pyme; se automatiza solo con volumen y autorización | EP-06, EP-11 |

**Regla transversal:** un mismo pago nunca se cuenta dos veces.

**Métrica del piloto:** proporción automático/manual en envíos, clasificaciones y conciliaciones (E11-05).

---

## Stack técnico

| Capa | Elección | Notas |
|---|---|---|
| Backend / API | FastAPI (Python) | — |
| Base de datos | **PostgreSQL 16 en Docker** | En desarrollo, tests, demo y producción. **Nunca SQLite.** |
| Migraciones | Alembic | Todo cambio de esquema es una migración versionada |
| Worker y tareas programadas | Contenedor worker + tabla de jobs en PostgreSQL | Temporal solo si aparecen flujos largos con aprobaciones |
| Frontend operador y cliente | Next.js | Dos áreas: operador y vista cliente |
| LLM | API de un modelo de lenguaje, con prompts versionados en el repositorio | Set de evaluación propio |
| Email | Proveedor transaccional con webhook de correos entrantes | Dominio propio con SPF, DKIM y DMARC |
| WhatsApp | WhatsApp Business API vía proveedor (BSP) | Verificación con Meta desde la semana 1; mientras tanto, modo asistido |
| Archivos / evidencia | Almacenamiento S3 compatible (MinIO en Docker para desarrollo) | Facturas, OC, HES, comprobantes, evidencias de carga en portales |
| Orquestación local | `docker compose`: `db`, `api`, `worker`, `web`, `minio` | Un solo comando levanta todo |
| Despliegue | Contenedores en un proveedor cloud, PostgreSQL con volumen persistente y respaldo | Entornos: `demo` y `piloto` |
| Observabilidad | Logs estructurados + tabla de eventos | OpenTelemetry más adelante |
| CI | Tests en cada push contra PostgreSQL en contenedor | — |

---

## Épica 0 — Plataforma e infraestructura

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E0-01 | Como equipo, levanto todo el sistema con `docker compose up` (db, api, worker, web, minio) | M | S |
| E0-02 | Como equipo, gestiono el esquema con migraciones Alembic | M | S |
| E0-03 | Como equipo, los tests corren contra PostgreSQL en contenedor, local y en CI | M | S |
| E0-04 | Como equipo, cargo datos de demostración (pyme ficticia, 50–100 facturas, pagadores con fichas, respuestas) con un comando | M | S |
| E0-05 | Como equipo, despliego los entornos `demo` y `piloto` con HTTPS | M | M |
| E0-06 | Como equipo, tengo respaldos diarios automáticos de PostgreSQL y probé restaurarlos | M | S |
| E0-07 | Como equipo, las credenciales viven en variables de entorno / secretos, nunca en el código | M | XS |
| E0-08 | Como operador, puedo fijar una "fecha de operación" en el entorno demo para mostrar el flujo completo sin esperar días | S | S |

---

## Épica 1 — Modelo de datos y multiempresa

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E1-01 | Como sistema, necesito entidades `Cliente (pyme)`, `Contrato`, `Pagador` (global por RUT), `FichaPagador`, `RelaciónClientePagador`, `Contacto`, `Factura`, `ÍtemPagabilidad`, `Documento`, `Mensaje`, `Pago`, `MovimientoBancario`, `Excepción`, `Evento` | M | M |
| E1-02 | Como sistema, todo dato de una pyme (facturas, montos, mensajes, contactos personales, pagos) está aislado por cliente (multi-tenant por fila, verificado con tests) | M | S |
| E1-03 | Como sistema, registro un log de eventos inmutable por factura (auditoría) | M | S |
| E1-04 | Como operador, creo un cliente con datos básicos, remitente, datos bancarios y DSO línea base | M | S |

**Criterios de aceptación E1-03:** cada cambio de estado, mensaje enviado/recibido, documento, clasificación y decisión humana genera un evento con timestamp, actor (sistema/IA/humano/pagador) y datos asociados; los eventos no se editan ni borran (restricción también a nivel de base de datos).

---

## Épica 2 — Contrato de resultado

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E2-01 | Como operador, configuro por cliente: tono, canales permitidos, horarios, frecuencia máxima de contacto y secuencia de días por etapa | M | M |
| E2-02 | Como operador, configuro límites de acuerdos de pago (máx. cuotas, plazo máximo, monto mínimo para escalar) | M | S |
| E2-03 | Como operador, configuro reglas de escalamiento (monto, días de mora, tipo de respuesta, confianza mínima de la IA) | M | S |
| E2-04 | Como operador, configuro la comisión: fee de activación, % por pago a tiempo tras gestión documental/preventiva y % por recuperación en mora | M | S |
| E2-05 | Como sistema, versiono el contrato: cada gestión registra con qué versión se ejecutó | M | S |
| E2-06 | Como cliente, apruebo las plantillas base antes de que se usen | S | S |

---

## Épica 3 — Importación de facturas y contactos

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E3-01 | Como operador, importo facturas desde Excel/CSV con mapeo de columnas (incluye el formato de exportación del Registro de Compras y Ventas del SII), incluyendo N° de OC si existe | M | M |
| E3-02 | Como sistema, valido datos (RUT, montos, fechas, duplicados) y muestro errores por fila antes de confirmar | M | S |
| E3-03 | Como operador, importo contactos por pagador con rol: cuentas por pagar, solicitante/administrador de contrato, otro | M | S |
| E3-04 | Como operador, marco facturas como pagadas, anuladas, reclamadas o en disputa manualmente | M | S |
| E3-05 | Como sistema, importo facturas emitidas desde XML de DTE del SII | W | M |
| E3-06 | Como sistema, sincronizo automáticamente facturas desde el SII o un ERP | W | XL |

---

## Épica P — Pagabilidad de la factura y ficha del pagador (diferenciador)

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| EP-01 | Como operador, mantengo una **ficha por pagador** (global por RUT): requisitos para pagar (OC, HES/conformidad, guía de despacho, otros), portal de proveedores y cómo se usa, canales y contactos corporativos de cuentas por pagar, días o ciclo de pago | M | M |
| EP-02 | Como sistema, la ficha del pagador contiene solo información operativa de la empresa pagadora; ningún dato de una pyme (facturas, montos, contactos personales, conversaciones) es visible para otra (probado con tests) | M | S |
| EP-03 | Como sistema, genero para cada factura un **checklist de pagabilidad** a partir de la ficha del pagador: aceptación en el SII, OC, HES/conformidad, carga en portal, otros; con estado por ítem (pendiente, solicitado, cumplido, no aplica) | M | M |
| EP-04 | Como operador, importo el estado de aceptación o reclamo de las facturas desde la información disponible en el SII (CSV) y el sistema alerta facturas reclamadas o no aceptadas dentro del plazo legal | M | S |
| EP-05 | Como sistema, solicito cada documento faltante al destinatario correcto (el solicitante en el pagador para la HES, la pyme para documentos propios) y hago seguimiento hasta obtenerlo | M | M |
| EP-06 | Como operador, registro la carga de una factura en el portal de proveedores del pagador con su evidencia (N° de ingreso, captura) | M | S |
| EP-07 | Como sistema, marco una factura **en riesgo** si su checklist está incompleto a N días del vencimiento y la priorizo en la bandeja | M | S |
| EP-08 | Como sistema, en la etapa preventiva confirmo con cuentas por pagar que la factura está aprobada y programada para pago | M | S |
| EP-09 | Como sistema, la IA propone actualizaciones a la ficha del pagador a partir de las respuestas recibidas (nuevo requisito, nuevo canal, día de pago) y el operador las aprueba | M | S |
| EP-10 | Como equipo, veo por pagador el plazo real de pago observado y las causas de atraso más frecuentes (agregado, sin exponer datos de pymes) | S | S |
| EP-11 | Como sistema, cargo facturas en portales de proveedores de forma automatizada, con autorización explícita y credenciales seguras | W | L |
| EP-12 | Como sistema, consulto automáticamente el estado de las facturas en el SII | W | L |

**Criterios de aceptación EP-03 / EP-07:** toda factura importada tiene checklist desde el día de emisión; el estado de pagabilidad (pagable / incompleta / en riesgo / reclamada) es visible en la lista de facturas, en la vista cliente y en el panel de métricas; cada cambio de ítem genera un evento.

---

## Épica 4 — Motor de flujos

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E4-01 | Como sistema, asigno a cada factura una etapa: emisión, documental, preventiva, vencimiento, mora temprana, escalamiento | M | S |
| E4-02 | Como sistema, el worker ejecuta las secuencias por etapa según el contrato y el checklist de pagabilidad | M | M |
| E4-03 | Como sistema, respeto horarios, frecuencia máxima y canales del contrato | M | S |
| E4-04 | Como sistema, agrupo facturas del mismo pagador y destinatario en un solo contacto | M | S |
| E4-05 | Como sistema, pauso la secuencia cuando hay respuesta, documento pendiente de la pyme, promesa de pago, disputa o pago | M | S |
| E4-06 | Como sistema, reanudo la secuencia si una promesa o una fecha de programación de pago no se cumple | M | S |
| E4-07 | Como operador, pauso o reanudo manualmente la gestión de una factura o pagador | M | XS |
| E4-08 | Como sistema, la ejecución es idempotente: si el worker se reinicia o se ejecuta un ciclo manual, no se duplican mensajes | M | S |
| E4-09 | Como operador, ejecuto un ciclo manualmente (por cliente o global) y veo qué se generó | M | S |

**Criterios de aceptación E4-03:** ningún mensaje se envía fuera del horario configurado (zona horaria America/Santiago); si cae fuera, se reprograma al siguiente horario válido; se registra el evento.

---

## Épica 5 — Comunicación multicanal

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E5-01 | Como sistema, envío emails desde un remitente configurado por cliente, con datos de la factura, documentos adjuntos y datos de pago | M | M |
| E5-02 | Como sistema, recibo respuestas de email por webhook y las asocio al pagador, factura y adjuntos | M | M |
| E5-03 | Como sistema, envío mensajes de WhatsApp con plantillas aprobadas | M | M |
| E5-04 | Como sistema, recibo respuestas de WhatsApp por webhook y las asocio al hilo correcto | M | M |
| E5-05 | Como sistema, registro estado de entrega/lectura cuando el canal lo permita | S | S |
| E5-06 | Como contacto, puedo solicitar no ser contactado por un canal (opt-out) y se respeta | M | S |
| E5-07 | Como operador, uso WhatsApp en modo asistido (texto + link) cuando la API no está disponible o no hay plantilla aprobada | M | XS |
| E5-08 | SMS como canal adicional | C | S |
| E5-10 | Como operador, registro una respuesta recibida por otro medio y entra al mismo flujo de clasificación | M | S |

---

## Épica 6 — Agente IA

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E6-01 | Como sistema, el agente redacta mensajes según etapa, destinatario (cuentas por pagar, solicitante, pyme), tono y lo que falta en el checklist | M | M |
| E6-02 | Como sistema, el agente clasifica cada respuesta en: ya pagué · en programación de pago · falta OC/HES · proveedor no registrado o datos incorrectos · factura reclamada/rechazada · promesa de pago · disputa · solicitud de documento · contacto equivocado · otro | M | M |
| E6-03 | Como sistema, extraigo datos de la respuesta y sus adjuntos (fecha de pago, monto, N° de OC/HES, comprobante) y actualizo el checklist | M | M |
| E6-04 | Como sistema, si la confianza de la clasificación es baja, se deriva a excepción | M | S |
| E6-05 | Como sistema, el agente propone acuerdos de pago solo dentro de los límites del contrato | S | M |
| E6-06 | Como sistema, respondo automáticamente solicitudes de documento disponibles (factura PDF, OC, HES ya obtenida) | S | S |
| E6-07 | Como equipo, mantengo un set de evaluación con respuestas reales anonimizadas y mido precisión por categoría | M | M |
| E6-08 | Como sistema, aplico reglas de seguridad: el agente nunca amenaza, no promete fuera del contrato, no inventa montos ni documentos; si la validación falla, uso plantilla de respaldo | M | S |
| E6-09 | Como operador, activo por categoría el modo de clasificación: revisión manual o acción automática | M | S |

**Criterios de aceptación E6-02 / E6-09:** una categoría solo pasa a acción automática con precisión ≥90% en el set de evaluación; mientras tanto, sus clasificaciones quedan en revisión del operador. El sistema muestra la precisión vigente por categoría.

---

## Épica 7 — Bandeja de excepciones (operador humano)

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E7-01 | Como operador, veo una cola de excepciones priorizada por monto, riesgo de pagabilidad y antigüedad | M | M |
| E7-02 | Como operador, veo el historial completo de la factura, su checklist y la ficha del pagador al abrir una excepción | M | S |
| E7-03 | Como operador, respondo, corrijo la clasificación, actualizo el checklist o reasigno la etapa desde la bandeja | M | M |
| E7-04 | Como operador, escalo un caso a la pyme cliente con una nota | M | S |
| E7-05 | Como sistema, registro el tiempo que el operador dedica a cada excepción | M | S |
| E7-06 | Como sistema, las correcciones del operador alimentan el set de evaluación | M | S |

---

## Épica 8 — Pagos y conciliación

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E8-01 | Como sistema, incluyo en los mensajes de pago los datos de transferencia del cliente | M | XS |
| E8-02 | Como operador, registro un pago manualmente con evidencia (comprobante) | M | S |
| E8-03 | Como operador, importo la cartola bancaria del cliente (Excel/CSV) | M | M |
| E8-04 | Como sistema, propongo coincidencias entre movimientos de cartola y facturas (RUT, monto, fecha) | M | M |
| E8-05 | Como operador, confirmo o rechazo las coincidencias propuestas | M | S |
| E8-06 | Como sistema, genero un link de pago por factura | W | M |
| E8-07 | Conexión automática a la cuenta bancaria del cliente | W | L |
| E8-08 | Como sistema, autoconfirmo coincidencias por sobre un umbral configurable | W | S |

**Criterios de aceptación E8-04 / E8-05:** la coincidencia considera RUT, monto (por factura o suma de facturas del mismo pagador) y ventana de fechas; cada propuesta muestra su puntaje; al confirmarse queda en la bitácora con su origen (manual o cartola); un pago nunca se cuenta dos veces.

---

## Épica 9 — Verificación de resultados y comisión

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E9-01 | Como sistema, marco un pago como **verificado** solo con conciliación y evidencia | M | S |
| E9-02 | Como sistema, aplico las reglas de atribución del contrato: pago a tiempo tras gestión documental/preventiva o recuperación en mora, cada uno con su % | M | M |
| E9-03 | Como operador, genero el resumen mensual de comisión por cliente con detalle por factura, exportable | M | S |
| E9-04 | Como cliente, puedo objetar un resultado y queda registrado para revisión | S | S |

---

## Épica 10 — Vista y reporte para la pyme

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E10-01 | Como cliente, recibo un reporte semanal por email: facturas pagables, en riesgo, pagadas, pendientes de mi parte, disputas | M | M |
| E10-02 | Como cliente, accedo a una vista web de solo lectura con el estado y checklist de cada factura y lo pagado | M | M |
| E10-03 | Como cliente, subo desde la vista web los documentos que se me solicitan (OC, guía, certificado) y se incorporan al checklist | M | S |
| E10-04 | Como cliente, apruebo o respondo excepciones escaladas desde la vista web | S | M |
| E10-05 | Como cliente, veo la evolución del DSO y del % pagado a tiempo | S | M |

---

## Épica 11 — Unit economics y métricas del piloto

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E11-01 | Como sistema, registro el costo de LLM y de mensajería por factura | M | S |
| E11-02 | Como equipo, veo por cliente: facturas gestionadas, % pagado a tiempo, monto recuperado, % sin intervención humana, minutos humanos, costo por factura, margen | M | M |
| E11-03 | Como equipo, veo la línea base de DSO y de % pagado a tiempo antes del piloto y su evolución | M | S |
| E11-04 | Como equipo, exporto las métricas del piloto para la postulación (CSV) | M | XS |
| E11-05 | Como equipo, veo la proporción automático/manual en envíos, clasificaciones y conciliaciones | M | S |
| E11-06 | Como sistema, registro la **causa de atraso** de cada factura atrasada (documental: aceptación/OC/HES/portal/datos · liquidez del pagador · disputa comercial · otra) y la muestro agregada | M | S |
| E11-07 | Como equipo, veo el tiempo promedio de resolución de cada tipo de problema documental | M | S |

**Por qué E11-06 es crítica:** es la evidencia de la hipótesis central de innovación ("una parte relevante de los atrasos es documental"). Sin este dato, la postulación pierde su principal argumento.

---

## Épica 12 — Seguridad, cumplimiento y auditoría

| ID | Historia | Prioridad | Est. |
|---|---|---|---|
| E12-01 | Autenticación de operadores y clientes con roles (operador, admin, cliente) | M | M |
| E12-02 | Cifrado en tránsito (HTTPS) y en reposo para datos y documentos sensibles | M | S |
| E12-03 | Registro de accesos a datos por usuario | M | S |
| E12-04 | Política de retención y borrado de datos por cliente | S | S |
| E12-05 | Registro de actividades de tratamiento (Ley 21.719) | S | S |
| E12-06 | Datos anonimizados para el set de evaluación de IA | M | S |

---

## Épica 13 — Futuro (después del piloto)

| ID | Historia | Prioridad |
|---|---|---|
| E13-01 | Predicción de fecha de pago por pagador (requiere volumen y revisión legal) | W |
| E13-02 | Optimización automática de canal y momento de contacto | W |
| E13-03 | Integraciones con ERP y software contable locales | W |
| E13-04 | Onboarding autoservicio | W |
| E13-05 | Adaptador de facturación electrónica y fichas de pagadores para un segundo país | W |
| E13-06 | Migración de flujos a ejecución durable (Temporal) | W |
| E13-07 | Alianza para derivar a cobranza extrajudicial los casos que superan el alcance del servicio | W |

---

## Tareas de validación en paralelo (no son desarrollo)

| ID | Tarea | Cuándo |
|---|---|---|
| V-01 | Guion de entrevista a dueños/gerentes de finanzas de pymes que le facturan a grandes empresas, con foco en causas de atraso | Semana 1 |
| V-02 | Realizar 10–15 entrevistas y cuantificar: plazo real de pago, causas de atraso (documental vs. liquidez vs. disputa), herramientas actuales (Xepelin, Moonflow, Faaro, factoring) | Semanas 1–6 |
| V-03 | **Análisis retrospectivo** con 2–3 pymes: clasificar por causa las facturas atrasadas del último año | Semanas 2–5 |
| V-04 | Entrevistar a 3–5 personas de cuentas por pagar o de gestión de proveedores de grandes empresas: requisitos, portales y por qué se retienen facturas | Semanas 2–6 |
| V-05 | Consulta legal: alcance de la gestión B2B, ficha compartida de pagadores, uso de credenciales de portales y protección de datos | **Antes de contactar a pagadores reales** |
| V-06 | Contrato de servicio piloto (mandato de gestión, comisión por etapa, datos, garantías, autorización para portales) | Antes del piloto |
| V-07 | Obtener 2–3 pymes piloto con carta de intención, idealmente con pagadores en común | Semanas 1–8 |
| V-08 | Iniciar verificación de WhatsApp Business con Meta y configurar dominio de email | Semana 1 |
| V-09 | Operar el piloto durante 6–8 semanas | Desde el fin de S6 |
| V-10 | Informe de resultados del piloto (insumo directo para la postulación) | Al cierre del piloto |

**V-03 es la validación más barata y rápida de la hipótesis central:** no requiere desarrollo y puede confirmar o descartar el enfoque antes de construir la Épica P completa.

---

## Plan de sprints (2 semanas)

| Sprint | Foco | Historias |
|---|---|---|
| **S1** | Plataforma y base | E0-01 a E0-04, E0-07, E1-01 a E1-04, E12-01, E3-01 a E3-04 |
| **S2** | Contrato y motor | E2-01 a E2-05, E4-01 a E4-09 |
| **S3** | Pagabilidad | EP-01 a EP-08, E11-06 |
| **S4** | Comunicación | E5-01 a E5-04, E5-06, E5-07, E5-10, E8-01, E6-01, E6-08, E11-01 |
| **S5** | IA y excepciones | E6-02 a E6-04, E6-07, E6-09, EP-09, E7-01 a E7-06, E12-06 |
| **S6** | Pagos, resultados y despliegue | E8-02 a E8-05, E9-01 a E9-03, E0-05, E0-06, E12-02, E12-03 |
| — | **Inicio del piloto** con la primera pyme (semana 12) | V-09 |
| **S7** | Vista cliente y métricas (con el piloto corriendo) | E10-01 a E10-03, E11-02 a E11-05, E11-07, E0-08 |
| **S8** | Ajustes del piloto y pulido para mostrar | Correcciones según el piloto, E2-06, E5-05, E6-05, E6-06, EP-10, E10-04, E10-05 |

El resultado de V-03 (semana 5) llega antes de cerrar S3: si la hipótesis documental no se confirma, la Épica P se reduce a lo esencial y el piloto se adelanta un sprint.

---

## Criterio de éxito del MVP piloto

- 2–3 pymes operadas en producción durante al menos 6 semanas.
- Todo lo listado en "Qué significa sólido para mostrar" funcionando.
- Datos medidos: distribución de causas de atraso, % pagado a tiempo vs. línea base, monto recuperado, % de facturas sin intervención humana, minutos humanos y costo por factura, precisión de la clasificación IA, margen.
- Fichas completas de los principales pagadores del piloto.
- Decisión documentada: qué hipótesis se confirmaron, cuáles no y qué cambia después del piloto.

---

## Notas para desarrollar en Claude Code

- Partir el repositorio con un `CLAUDE.md` que resuma la visión, este backlog, las reglas de seguridad del agente (sección 5 de la visión: lo que la IA **no** hace) y estas reglas técnicas:
  - **PostgreSQL en Docker siempre; nunca SQLite**, tampoco en tests.
  - Todo cambio de esquema mediante migración Alembic.
  - Todo se levanta con `docker compose`.
  - Credenciales solo en variables de entorno.
  - La ficha del pagador es global; todo lo demás está aislado por cliente.
  - Las operaciones con doble modo dejan el mismo rastro de auditoría, con el modo registrado en cada evento.
- Seguir el orden de los sprints; dentro de cada sprint, cerrar una historia completa (backend, interfaz, tests) antes de pasar a la siguiente.
- Pedir tests desde el inicio para las reglas críticas: cálculo de etapa, generación del checklist, horario y frecuencia, idempotencia del worker, validación de RUT, aislamiento entre clientes (incluida la ficha compartida), reglas de atribución y cálculo de comisión.

---

## Definición de "Hecho"

- Criterios de aceptación cumplidos y probados con datos realistas.
- Migración Alembic incluida si hay cambios de esquema.
- Funciona levantando el sistema con `docker compose`.
- Tests automáticos pasando contra PostgreSQL en contenedor.
- Eventos de auditoría registrados para la funcionalidad.
- Sin datos de un cliente visibles para otro (probado).
- Costos de LLM y mensajería registrados si aplica.
- Documentado en el README o en notas de la épica.
