# Estado de la Fase 8

> Inicio técnico: 19 de octubre de 2026
>
> Modalidad actual: cierre local con datos sintéticos; decisión G4 real pendiente

## Incremento 8.1 — Medición final y matriz de decisión

| Entregable | Estado local | Evidencia |
|---|---|---|
| Dataset agregado y anonimizado | Completo localmente | CSV por cliente, pagador, causa y tramo de monto; alias HMAC-SHA256 y supresión configurable de grupos pequeños |
| Informe final V-10 | Completo localmente | JSON para el portal y documento Markdown descargable con versión, parámetros y huella SHA-256 |
| Comparación por cliente | Completo localmente | DSO y pago oportuno frente a línea base, facturas, minutos humanos y margen usando solo alias |
| Análisis de segmentos | Completo localmente | Cantidad, monto nominal, monto verificado, liquidación y pago oportuno por pagador, causa y monto |
| Hipótesis | Completo como instrumento | Estados confirmada, rechazada o incierta para resultado, relevancia documental y economía |
| Matriz G4 | Completo como instrumento | Escalar, iterar, pivotar o detener con controles mínimos; el seed solo puede producir una decisión pendiente |

## Límites deliberados

- No se agregaron tablas ni datos de resultado inventados: el cierre se calcula desde los registros auditables existentes.
- La segmentación usa facturas emitidas dentro del período y resultados derivados de pagos verificados.
- El dataset no contiene nombres, RUT, folios, contactos ni UUID internos.
- Un grupo se publica solo si alcanza `minimum_group_size`; el valor predeterminado es 2.
- Los seudónimos son deterministas dentro de la instalación mediante una clave independiente, pero no son reversibles desde el exportado.
- Declarar `authorized_pilot` identifica la procedencia informada por el operador; no reemplaza mandato, autorización ni revisión de evidencia.
- La decisión G4 exige evidencia autorizada, al menos 42 días, 2 pymes y 10 facturas saldadas.

## Trabajo externo pendiente

La funcionalidad permite cerrar el informe, pero los datos sintéticos no validan el negocio. Continúan pendientes la operación real de 6–8 semanas, la aceptación de las pymes, la revisión de incidentes y la aprobación humana de la decisión de continuidad.

## Validación local

- Compilación Python aprobada para aplicación, pruebas y scripts.
- 27 comprobaciones offline aprobadas, incluida la invariancia de G4 ante evidencia sintética.
- Build de producción Next.js aprobado usando la imagen local `recupera-web:phase7-4` y los archivos de Fase 8.1 montados sin red.
- Prueba HTTP/PostgreSQL preparada en `backend/tests/test_final_report.py` para privacidad, exportaciones y control de roles.
- La ejecución integral de `pytest` queda pendiente: el runtime backend no está disponible localmente y Docker no puede descargar dependencias por el firewall.
