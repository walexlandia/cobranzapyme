# Runbook de observabilidad e incidentes

## Consulta segura

Un administrador autenticado consulta `GET /api/v1/operations/observability`. Un operador o cliente recibe `403`. La respuesta contiene `overall_status`, alertas, umbrales, telemetría HTTP agregada, carga de trabajo y el último latido del worker.

Después de desplegar una revisión, confirmar en este orden:

1. `GET /health/live` responde `200`.
2. `GET /health/ready` responde `200` y prueba PostgreSQL.
3. `GET /health/version` informa cabeza `0019`.
4. El diagnóstico muestra `worker.observed=true`, `worker.status=healthy` y un `stale_seconds` menor que 75.
5. No quedan alertas críticas sin una incidencia registrada y responsable humano.

## Umbrales y respuesta

| Alerta | Warning | Critical | Primera respuesta |
|---|---:|---:|---|
| Antigüedad del job pendiente más antiguo | 300 s | 1.800 s | Verificar worker, bloqueo de base y volumen de cola |
| Latido del worker | 75 s | 120 s | Revisar logs y conectividad PostgreSQL; no duplicar workers a ciegas |
| Fallos consecutivos del worker | 1 | 3 | Identificar la excepción; el backoff progresa 60, 120, 240 y 300 s |
| Documentos pendientes | 20 | — | Redistribuir revisión humana |
| Excepciones abiertas | 50 | — | Priorizar por antigüedad y criticidad |
| Mensajes fallidos | 1 | — | Mantener comunicación pausada hasta revisar proveedor y destinatario |
| Documento en texto plano legado | — | 1 | Detener carga/descarga y completar migración cifrada |
| Incidente crítico abierto | — | 1 | Asignar responsable y registrar resolución verificable |

## Recuperación del worker

El worker conserva un único latido `service_name=worker`. Cada ciclo exitoso reinicia los fallos a cero. Cada fallo marca estado `degraded`; el tiempo antes del próximo intento crece exponencialmente y queda limitado a cinco minutos. Si PostgreSQL no está disponible, el log local conserva el error aunque no pueda actualizarse el latido.

Para ensayar la lógica sin servicios externos:

```powershell
python scripts/simulate_worker_resilience.py
```

El ensayo esperado produce dos estados warning, demoras de 60 y 120 segundos, y luego recuperación healthy con cadencia de 30 segundos.

## Cierre del incidente

No cerrar por el solo reinicio del proceso. Confirmar dos ciclos saludables, reducción efectiva de la cola y ausencia de mensajes duplicados. Registrar causa, ventana, impacto, acciones y evidencia en la bitácora del piloto. Si intervino una comunicación, mantener la reanudación bajo decisión humana.
