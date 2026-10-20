# Matriz G4 — Escalar, iterar, pivotar o detener

## Controles obligatorios

| Control | Umbral |
|---|---:|
| Evidencia | Piloto autorizado, no seed sintético |
| Cobertura legal | Autorización vigente y contrato activo para todas las pymes participantes durante el período completo |
| Duración | 42 días o más |
| Cobertura | 2 pymes activas o más |
| Resultado observable | 10 facturas saldadas o más |

Si falla un control, la salida es `pending` aunque las métricas sintéticas sean favorables.

## Hipótesis evaluadas

1. **Resultado:** la mayoría de clientes comparables mejora DSO o pago oportuno sin señal contraria.
2. **Relevancia documental:** al menos 30% de una muestra de 10 o más facturas corresponde a causas documentales; menos de 15% rechaza la hipótesis y el rango intermedio queda incierto.
3. **Economía:** el margen agregado, después de tecnología y minutos humanos, es positivo.

## Reglas de recomendación

| Alternativa | Regla automática |
|---|---|
| Escalar | Las tres hipótesis se confirman y el mayor pagador concentra menos de 60% del monto publicado |
| Iterar | Hay mejora, pero persiste concentración, margen negativo o señal operativa mixta |
| Pivotar | La hipótesis documental se rechaza |
| Detener | Resultado y economía se rechazan después de superar los controles mínimos |

Los casos que no encajan exactamente se orientan a una iteración acotada. La decisión final debe registrarse en la bitácora con responsable, evidencia revisada y fecha de siguiente revisión.

## Flujo de aprobación

1. Un operador o administrador genera el informe y prepara el snapshot.
2. El sistema valida evidencia, autorizaciones, duración, cobertura y liquidaciones.
3. Un administrador diferente revisa escenarios económicos, hipótesis y backlog.
4. El administrador selecciona una alternativa y registra su justificación.
5. El snapshot cambia de `prepared` a `decided` y queda cerrado.

El sistema admite que la decisión humana difiera de la recomendación automática, pero conserva ambas para auditoría. No permite decidir snapshots sintéticos, reemplazar una decisión previa ni autoaprobar el cierre preparado por la misma persona.
