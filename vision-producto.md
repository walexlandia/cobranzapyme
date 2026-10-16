# Visión de Producto — Facturas pagables y pagadas a tiempo para pymes, operado por IA

> Nombre de trabajo: **Recupera** (provisional, disponibilidad de marca no verificada)
> Versión: 0.4 · Octubre 2026 · Documento vivo
> Cambio v0.4: tras el análisis de mercado, el foco pasa de "cobranza" a **asegurar que cada factura sea pagable y se pague a tiempo**, desde su emisión. Se agregan el mapa de competencia, los referentes y la nueva hipótesis central.

---

## 1. Visión en una frase

**Que ninguna pyme espere su pago por un papel que faltaba o por una factura que nadie siguió.**

Recupera se hace cargo, en nombre de la pyme, de que cada factura emitida a otra empresa **cumpla lo que el pagador exige para pagarla** (aceptación en el SII, orden de compra, hoja de entrada de servicios, registro en el portal de proveedores) y **se pague a tiempo**, con seguimiento desde la emisión hasta el pago y su conciliación. Un agente de IA hace el trabajo; una persona interviene solo en los casos complejos. La pyme no opera una herramienta: recibe el resultado y paga por él.

---

## 2. El problema

- Las pymes que venden a empresas medianas y grandes esperan su pago mucho más de lo pactado, aunque exista la Ley de pago a 30 días.
- **Hipótesis central:** una parte importante de esos atrasos no se debe a falta de voluntad o liquidez del pagador, sino a que la factura **no es pagable** para su área de cuentas por pagar:
  - la factura no fue aceptada o fue reclamada en el SII;
  - falta la orden de compra (OC) o la hoja de entrada de servicios (HES) / conformidad;
  - el proveedor no está registrado, o sus datos no calzan, en el portal de proveedores del cliente;
  - la factura no se cargó donde corresponde o con los datos que el pagador exige.
- Nadie en la pyme tiene esto como trabajo principal. El problema se descubre tarde, cuando la factura ya está vencida.
- Las alternativas actuales no resuelven esta etapa:
  - **Software de cobranza** (Xepelin, Cuadra, Chipax, Bemmbo, Clay, Moonflow): recuerda fechas o conversa por WhatsApp, pero la pyme debe operarlo y nadie persigue la HES ni el portal.
  - **Cobranza por éxito para pymes** (Faaro, ex CobranzaOnline): actúa cuando la factura ya es deuda, con presión extrajudicial y publicación en boletines, lo que tensiona la relación comercial.
  - **Factoring**: adelanta la caja con costo financiero, pero no destraba la factura.

**El dolor es crítico:** la falta de caja es una de las principales causas de cierre de pymes, y el atraso de un gran cliente puede comprometer sueldos y proveedores.

---

## 3. Cliente objetivo

### Segmento inicial (beachhead)
Pymes chilenas B2B que:
- **Le facturan a empresas medianas y grandes** con procesos formales de pago (OC, HES, portales de proveedores).
- Emiten entre ~20 y ~300 facturas al mes.
- No tienen un área de cobranza ni de gestión de cuentas por cobrar.

Rubros prioritarios a validar: proveedores y contratistas de minería, construcción, industria, energía y retail; servicios profesionales y técnicos a grandes empresas.

### Usuario y comprador
- **Comprador**: dueño, gerente general o gerente de administración y finanzas.
- **Usuario ocasional**: administrativo o contador, que aporta documentos y aprueba excepciones.

### Fuera del segmento (explícito)
- **Cobranza a personas naturales / consumidores.** El servicio es exclusivamente B2B.
- Cobranza judicial y publicación en boletines comerciales.
- Grandes empresas con área propia de cuentas por cobrar.

---

## 4. Propuesta de valor

| Para la pyme | Cómo |
|---|---|
| **Facturas pagables desde el día 1** | Revisión de aceptación en el SII y de los requisitos documentales del pagador desde la emisión |
| **Problemas detectados antes del vencimiento** | OC, HES y portal resueltos a tiempo, no cuando ya hay mora |
| **Pago a tiempo** | Seguimiento con cuentas por pagar del cliente hasta el pago y su conciliación |
| **Cero trabajo operativo** | El servicio ejecuta; la pyme solo aporta documentos y aprueba excepciones |
| **Cuida la relación comercial** | Gestión documental y cordial, no presión de cobranza |
| **Paga por resultado** | Activación baja + porcentaje sobre pagos verificados de facturas gestionadas |

---

## 5. Cómo funciona

```
Facturas emitidas (Registro de Compras y Ventas del SII / Excel)
        │
        ▼
 ┌──────────────────┐
 │ Contrato de      │  Reglas de la pyme: tono, canales, límites,
 │ resultado        │  escalamiento, comisión, garantías
 └────────┬─────────┘
          ▼
 ┌──────────────────┐     ┌──────────────────────┐
 │ Revisión de      │◀────│ Ficha del pagador    │  Requisitos, portal, contactos de
 │ pagabilidad      │     │ (conocimiento        │  cuentas por pagar, día de pago,
 │ SII · OC · HES · │     │  compartido)         │  plazo real observado
 │ portal           │────▶│                      │
 └────────┬─────────┘     └──────────────────────┘
          ▼
 ┌──────────────────┐
 │ Motor de flujos  │  Emisión → documental → preventiva →
 │                  │  vencimiento → mora temprana → escalamiento
 └────────┬─────────┘
          ▼
 ┌──────────────────┐     ┌──────────────────┐
 │ Agente IA        │────▶│ Bandeja humana   │  Rechazos, disputas, montos altos,
 │ redacta, envía,  │     │ de excepciones   │  casos ambiguos, cargas en portales
 │ clasifica        │◀────│                  │
 └────────┬─────────┘     └──────────────────┘
          ▼
 ┌──────────────────┐
 │ Pago y           │  Comprobante manual y coincidencias
 │ conciliación     │  contra la cartola
 └────────┬─────────┘
          ▼
 ┌──────────────────┐
 │ Verificación y   │  Pago verificado → resultado aceptado →
 │ comisión         │  cálculo de comisión
 └──────────────────┘
```

### Etapas de cada factura
1. **Emisión** (día 0): se registra la factura y se identifica al pagador y su ficha.
2. **Documental** (días 1–10): se verifica la aceptación en el SII dentro del plazo legal de reclamo y se completan los requisitos del pagador (OC, HES/conformidad, carga en portal). Si falta algo, se solicita a quien corresponde: el solicitante del servicio en el cliente para la HES, la pyme para documentos propios.
3. **Preventiva** (antes del vencimiento): confirmación con cuentas por pagar de que la factura está aprobada y en programación de pago.
4. **Vencimiento**: recordatorio con datos de pago.
5. **Mora temprana** (1–30 días): seguimiento multicanal, detección de disputas, acuerdos dentro de los límites del contrato.
6. **Escalamiento** (>30 días o reglas del contrato): a operador humano y a la pyme. La cobranza extrajudicial o judicial queda fuera del servicio.

### Lo que hace la IA
- Identificar qué le falta a cada factura para ser pagable, según la ficha del pagador.
- Redactar solicitudes y seguimientos según etapa, destinatario y tono.
- Clasificar respuestas: ya pagué · en programación de pago · falta OC/HES · proveedor no registrado · factura reclamada o rechazada · promesa de pago · disputa · solicitud de documento · contacto equivocado · otro.
- Proponer acuerdos de pago **solo dentro de las reglas aprobadas por la pyme**.
- Actualizar la ficha del pagador con lo aprendido en cada caso.

### Lo que NO hace la IA
- No negocia fuera de los límites del contrato.
- No amenaza ni usa lenguaje coercitivo.
- No resuelve disputas comerciales: las escala.
- No promete nada en nombre de la pyme que no esté autorizado.
- No ingresa a portales de proveedores con credenciales de la pyme sin autorización explícita (en el piloto, las cargas en portales las hace el operador).

### Modo manual y modo automático, donde agrega valor
El doble modo se usa solo donde resuelve un problema real: envíos por WhatsApp (mientras se aprueba la API), registro de respuestas que llegan por teléfono, clasificación de respuestas (revisión humana hasta que cada categoría demuestre precisión) y conciliación de pagos (comprobante manual y cartola). La proporción automático/manual se mide como indicador de escalabilidad.

---

## 6. Principios de producto

1. **Vendemos resultados, no pantallas.** Cada funcionalidad se justifica por su impacto en facturas pagadas a tiempo o en costo por resultado.
2. **Prevenir antes que cobrar.** El mejor cobro es el que no hace falta porque la factura se pagó a tiempo.
3. **El contrato de resultado es el corazón.** Todo comportamiento deriva de un contrato configurable y auditable.
4. **Cada caso enseña.** Lo aprendido de un pagador sirve a todas las pymes que le facturan.
5. **Humano solo donde agrega valor.** Maximizar el % de facturas resueltas sin intervención humana, sin sacrificar calidad.
6. **Evidencia de todo.** Cada mensaje, documento, pago y decisión queda registrado y es auditable.
7. **Cuidar la relación comercial de la pyme.**
8. **Margen que escala.** Si para crecer 10x necesitamos 10x personas, el diseño está mal.

---

## 7. Mercado y competencia

### Mapa de alternativas

| Categoría | Ejemplos | Qué hacen | Qué no resuelven |
|---|---|---|---|
| Software de cobranza para pymes (Chile) | Xepelin, Cuadra, Chipax, Bemmbo, Clay, Moonflow | Recordatorios automáticos, conciliación; Moonflow con agente IA por WhatsApp y correo. Cuota mensual fija (Xepelin gratis, financiado por factoring) | La pyme debe operarlo; no persiguen OC, HES ni portales; no cobran por resultado |
| Cobranza por éxito para pymes (Chile) | Faaro (ex CobranzaOnline), Duemint | Cobranza extrajudicial de facturas vencidas, publicación en boletines, convenios. Solo cobran si recuperan | Llegan tarde, con presión; tensionan la relación comercial |
| Cobranza con IA en Latinoamérica | Kleva (México), Mozart (Uruguay), startup colombiana en Y Combinator | Agentes de IA que negocian y cobran por voz, WhatsApp, SMS y correo | Deuda de consumidores para bancos, fintechs y retail; no facturas B2B de pymes |
| Factoring | Diversas fintech y bancos | Adelantan el pago con costo financiero | No destraban la factura ni mejoran el plazo real |
| Agencias y abogados | Diversas | Cobranza humana de montos altos | Costo humano por caso; no tocan facturas pequeñas ni la etapa preventiva |

### Referente internacional: Stuut (EE.UU.)
En octubre de 2026 levantó una Serie B de US$52,5 millones liderada por Insight Partners, que lo describe como una capa de ejecución de cuentas por cobrar con IA. Declara más de 150 clientes, un 81,7% de la cobranza saliente sin intervención humana, un 95% de pagos conciliados automáticamente y reducciones de DSO de hasta 47% (cifras declaradas por la empresa).

**Qué valida:** que el modelo "la IA ejecuta el trabajo, no solo lo gestiona" atrae capital de primer nivel.
**Diferencia clave:** Stuut trabaja para la **gran empresa que cobra**, conectada a su ERP. Recupera trabaja para la **pyme que le cobra a la gran empresa**: el lado opuesto de la misma transacción, justo donde la factura se traba (cuentas por pagar del pagador).

### Dónde está la innovación
- **Etapa no atendida:** la pagabilidad de la factura entre la emisión y el vencimiento. El software recuerda fechas; las agencias llegan tarde.
- **Modelo:** servicio operado por IA con pago por resultado, en una etapa donde hoy nadie cobra por resultado.
- **Efecto red:** muchas pymes le facturan a los mismos grandes pagadores. La ficha de cada pagador (requisitos, portal, contactos, plazo real) mejora con cada caso y beneficia a todos los clientes. Es un activo que crece con la escala y que un competidor nuevo no tiene.
- **Especialización local:** SII, aceptación de facturas, Ley de pago a 30 días, HES y portales de proveedores chilenos, WhatsApp y comisión por resultado. Una plataforma enterprise extranjera no trae nada de eso.

### Riesgos competitivos
- Moonflow o Xepelin podrían agregar seguimiento documental; Faaro podría adelantar su intervención. Respuesta: velocidad, especialización en pagabilidad y la ficha de pagadores como activo acumulado.
- Stuut u otro actor internacional podría bajar al segmento pyme o entrar a la región. Respuesta: especialización local y relación con la red de pagadores.

---

## 8. Modelo de negocio

- **Fee de activación mensual bajo** por empresa: cubre onboarding y operación base, filtra clientes no comprometidos.
- **Comisión por pago verificado** de facturas gestionadas, diferenciada por etapa:
  - % menor para facturas pagadas a tiempo tras gestión documental o preventiva;
  - % mayor para facturas recuperadas en mora temprana.
- **Garantía**: errores atribuibles al servicio se corrigen sin costo.

La regla de atribución (qué pagos se habrían producido igual) se define y prueba en el piloto, comparando contra el DSO y el comportamiento previo de cada pagador.

### Unit economics a medir desde el piloto
- Costo tecnológico y minutos humanos por factura.
- % de facturas resueltas sin intervención humana.
- % de facturas con problema documental y tiempo de resolución.
- Monto pagado a tiempo y monto recuperado / monto gestionado.
- DSO antes vs. después.
- Margen por cliente.

---

## 9. Métricas de éxito

**North Star:** Monto de facturas pagadas a tiempo o recuperadas, verificado, por mes.

| Métrica | Meta piloto (hipótesis) |
|---|---|
| % de facturas con problema documental detectado antes del vencimiento | Línea base a establecer |
| % de facturas pagadas dentro del plazo pactado | +20 puntos vs. línea base |
| Reducción del DSO en cartera gestionada | ≥ 20% |
| % facturas resueltas sin intervención humana | ≥ 70% |
| Quejas de pagadores por tono | 0 escaladas |
| Margen operativo por cliente | Positivo incluyendo costo humano |

---

## 10. Hoja de ruta

| Fase | Objetivo | Resultado esperado |
|---|---|---|
| **1. MVP piloto** (~16 semanas de desarrollo; piloto desde la semana 12) | Construir con Claude Code un producto sólido, desplegado y demostrable, y operarlo con 2–3 pymes reales. En paralelo: entrevistas a pymes y a áreas de cuentas por pagar, revisión legal y aprobación de WhatsApp Business | Producto en producción; fichas de los principales pagadores; datos reales de causas de atraso, pago a tiempo, % sin intervención humana y costo por factura |
| **2. Build / Producto** (3–6 meses) | Escalar a 10–20 clientes con equipo pequeño | Integración con el SII, carga asistida en portales de proveedores, conciliación automática, red de fichas de pagadores |
| **3. Expansión** | Segundo país con facturación electrónica obligatoria (México, Colombia o Perú) | Adaptadores por país y fichas de pagadores regionales |

---

## 11. Hipótesis críticas a validar

1. **Una proporción relevante de los atrasos se explica por problemas documentales** (aceptación, OC, HES, portal) y no por liquidez del pagador. *Es la hipótesis que sostiene la innovación.*
2. Los grandes pagadores se repiten entre pymes, de modo que la ficha del pagador genera efecto red.
3. Las pymes aceptan que un tercero gestione con sus clientes en su nombre.
4. La gestión desde la emisión aumenta el % de facturas pagadas a tiempo de forma medible.
5. ≥70% de las facturas se pueden gestionar sin intervención humana.
6. Las pymes pagan una comisión por pago a tiempo (no solo por recuperar mora).
7. Las áreas de cuentas por pagar y los solicitantes responden a un gestor externo que actúa por la pyme.

---

## 12. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| La hipótesis documental no se confirma | Medirla en las primeras entrevistas; si es baja, el producto queda como cobranza temprana operada por IA |
| Regulatorio (cobranza extrajudicial) | Solo B2B; enfoque documental y preventivo; validar alcance con abogado antes del piloto |
| Protección de datos (Ley 21.719) | Minimización de datos, base legal en el contrato con la pyme, opt-out, registro de tratamientos |
| Ficha compartida de pagadores | Solo información operativa de empresas (requisitos, canales, plazos), sin datos personales sensibles ni datos de una pyme visibles para otra; validación legal |
| Acceso a portales de proveedores | En el piloto, cargas hechas por el operador con autorización de la pyme; automatización solo con autorización explícita y almacenamiento seguro de credenciales |
| Daño a la relación comercial | Tono configurable, aprobación de plantillas, escalamiento de disputas |
| Atribución del resultado | Reglas explícitas en el contrato y comparación contra línea base |
| Caja del modelo por resultado | Fee de activación + ciclo corto de la gestión preventiva |
| Competencia | Ver sección 7 |

---

## 13. Ángulo para fondos (Start-Up Chile Build / Semilla Inicia)

- **Problema:** las pymes financian a las grandes empresas con plazos reales de pago muy superiores a lo pactado, en gran parte por facturas que no son pagables a tiempo.
- **Innovación:** servicio operado por IA que asegura la pagabilidad de la factura desde la emisión, con pago por resultado y una base de conocimiento de pagadores que mejora con cada caso. Hoy no existe en Chile: el software recuerda fechas y la cobranza por éxito llega tarde.
- **Base tecnológica:** motor de contratos de resultado ejecutables, agente de revisión documental y clasificación, ficha de pagadores y conciliación.
- **Validación internacional del modelo:** Stuut (US$52,5M, Insight Partners) en el lado de las grandes empresas.
- **Escalabilidad internacional:** México, Colombia, Perú y Brasil tienen facturación electrónica obligatoria y grandes pagadores con procesos similares (a validar país por país).
- **Impacto:** liquidez para pymes y cumplimiento efectivo de los plazos de pago.
- **En la postulación:** nombrar a Faaro, Moonflow y Xepelin y explicar la diferencia; los evaluadores los conocen.
