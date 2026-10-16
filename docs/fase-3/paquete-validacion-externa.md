# Paquete de validación externa — Fase 3

> Preparado para ejecutar cuando existan datos autorizados, revisión jurídica y pymes interesadas. Ningún punto de este documento acredita por sí solo una validación real.

## V-03 — Análisis retrospectivo real

### Insumos mínimos por factura

- identificador pseudonimizado de la pyme y del pagador;
- tipo y folio de documento;
- fechas de emisión, vencimiento y pago;
- monto total;
- estado final de la factura;
- causa principal de atraso;
- días de atraso y marca de pago dentro de plazo;
- presencia o ausencia de OC, HES/conformidad, aceptación SII y carga en portal.

No deben incluirse credenciales, secretos, conversaciones completas ni datos personales que no sean necesarios para el análisis.

### Ejecución preparada

El libro autorizado debe conservar una hoja `Facturas` con el mismo orden de columnas del libro demo. El análisis no modifica el archivo:

```powershell
python scripts/analyze_retrospective.py --workbook "RUTA_AL_ARCHIVO.xlsx" --authorized-real-data
```

Antes de presentar el resultado se debe comprobar:

- al menos dos pymes y un período comparable;
- conciliación de totales con la fuente entregada;
- causas vacías revisadas como dato faltante, no asumidas como pago normal;
- cálculo separado por cantidad y monto;
- línea base por pyme: DSO, pago a tiempo y distribución de atrasos;
- registro de quién autorizó el uso y la fecha de corte.

## V-05 — Consulta legal

Enviar al profesional competente los siguientes documentos:

- `restricciones-legales-operativas.md`;
- `mandato-piloto-borrador.md`;
- `carta-intencion-piloto.md`;
- descripción de la ficha global, aislamiento por pyme y bitácora inmutable;
- ejemplos ficticios de trabajos `action_ready`, sin datos reales.

La respuesta debe pronunciarse expresamente sobre:

1. alcance del mandato de coordinación documental y cobranza B2B;
2. tratamiento, corrección, oposición, retención y eliminación de datos;
3. uso de estados SII y credenciales de portales;
4. identificación, frecuencia y canales permitidos para contactar pagadores;
5. límites de la ficha compartida de pagadores;
6. responsabilidad por errores, asociación de pagos y evidencia;
7. texto contractual y controles que deben existir antes del piloto.

El entregable aceptable es un dictamen o minuta fechada, con autor identificable, jurisdicción y lista de cambios obligatorios. Las restricciones resultantes deben incorporarse al contrato y al producto antes de habilitar comunicaciones reales.

## V-07 — Cartas de intención

Meta: 2–3 pymes, idealmente con pagadores en común. Para cada candidata registrar, sin inventar firmas:

| Campo | Evidencia requerida |
|---|---|
| Pyme y representante | Identificación confirmada por la propia empresa |
| Período y cartera del piloto | Segmento, volumen y pagadores incluidos |
| Disponibilidad de datos V-03 | Tipo de datos, período y autorización |
| Responsable operativo | Persona que valida documentos, pausas y resultados |
| Canales inicialmente permitidos | Simulación, email o WhatsApp asistido |
| Restricciones del pagador | Contratos, portales y contactos excluidos |
| Carta | Documento firmado y fechado por ambas partes |

Una conversación o borrador no cuenta como carta cerrada. La carta tampoco reemplaza el mandato operativo ni la revisión V-05.

## Orden de desbloqueo

1. Recibir datos autorizados y ejecutar V-03.
2. Presentar el resultado y el diseño al asesor jurídico para completar V-05.
3. Incorporar los cambios obligatorios al producto y al mandato.
4. Firmar 2–3 cartas de intención y el mandato correspondiente.
5. Recién entonces habilitar un piloto con contactos reales.

