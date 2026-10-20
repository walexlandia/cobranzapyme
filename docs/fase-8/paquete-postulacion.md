# Paquete de postulación e inversionistas

El incremento 8.3 genera un ZIP determinista desde un snapshot de cierre ya persistido. No recalcula la cartera ni consulta fuentes transaccionales al descargarlo: todos los artefactos derivan del mismo informe agregado y de su huella SHA-256.

## Contenido

| Archivo | Propósito |
|---|---|
| `resumen-ejecutivo.md` | Propuesta, alcance, resultados, economía y estado del cierre |
| `informe-final-v10.md` | Informe completo reproducible del piloto |
| `dataset-anonimizado.csv` | Segmentos agregados que superan el umbral de privacidad |
| `unit-economics.csv` | Sensibilidad conservadora, observada y eficiente |
| `backlog-priorizado.csv` | Trabajo posterior ordenado por la evidencia |
| `anexo-evidencia.md` | Cobertura de autorización, controles G4 e hipótesis |
| `manifest.json` | Versión, huella del informe y SHA-256/tamaño de cada archivo |

El archivo se descarga desde **Cierre verificable del piloto → Snapshots y decisiones G4 → Descargar paquete ZIP**. También está disponible por `GET /api/v1/metrics/closures/{closure_id}/package.zip` para roles operador y administrador.

## Reproducibilidad e integridad

- Los archivos se escriben en un orden fijo y el ZIP usa una fecha interna constante.
- Dos descargas del mismo snapshot y estado producen exactamente los mismos bytes.
- `X-Package-SHA256` informa la huella del ZIP y `manifest.json` permite verificar cada contenido por separado.
- Una decisión posterior cambia el contenido legítimamente; desde ese momento el snapshot queda inmutable por base de datos.

## Privacidad y uso correcto

- El paquete excluye nombres, RUT, folios, contactos, UUID internos y el texto libre usado para justificar la decisión.
- Los seudónimos y segmentos conservan las reglas de anonimización y supresión del informe V-10.
- Si la evidencia es sintética, el resumen y el manifiesto marcan el paquete como borrador. No debe presentarse como validación comercial, resultado real ni decisión G4.
- Para un piloto autorizado, el paquete sigue requiriendo revisión humana de las fuentes, permisos y consistencia antes de compartirse externamente.

## Verificación manual

1. Descargar el ZIP desde el snapshot correcto.
2. Comparar la cabecera `X-Report-Fingerprint` con la huella mostrada en el portal.
3. Calcular SHA-256 de los seis artefactos y contrastarlos con `manifest.json`.
4. Confirmar que `evidence_kind`, `draft`, `closure_status` y `decision` describen el uso previsto.
5. Revisar el resumen ejecutivo y los anexos antes de cualquier entrega externa.
