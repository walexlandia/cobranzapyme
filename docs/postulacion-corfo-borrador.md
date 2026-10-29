# Borrador de postulación CORFO — Recupera

> Versión de trabajo: 29 de octubre de 2026.
>
> Estado recomendado de la solución: **Prototipo/PMV**.
>
> Este documento se preparó desde la evidencia interna del proyecto. Los campos `[POR COMPLETAR]` requieren información del postulante o validación externa. Las pruebas con datos sintéticos demuestran funcionamiento técnico, no ventas, pilotos reales ni impacto comercial.

## 1. Introducción

### Nombre del proyecto

**Recupera — Facturas pagables y pagadas a tiempo para pymes, operado por IA.**

El nombre “Recupera” es provisional. Antes de postular o invertir en marca se debe verificar su disponibilidad legal, comercial y de dominio.

### Resumen ejecutivo

Las pymes chilenas que venden a empresas medianas y grandes suelen enfrentar atrasos de pago que afectan su liquidez y capacidad de cumplir con remuneraciones, proveedores y crecimiento. Una parte de este problema comienza antes del vencimiento: la factura no está en condiciones de ser pagada porque falta una orden de compra, una hoja de entrada de servicios o conformidad, una aceptación, un registro en el portal del proveedor o una coordinación con cuentas por pagar. Como estas tareas no suelen tener un responsable dedicado dentro de la pyme, la dificultad se detecta cuando la factura ya venció.

Recupera es un servicio tecnológico B2B que acompaña cada factura desde su emisión hasta el pago y la conciliación. La solución organiza los requisitos del pagador, controla la pagabilidad, prepara seguimientos según la etapa de la factura, identifica respuestas y excepciones, mantiene trazabilidad de documentos y pagos y deriva a una persona los casos sensibles. Su diseño combina automatización con aprobación humana: la IA no negocia fuera de reglas autorizadas, no resuelve disputas comerciales y no ejecuta acciones irreversibles sin control.

El segmento inicial son pymes chilenas B2B que emiten aproximadamente entre 20 y 300 facturas mensuales a empresas con procesos formales de pago y que no cuentan con un área propia de cuentas por cobrar. Los rubros iniciales por validar son servicios técnicos y profesionales, minería, construcción, industria, energía y retail. El comprador esperado es el dueño, gerente general o responsable de administración y finanzas; el usuario operativo ocasional es el administrativo o contador que entrega documentos y aprueba excepciones.

La propuesta se diferencia de un software de cobranza tradicional, una agencia de cobranza o el factoring. Recupera no se limita a recordar vencimientos, no espera a que la deuda esté morosa y no adelanta dinero con costo financiero. Su foco es resolver preventivamente aquello que impide pagar la factura, operar el seguimiento bajo reglas contractuales y vincular cualquier comisión a pagos efectivamente verificados. Además, cada caso alimenta una ficha operativa del pagador —requisitos, canales, plazos y aprendizajes— que puede mejorar la operación para nuevas pymes sin compartir datos privados entre ellas.

El producto se encuentra en estado de prototipo/PMV funcional. El repositorio incluye un portal multiempresa, contratos y reglas versionadas, gestión de facturas y requisitos documentales, seguimiento asistido, conciliación supervisada, carga cifrada de evidencia, métricas, auditoría y reportes reproducibles. La validación local registra 79 pruebas backend sobre PostgreSQL, 35 comprobaciones offline y build web aprobado. Los experimentos PM-1, PM-2 y PM-3 usan datos sintéticos para validar medición de trabajo humano, optimización guiada y trazabilidad de atribución. Todavía no existen pilotos reales autorizados, ventas verificadas ni una decisión de escala; esas validaciones son parte central del proyecto a financiar.

El modelo de negocio propuesto combina un fee de activación u operación base con una comisión sobre pagos verificados de facturas gestionadas. La estrategia inicial es realizar pilotos controlados con 2 o 3 pymes, medir pago oportuno, DSO, causas documentales, minutos humanos y margen, y luego avanzar hacia 10 a 20 clientes con una operación pequeña. El tamaño TAM/SAM/SOM debe cuantificarse con fuentes oficiales y entrevistas antes del envío definitivo; no se incorpora una cifra no verificada en este borrador.

### Ubicación de ejecución e impacto

- **Región de ejecución:** `[POR COMPLETAR]`.
- **Comuna de ejecución:** `[POR COMPLETAR]`.
- **Región inicial de impacto:** `[POR COMPLETAR; sugerencia: región donde se ejecutarán los primeros pilotos]`.
- **Expansión prevista:** cobertura nacional en Chile después de validar el segmento inicial; una eventual expansión a otro país latinoamericano con facturación electrónica obligatoria está condicionada a evidencia de producto y negocio.

Texto sugerido una vez confirmada la ubicación:

> El proyecto se ejecutará inicialmente en la comuna de `[COMUNA]`, Región de `[REGIÓN]`. Desde esta base se validará con pymes B2B de la región y con empresas que facturan a pagadores medianos y grandes. Al ser una solución digital, el impacto comercial puede extenderse posteriormente a otras regiones de Chile sin requerir presencia física permanente en cada territorio.

### Clasificación económica

- **Sector de la solución propuesto:** Tecnologías de la Información y Comunicaciones / servicios de software para gestión empresarial.
- **Subsector propuesto:** automatización y asistencia inteligente para cuentas por cobrar, pagabilidad y conciliación B2B.
- **Sector de clientes:** pymes proveedoras B2B, inicialmente en servicios profesionales y técnicos, minería, construcción, industria, energía y retail.
- **Código o categoría exacta del formulario CORFO:** `[POR VALIDAR EN EL LISTADO DE LA CONVOCATORIA]`.

### Presencia en plataformas web

- Sitio web: `[POR COMPLETAR O INDICAR “NO DISPONIBLE AÚN”]`.
- LinkedIn del proyecto o empresa: `[POR COMPLETAR]`.
- Instagram: `[POR COMPLETAR O “NO APLICA”]`.
- Facebook: `[POR COMPLETAR O “NO APLICA”]`.
- Repositorio: `https://github.com/walexlandia/cobranzapyme` — confirmar si será público y conveniente incluirlo en la postulación.

No crear perfiles vacíos únicamente para llenar este apartado. Es preferible declarar que todavía no existen y presentar un sitio o perfil consistente antes del envío.

### Objetivo de Desarrollo Sostenible

**ODS principal propuesto: ODS 8 — Trabajo decente y crecimiento económico.**

Recupera busca mejorar la liquidez y estabilidad operativa de pymes proveedoras mediante pagos más oportunos y menor carga administrativa. Una gestión preventiva de facturas puede ayudar a que las pymes dediquen menos horas a perseguir documentos y pagos, y más recursos a empleo, operación e inversión. El impacto deberá medirse en el piloto mediante DSO, pago oportuno, minutos humanos y costos por factura.

**ODS secundario posible:** ODS 9 — Industria, innovación e infraestructura, por la digitalización y automatización responsable de un proceso empresarial fragmentado.

## 2. Antecedentes generales

### Tipo de postulante

`[POR COMPLETAR: PERSONA NATURAL / PERSONA JURÍDICA]`.

La selección debe coincidir con las bases de la convocatoria, la titularidad del proyecto y la capacidad de firmar convenios. No se puede inferir desde el repositorio.

### Datos del postulante — Persona Natural

- Nombre completo: `[POR COMPLETAR]`.
- RUT o identificación: `[POR COMPLETAR]`.
- Género: `[POR COMPLETAR]`.
- Fecha de nacimiento: `[POR COMPLETAR]`.
- Nacionalidad: `[POR COMPLETAR]`.
- Cédula de identidad: `[ADJUNTAR EN LA PLATAFORMA; NO GUARDAR EN GIT]`.
- Dirección completa: `[POR COMPLETAR; NO GUARDAR EN GIT]`.
- Correo electrónico: `[POR COMPLETAR]`.
- Teléfono: `[POR COMPLETAR]`.
- LinkedIn: `[POR COMPLETAR]`.

### Datos de la empresa — Persona Jurídica

- RUT empresa: `[POR COMPLETAR]`.
- Razón social: `[POR COMPLETAR]`.
- Dirección: `[POR COMPLETAR; NO GUARDAR EN GIT]`.
- Teléfono: `[POR COMPLETAR]`.
- Correo empresarial: `[POR COMPLETAR]`.
- Representante legal, RUT, cargo y datos de contacto: `[POR COMPLETAR; NO GUARDAR EN GIT]`.
- Documento que acredita personería: `[ADJUNTAR EN LA PLATAFORMA; NO GUARDAR EN GIT]`.

### Empresa liderada por mujeres

`[POR COMPLETAR SEGÚN CAPITAL SOCIAL, ADMINISTRACIÓN Y REPRESENTACIÓN LEGAL]`.

No declarar este beneficio sin revisar la definición y los documentos exigidos por la convocatoria específica.

### Autorizaciones formales

`[DEBE ACEPTARLAS EL POSTULANTE EN LA PLATAFORMA]`.

Antes de aceptar, revisar el alcance del consentimiento de seguimiento, notificaciones y cesión de datos al ecosistema. La aceptación debe hacerla la persona facultada y no se debe registrar su cédula, domicilio u otros documentos sensibles en este repositorio.

## 3. Admisibilidad

### Estado de avance de la solución

**Selección recomendada: Prototipo/PMV.**

Fundamento: existe una aplicación funcional de punta a punta, con backend, portal web, PostgreSQL, almacenamiento cifrado, pruebas, auditoría y reportes reproducibles. Sin embargo, la operación actual utiliza datos ficticios o sintéticos. No se ha acreditado un piloto real con 2–3 pymes, ventas informales ni ventas formales.

### Tamaño de la empresa y tramo de ventas

- Tamaño: `[POR COMPLETAR SEGÚN LA ENTIDAD POSTULANTE]`.
- Tramo de ventas: `[POR COMPLETAR CON RESPALDO TRIBUTARIO]`.
- Ventas de Recupera: `[POR COMPLETAR; SI NO EXISTEN, DECLARAR $0]`.

### Uso principal del cofinanciamiento

Texto propuesto:

> El cofinanciamiento se utilizará principalmente para validar comercial y operacionalmente el PMV con 2–3 pymes B2B, preparar la infraestructura segura para datos reales, completar la revisión legal y contractual, habilitar canales de comunicación controlados, medir impacto y unit economics, y ejecutar actividades comerciales para convertir el aprendizaje del piloto en una oferta repetible. No se financiará automatización masiva antes de comprobar qué bloqueo documental es frecuente, costoso y atribuible a la solución.

Distribución preliminar, sujeta a las categorías financiables de la convocatoria:

1. validación con clientes, onboarding y operación de pilotos;
2. infraestructura, seguridad, respaldo y observabilidad;
3. revisión legal, mandato, privacidad y contratos;
4. desarrollo de integraciones o automatizaciones únicamente después de validar su necesidad;
5. medición de impacto, unit economics y atribución;
6. comercialización, marca, sitio web y material de ventas;
7. dedicación del equipo y servicios especializados permitidos por las bases.

### Alcance comercial y competencia

- **Ubicación del problema:** inicialmente Chile, en pymes B2B que venden a empresas con procesos formales de compra y pago.
- **Cantidad exacta de competidores directos:** `[POR VERIFICAR CON ESTUDIO ACTUALIZADO]`.
- **Sustitutos identificados:** software de cobranza y cuentas por cobrar, cobranza extrajudicial, factoring, agencias y gestión manual con planillas, correo y WhatsApp.
- **Expansión:** nacional después del piloto; posible adaptación futura a México, Colombia o Perú, condicionada a regulación, facturación electrónica, idioma operativo y evidencia de tracción.

### Declaración de innovación

**Respuesta propuesta: Sí, es una solución innovadora desarrollada por el equipo.**

Justificación:

> Recupera integra en un mismo servicio la pagabilidad preventiva de facturas B2B, la ejecución asistida por IA, reglas contractuales auditables, intervención humana en excepciones, conciliación y cobro por resultado verificado. La innovación no consiste solo en aplicar IA a recordatorios: desplaza la gestión hacia la etapa anterior al vencimiento, donde se resuelven requisitos como OC, HES, aceptación y portales de proveedores, y construye conocimiento operativo reutilizable de pagadores. La titularidad del software y la relación entre autores y postulante deberán formalizarse antes de la firma de un eventual convenio.

### Video de pitch — máximo 40 segundos

- URL: `[POR GRABAR Y PUBLICAR]`.
- Contraseña: `[SI APLICA]`.

Guion propuesto, aproximadamente 85 palabras:

> Muchas pymes no cobran tarde porque su cliente no quiera pagar, sino porque la factura nunca quedó pagable: falta una orden de compra, una conformidad o una carga en el portal. Recupera acompaña cada factura desde su emisión, detecta bloqueos, coordina documentos y hace seguimiento hasta verificar el pago. La IA ejecuta tareas repetitivas bajo reglas auditables y una persona resuelve excepciones. A diferencia del software de cobranza o el factoring, prevenimos el atraso y cobramos por resultado. Buscamos validar el PMV con pymes chilenas y demostrar impacto en pago oportuno, DSO y horas administrativas.

El video debe mostrar el producto funcionando, al menos una pantalla del flujo y una frase explícita sobre la innovación frente a alternativas actuales.

### Incompatibilidades y financiamiento previo

- Participación del postulante en otras personas jurídicas: `[POR COMPLETAR]`.
- Proyectos cofinanciados anteriormente por CORFO: `[POR COMPLETAR]`.
- Otros subsidios públicos para el mismo objeto: `[POR COMPLETAR]`.
- Conflictos, deudas o incompatibilidades definidas en bases: `[REVISAR Y DECLARAR]`.

## 4. Innovación

### Problema u oportunidad

Las pymes B2B dependen del pago de facturas para financiar su operación, pero muchas no cuentan con un área especializada de cuentas por cobrar. Cuando venden a empresas medianas o grandes deben cumplir requisitos que varían por pagador: orden de compra, HES o conformidad, aceptación, datos maestros, registro de proveedor, carga en un portal y coordinación con cuentas por pagar. El trabajo se distribuye entre el dueño, administración y contabilidad; no existe una visión única del estado de la factura y el problema se descubre cuando ya venció.

El costo no es solo financiero. El equipo de la pyme invierte horas en revisar correos, pedir documentos, confirmar recepciones, reconstruir conversaciones y conciliar pagos. El factoring puede adelantar caja, pero no corrige el proceso; la cobranza tradicional interviene después del atraso; y el software requiere que la propia pyme opere el seguimiento. La oportunidad es convertir esa operación fragmentada en un servicio preventivo, trazable y medible.

El alcance territorial inicial es Chile. La magnitud económica del problema y el número de empresas del segmento objetivo deben cuantificarse con estadísticas oficiales y fuentes recientes antes del envío. El proyecto no presentará como hechos las hipótesis de atraso documental hasta medirlas con datos autorizados.

### Solución y grado de innovación

Recupera recibe o importa la cartera de facturas, aplica reglas específicas de cada pyme y pagador, controla su avance por etapas y mantiene un checklist de pagabilidad. El sistema prepara comunicaciones, clasifica respuestas, solicita documentos, gestiona excepciones, registra evidencia y propone conciliaciones. Los pagos se verifican y vinculan a una regla contractual antes de calcular una comisión.

Sus elementos diferenciadores son:

1. **Prevención:** actúa desde la emisión, no solo después del vencimiento.
2. **Pagabilidad:** gestiona requisitos concretos del proceso de compra y pago, no únicamente mensajes de cobranza.
3. **Servicio operado:** la pyme compra un resultado y no una nueva herramienta que deba administrar sola.
4. **IA con límites humanos:** las tareas repetitivas se asisten o automatizan, mientras pagos, disputas, conciliaciones y acciones sensibles conservan aprobación.
5. **Contrato y auditoría:** las reglas, canales, tono, frecuencia y comisión se versionan y cada evento queda trazado.
6. **Conocimiento de pagadores:** los requisitos y aprendizajes operativos pueden reutilizarse de forma aislada y sin exponer datos de una pyme a otra.
7. **Atribución defendible:** el reporte separa atribución, correlación e incertidumbre y evita contar dos veces un pago.

### Estado de desarrollo

Estado actual: **PMV funcional en ambiente local con datos sintéticos**.

Avances verificables:

- arquitectura multiempresa con aislamiento por pyme y roles;
- importación y gestión de facturas, contactos y estados;
- contratos y reglas versionadas por cliente;
- flujo por emisión, etapa documental, prevención, vencimiento, mora y escalamiento;
- gestión asistida de comunicaciones y respuestas;
- requisitos de pagabilidad y perfiles de pagadores;
- conciliación supervisada y pagos con evidencia;
- carga segura de documentos, cifrado y revisión del operador;
- portal cliente, métricas, auditoría y cierre reproducible;
- medición de trabajo humano y flujo guiado optimizado;
- cohortes comparables, exclusiones y trazabilidad de atribución;
- 79 pruebas backend sobre PostgreSQL, 35 controles offline y build web aprobado.

Pruebas realizadas:

- demostraciones y ensayos con datos ficticios;
- benchmark sintético del flujo guiado: reducción de 54 a 36 minutos en tres casos comparables, equivalente a 33,33%, sin acciones externas;
- ensayo sintético de atribución: 6 pagos verificados, 4 incluidos, 2 excluidos, 66,67% de cobertura trazable y 0 duplicados;
- controles de privacidad, roles, idempotencia, inmutabilidad y recuperación local.

Limitación que debe declararse: estos resultados prueban el instrumento técnico, no el impacto real, la disposición a pagar ni la rentabilidad. Están pendientes datos autorizados, revisión jurídica, 2–3 pymes, infraestructura pública y operación real de 6–8 semanas.

Protección intelectual:

- Patentes: no se ha identificado una solicitud o patente registrada; confirmar si aplica.
- Marca “Recupera”: disponibilidad no verificada.
- Código y documentación: existentes en el repositorio; `[POR FORMALIZAR TITULARIDAD, LICENCIAS Y CESIONES AL POSTULANTE]`.
- Estrategia sugerida: marca, derechos de autor sobre software y documentación, secretos empresariales para reglas y conocimiento de pagadores, y contratos de confidencialidad y cesión cuando corresponda.

### Análisis de competencia

| Alternativa | Atributos | Brecha frente a Recupera |
|---|---|---|
| Software de cobranza o cuentas por cobrar | Recordatorios, paneles, conciliación y seguimiento | La pyme normalmente debe operar el software; la cobertura de OC, HES y portales debe verificarse caso a caso |
| Cobranza extrajudicial por éxito | Incentivo por recuperación y experiencia de cobro | Actúa principalmente cuando la deuda ya está vencida y puede tensionar la relación comercial |
| Factoring | Liquidez inmediata | Tiene costo financiero y no corrige el bloqueo de la factura ni el plazo real del pagador |
| Agencias o abogados | Gestión humana y escalamiento | Costos por caso, orientación a mora y menor viabilidad para facturas pequeñas o prevención |
| Gestión interna con planillas, correo y WhatsApp | Flexible y conocida por la pyme | Fragmentada, difícil de medir, dependiente de personas y sin trazabilidad integral |
| Plataformas internacionales de IA para cuentas por cobrar | Automatización avanzada y conexión con ERP | Suelen enfocarse en grandes empresas y no necesariamente incluyen regulación, SII, HES y operación de pymes chilenas |

Referentes identificados internamente para revisar antes del envío: Xepelin, Cuadra, Chipax, Bemmbo, Clay, Moonflow, Faaro, Duemint y Stuut. No incluir afirmaciones específicas de producto, precio, clientes o inversión sin verificarlas con fuentes actuales.

### Información adicional sobre innovación

La solución fue diseñada con puertas de evidencia: una función no avanza a automatización productiva porque sea técnicamente posible, sino cuando demuestra un problema frecuente, una métrica de mejora y controles de reversión. PM-1 mide costo humano, PM-2 optimiza un flujo y PM-3 fortalece comparables y atribución. Este enfoque reduce el riesgo de automatizar tareas que no aportan valor y protege la credibilidad de los resultados ante CORFO, clientes e inversionistas.

## 5. Escalabilidad

### Análisis de mercado

Mercado objetivo inicial: pymes chilenas B2B que emiten entre 20 y 300 facturas mensuales a empresas medianas o grandes, usan procesos formales de compra y pago y no cuentan con un equipo dedicado de cuentas por cobrar.

Segmentos prioritarios por validar:

- proveedores y contratistas de minería;
- construcción y montaje;
- industria y energía;
- servicios profesionales y técnicos;
- proveedores de retail y grandes empresas.

Necesidad de cuantificación antes del envío:

- **TAM:** total de pymes B2B en Chile que venden a empresas y administran cuentas por cobrar.
- **SAM:** pymes del segmento con volumen, formalidad y complejidad documental compatible con la solución.
- **SOM inicial:** clientes alcanzables durante los primeros 24–36 meses según capacidad comercial y operativa.
- Fuentes sugeridas para validación externa: SII, INE, Banco Central, Ministerio de Economía, registros de pago oportuno y estudios gremiales. `[PENDIENTE POR RESTRICCIÓN DE CONECTIVIDAD]`.

Tendencias relevantes a validar con fuentes actuales: adopción de facturación electrónica, digitalización de cuentas por pagar, mayor uso de IA empresarial, presión por eficiencia de capital de trabajo y nuevas exigencias de protección de datos.

Barreras de entrada:

- confianza para actuar en nombre de la pyme;
- integración con fuentes y canales de comunicación;
- conocimiento específico de requisitos de pagadores;
- seguridad, privacidad y trazabilidad;
- capacidad de demostrar atribución y evitar cobrar por pagos que habrían ocurrido igualmente;
- operación humana eficiente durante las excepciones.

La ficha acumulada de pagadores, los contratos versionados y la evidencia operacional pueden convertirse en ventajas defensibles si se construyen con aislamiento y base legal adecuada.

### Oportunidad de mercado

Es oportuno validar Recupera porque la tecnología permite automatizar clasificación, redacción y priorización con costos decrecientes, mientras los procesos de pago B2B continúan fragmentados entre sistemas, documentos, correos y portales. El proyecto ya cuenta con un PMV funcional, por lo que el cofinanciamiento puede concentrarse en reducir incertidumbre comercial y operacional en lugar de comenzar desde una idea.

El hito clave no es agregar más funciones, sino probar tres supuestos: que los bloqueos documentales explican una proporción material del atraso, que las pymes permiten y valoran una gestión externa preventiva, y que el costo humano por factura permite un margen sostenible.

### Factores regionales y territoriales

`[POR COMPLETAR DESPUÉS DE DEFINIR REGIÓN Y COMUNA]`.

Texto adaptable:

> La Región de `[REGIÓN]` concentra actividades `[RUBROS RELEVANTES]` y una red de pymes proveedoras que vende a empresas con procesos formales de compra y pago. Esta estructura permite validar requisitos documentales repetitivos y pagadores compartidos. La ejecución digital facilita atender posteriormente otras regiones, mientras el aprendizaje inicial se obtiene desde una red territorial concreta de empresas, asociaciones y actores del ecosistema.

Se deben respaldar las ventajas territoriales con datos regionales y alianzas reales; no usar este párrafo sin completar esa evidencia.

### Perfil de cliente

**Tipo:** pymes.

**Cliente ideal inicial:** empresa chilena B2B que emite aproximadamente 20–300 facturas mensuales, vende a empresas medianas o grandes, enfrenta requisitos como OC, HES, aceptación o portales y no tiene un área especializada de cobranza. Debe disponer de información histórica mínima, autorizar el uso de datos y nombrar un responsable para aprobar documentos, pausas y excepciones.

**Comprador:** dueño, gerente general o gerente de administración y finanzas.

**Usuario operativo:** administrativo, encargado de finanzas o contador.

**Pagador indirectamente involucrado:** área de cuentas por pagar, solicitante del servicio o responsable de conformidad en la empresa cliente.

**Fuera del segmento:** consumidores, cobranza judicial, publicación en boletines, grandes empresas con operación interna madura y casos donde no existe mandato para contactar al pagador.

### Estrategia comercial y de expansión

1. **Descubrimiento y selección:** entrevistar pymes y áreas de cuentas por pagar, identificar volúmenes, causas y disposición a participar.
2. **Piloto controlado:** incorporar 2–3 pymes con datos autorizados, línea base y pagadores idealmente compartidos; operar 6–8 semanas.
3. **Oferta inicial:** fee de activación u operación base y comisión diferenciada sobre pagos verificados, sujeta a validación de disposición a pagar.
4. **Prueba de valor:** entregar un reporte de pagabilidad, pago oportuno, DSO, horas ahorradas y causas de atraso.
5. **Adquisición:** venta directa a dueños y finanzas, alianzas con contadores, asociaciones gremiales, incubadoras y proveedores de servicios a pymes.
6. **Repetibilidad:** estandarizar onboarding, contratos, checklist, fichas de pagadores y revisión semanal.
7. **Escala nacional:** llegar a 10–20 clientes con un equipo pequeño y medir que los minutos humanos no crezcan linealmente.
8. **Expansión internacional:** evaluar un segundo país solo después de demostrar retención, margen y repetibilidad en Chile.

### Actividades principales y alianzas

Actividades propuestas durante la ejecución:

- reclutar y seleccionar pymes piloto;
- recopilar línea base y datos históricos autorizados;
- completar revisión legal, privacidad, mandato y contratos;
- preparar infraestructura pública segura, respaldos y observabilidad;
- configurar reglas, pagadores, requisitos y canales por pyme;
- operar el piloto con revisión diaria y reporte semanal;
- medir DSO, pago oportuno, causas, minutos humanos, costos y margen;
- entrevistar usuarios, pagadores y responsables financieros;
- priorizar mejoras únicamente desde evidencia;
- definir precio, canal comercial y caso de éxito;
- preparar la decisión de escalar, iterar, pivotar o detener.

Alianzas necesarias, todavía no acreditadas:

- 2–3 pymes piloto;
- asesoría jurídica en mandato B2B, privacidad y tratamiento de datos;
- contador, estudio contable o asociación gremial para acceso al segmento;
- proveedor de infraestructura y comunicaciones;
- incubadora, mentor o red comercial regional.

**Alianzas ya disponibles:** `[POR COMPLETAR; NO PRESENTAR LAS ANTERIORES COMO CERRADAS]`.

### Sostenibilidad

Impacto social esperado:

- mejorar la previsibilidad de caja de pymes proveedoras;
- reducir horas administrativas repetitivas;
- disminuir la dependencia de cobranza tardía o financiamiento de emergencia;
- facilitar relaciones comerciales más ordenadas y menos confrontacionales;
- generar información sobre causas de atraso para mejorar procesos.

Impacto ambiental potencial: digitalización y reducción de reprocesos documentales. No se debe prometer una reducción ambiental cuantificada mientras no exista una línea base.

Indicadores propuestos:

- cambio en pago oportuno y DSO;
- monto pagado a tiempo o recuperado;
- minutos humanos por factura;
- tiempo de resolución documental;
- porcentaje de gestiones sin intervención humana;
- contactos duplicados, incidentes y quejas;
- costo y margen por cliente.

## 6. Equipo

### Composición del equipo emprendedor

- Número de socios con al menos 5%: `[POR COMPLETAR]`.
- Estructura societaria actual o futura: `[POR COMPLETAR]`.
- Persona responsable de producto/negocio: `[POR COMPLETAR]`.
- Persona responsable de tecnología: `[POR COMPLETAR]`.
- Persona responsable comercial/operacional: `[POR COMPLETAR]`.
- Apoyo legal o financiero: `[POR COMPLETAR]`.

### Ficha de cofundador 1

- Nombre y RUT: `[POR COMPLETAR; NO GUARDAR RUT EN GIT]`.
- Fecha de nacimiento, género y nacionalidad: `[POR COMPLETAR]`.
- Rol: `[POR COMPLETAR]`.
- Nivel educacional: `[POR COMPLETAR]`.
- Años de experiencia laboral: `[POR COMPLETAR]`.
- Emprendimientos fundados: `[POR COMPLETAR]`.
- Proyectos CORFO previos: `[POR COMPLETAR]`.
- Experiencia, capacidades y logros relevantes: `[POR COMPLETAR]`.
- Dedicación: `[POR COMPLETAR: HORAS O % SOBRE 180 HORAS MENSUALES]`.
- Actividad principal y compatibilización: `[POR COMPLETAR]`.
- Participación social actual o futura: `[POR COMPLETAR]`.

### Ficha de cofundador 2

`[REPETIR LOS CAMPOS ANTERIORES SI APLICA]`.

### Ficha de cofundador 3

`[REPETIR LOS CAMPOS ANTERIORES SI APLICA]`.

### Descripción general del equipo

Plantilla sugerida:

> El equipo combina capacidades de `[TECNOLOGÍA/IA]`, `[FINANZAS Y CUENTAS POR COBRAR]`, `[OPERACIÓN B2B]` y `[VENTAS A PYMES]`. `[NOMBRE]` lidera `[FUNCIÓN]` y aporta `[EXPERIENCIA]`; `[NOMBRE]` lidera `[FUNCIÓN]` y aporta `[EXPERIENCIA]`. La complementariedad permite desarrollar el producto, operar el piloto, interpretar métricas financieras y convertir el aprendizaje en una oferta comercial. Las brechas actuales son `[LEGAL/VENTAS/INDUSTRIA]` y se cubrirán mediante `[CONTRATACIÓN O ALIANZA]`.

No completar esta sección con capacidades genéricas: debe vincular cada experiencia con una actividad crítica del proyecto.

### Declaraciones obligatorias

`[DEBEN SER REVISADAS Y ACEPTADAS PERSONALMENTE POR CADA INTEGRANTE]`.

Confirmar participación accionaria, dedicación, ausencia de incompatibilidades y veracidad de antecedentes antes de enviar.

## 7. Datos estadísticos

- Alcance comercial potencial a 3–6 años: **Nacional**, con expansión latinoamericana como posibilidad condicionada a validación en Chile.
- Número de empleados al 31 de diciembre de 2025: `[POR COMPLETAR]`.
- Ventas totales acumuladas de 2025: `[POR COMPLETAR; $0 SI CORRESPONDE]`.
- Exportaciones de 2025: `[POR COMPLETAR; $0 SI CORRESPONDE]`.
- Capital o inversión previa, fuente y monto: `[POR COMPLETAR]`.
- Incubadoras, mentores o cursos: `[POR COMPLETAR]`.
- Interacción con el Viaje del Emprendedor: `[POR COMPLETAR]`.
- Medio por el cual conoció la convocatoria: `[POR COMPLETAR]`.
- Declaración final: `[ACEPTAR EN LA PLATAFORMA DESPUÉS DE REVISAR EL FORMULARIO COMPLETO]`.

## 8. Plan de ejecución propuesto para el fondo

> Ajustar duración, presupuesto y entregables a las bases específicas.

| Etapa | Actividades | Resultado verificable |
|---|---|---|
| 1. Preparación | Segmentación, entrevistas, selección de pymes, revisión legal y diseño de línea base | 2–3 cartas de intención, mandato y protocolo de datos |
| 2. Habilitación | Infraestructura segura, dominio, canales, respaldo, configuración y onboarding | Entorno operativo y checklist GO aprobado |
| 3. Piloto | Operación de 6–8 semanas, seguimiento, excepciones y reportes semanales | Bitácora, métricas por pyme e incidentes |
| 4. Evaluación | Comparables, atribución, unit economics, entrevistas y disposición a pagar | Informe real, caso de negocio y decisión G4 |
| 5. Comercialización | Precio, material de ventas, canales, alianzas y plan de expansión | Oferta repetible y cartera comercial inicial |

### Objetivo general propuesto

**Validar técnica, comercial y operacionalmente un servicio asistido por IA que mejora la pagabilidad y el pago oportuno de facturas B2B de pymes chilenas, demostrando su impacto, aceptación y ruta a un modelo escalable.**

### Objetivos específicos propuestos

1. Ejecutar un piloto autorizado con 2–3 pymes B2B durante 6–8 semanas.
2. Medir causas de atraso, pago oportuno, DSO y tiempo de resolución documental frente a una línea base.
3. Validar la disposición a pagar y el modelo de fee más comisión sobre pagos verificados.
4. Reducir y medir los minutos humanos por factura sin aumentar errores, duplicados o incidentes.
5. Definir una estrategia comercial nacional y una decisión fundada de escalar, iterar, pivotar o detener.

### Indicadores y metas de validación

Estas metas son hipótesis de trabajo y deben alinearse con la convocatoria:

| Indicador | Línea base | Meta propuesta |
|---|---:|---:|
| Pymes con piloto autorizado | 0 | 2–3 |
| Duración de operación real | 0 semanas | 6–8 semanas |
| Línea base completa | No disponible | 100% de pymes piloto |
| Pagos incluidos con cadena trazable | No disponible | 100% de resultados reportados |
| Duplicados de mensajes o pagos | 0 en ensayo | 0 |
| Incidentes graves de privacidad | 0 en ensayo | 0 |
| Mejora de pago oportuno | Por establecer | hipótesis: +20 puntos |
| Reducción de DSO | Por establecer | hipótesis: al menos 20% |
| Facturas sin intervención humana | Por establecer | hipótesis: al menos 70% |
| Margen operativo por cliente | No validado | positivo en escenario observado |

No comprometer las metas de impacto porcentual como resultados ya logrados; deben presentarse como objetivos de validación.

## 9. Evidencia disponible y límites

| Evidencia | Estado | Uso correcto en la postulación |
|---|---|---|
| PMV funcional | Completo localmente | Demostrar capacidad de ejecución y avance tecnológico |
| Suite de pruebas | 79 pruebas backend + 35 controles offline | Respaldar calidad técnica, no tracción |
| Flujo guiado PM-2 | `passed_synthetic` | Explicar instrumento y mejora experimental, no ahorro real |
| Comparables PM-3 | `passed_synthetic` | Demostrar metodología de atribución, no impacto comercial |
| Datos reales autorizados | Pendiente | No afirmar resultados reales |
| Revisión legal y mandato | Pendiente | No operar contactos reales todavía |
| Pymes piloto | Pendiente | No declarar pilotos o cartas sin firma |
| Ventas | `[POR COMPLETAR]` | Adjuntar respaldo si existen |
| Infraestructura pública | Pendiente | No afirmar que está en producción |
| Decisión de escala | Pendiente | El fondo financiará la reducción de esta incertidumbre |

## 10. Información mínima que debe entregar el postulante

### Prioridad 1 — Admisibilidad

- convocatoria y línea CORFO exactas;
- persona natural o jurídica;
- región y comuna;
- RUT y antecedentes legales en la plataforma, nunca en Git;
- fecha de constitución y ventas si existe empresa;
- financiamientos CORFO anteriores e incompatibilidades;
- estado real de ventas y capital levantado.

### Prioridad 2 — Evaluación

- integrantes, roles, experiencia, dedicación y participación;
- alianzas reales, cartas de intención o conversaciones verificables;
- acceso a pymes del segmento;
- presupuesto total, subsidio solicitado y aporte propio;
- duración máxima permitida;
- región y argumento territorial;
- límites de caracteres de cada campo.

### Prioridad 3 — Anexos

- video de pitch;
- sitio web o página de presentación;
- perfiles de LinkedIn;
- constitución, personería y certificados exigidos;
- respaldos de ventas, inversión o cofinanciamiento;
- cotizaciones y cartas según bases.

## 11. Revisión antes de enviar

- Confirmar que el programa CORFO acepta el tipo de postulante y estado PMV.
- Sustituir todos los marcadores `[POR COMPLETAR]`.
- Ajustar cada respuesta al límite de caracteres del formulario.
- Verificar competencia, mercado y normativa con fuentes actuales.
- No incluir datos sintéticos como ventas, pilotos o impacto real.
- No afirmar alianzas, cartas de intención, propiedad intelectual o liderazgo femenino sin respaldo.
- Confirmar titularidad del código y del nombre comercial.
- Conciliar presupuesto, objetivos, actividades e indicadores.
- Revisar el pitch y el formulario con una persona externa.
- Guardar documentos personales únicamente en la plataforma autorizada, no en el repositorio.
