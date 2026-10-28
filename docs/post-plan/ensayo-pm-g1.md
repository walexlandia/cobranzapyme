# PM-G1.1 — Ensayo integral desechable

Fecha de ejecución: 2026-10-28.

Este ensayo cierra la validación local de PM-1. Comprueba el mecanismo de PM-G1 con datos exclusivamente sintéticos; no reemplaza contratos, mandatos ni evidencia real y no autoriza PM-2.

## Escenario ejecutado

- entorno Docker dedicado, con PostgreSQL vacío y sin volumen persistente;
- tres pymes, contratos, facturas, contactos y mediciones sintéticas;
- comprobantes de autorización cargados por la API y cifrados con `aesgcm-v1`;
- generación segura del diagnóstico fuera del repositorio con `--require-approved`;
- revocación de una autorización y repetición inmediata del diagnóstico;
- destrucción de contenedores, red y volúmenes al finalizar.

## Resultado

| Paso | Resultado esperado | Resultado observado |
|---|---|---|
| Sin autorizaciones | `authorization_incomplete` | Aprobado |
| Tres autorizaciones vigentes | `approved`, cobertura 3/3 y `pm2_authorized: true` | Aprobado |
| CLI con gate aprobado | Código de salida `0` | Aprobado |
| Cifrado documental | Texto plano distinto del contenido almacenado y descifrado exacto | Aprobado |
| Revocación de una autorización | `authorization_incomplete` y `pm2_authorized: false` | Aprobado |
| CLI con gate revocado | Código de salida `2` | Aprobado |
| Limpieza | Cero contenedores, redes y volúmenes del proyecto | Aprobado |

La secuencia verificada fue `approved -> revoked -> authorization_incomplete`. Los reportes temporales se generaron dentro del contenedor en `/tmp`; ningún comprobante ni reporte de muestra quedó en Git.

## Reproducción

```powershell
.\scripts\rehearse-pm-g1.ps1
```

El script usa `compose.pm-g1-rehearsal.yaml`, ejecuta únicamente `backend/tests/test_pm_g1_rehearsal.py` y destruye el entorno incluso si la prueba falla. La imagen de aplicación puede conservarse como caché local, pero no contiene los datos creados durante el ensayo.

## Decisión

PM-1 queda terminada en su alcance local, técnico, documental y de ensayo. PM-G1 real continúa pendiente de EXT-02 y EXT-03; hasta entonces el estado productivo sigue siendo `provisional_synthetic` y PM-2 permanece bloqueada.
