# Checklist de cierre — Fase 3

> Corte local: 15 de octubre de 2026  
> Alcance: producto y validación que pueden ejecutarse sin contactos ni servicios externos

## Cobertura de producto

| Requisito | Estado local | Evidencia principal |
|---|---|---|
| EP-01 Ficha global por RUT | Completo | `backend/app/routers/payers.py`, consola de pagadores y revisiones inmutables |
| EP-02 Separación global/privada | Completo | Respuesta global sin relaciones privadas y tests de contenido y acceso no asociado |
| EP-03 Checklist por factura | Completo | Generación al importar y en la semilla; unicidad comprobada en PostgreSQL |
| EP-04 Estado SII y alerta legal | Completo | Importación CSV/XLSX, estados aceptada/reclamada/rechazada/pendiente y caso de plazo vencido |
| EP-05 Solicitud y seguimiento | Completo local | El motor selecciona acción y destinatario según el requisito; la entrega externa permanece deshabilitada |
| EP-06 Evidencia de portal | Completo | Número de ingreso, fecha y referencia con evento de auditoría |
| EP-07 Riesgo previo al vencimiento | Completo | Umbral configurable por pagador y estado visible en cartera, vista cliente y métricas |
| EP-08 Confirmación preventiva | Completo | Aprobación o rechazo, fecha programada y referencia, con trazabilidad por control |
| E11-06 Causa de atraso | Completo | Registro por factura y agregado por cantidad y monto |

## Criterios de salida

| Criterio | Resultado |
|---|---|
| Toda factura importada obtiene checklist | Cumplido en el flujo de importación y en los datos demo |
| No se filtran datos privados entre pymes | Cubierto por diseño y tests preparados de respuesta y acceso |
| La causa de atraso se registra y agrega | Cumplido |
| Existe una decisión posterior a G1 | Cumplido para datos sintéticos: continuar en piloto controlado |

## Verificación local ejecutada

- Compilación Python sin errores.
- Trece comprobaciones offline aprobadas, incluidas las reglas críticas de Fase 3 y el contrato OpenAPI.
- Build de producción Next.js aprobado con red deshabilitada.
- DDL PostgreSQL 16 e invariantes aprobados: eventos y revisiones inmutables, unicidad del checklist.
- Análisis retrospectivo reproducible sobre 120 facturas ficticias.

## Cierre pendiente fuera del entorno local

- V-03: repetir el análisis con datos reales autorizados.
- V-05: obtener dictamen de asesoría jurídica competente antes de contactar pagadores reales.
- V-07: conseguir 2–3 cartas de intención firmadas.
- Ejecutar la suite integral del backend cuando estén disponibles sus dependencias Python o una imagen backend adecuada. La imagen base Python está en caché, pero la capa de dependencias del proyecto no existe y la construcción offline se detiene en `pip`.

El procedimiento, los insumos y la evidencia exigida para estas tareas están preparados en `paquete-validacion-externa.md`.

Por estas dependencias, el **desarrollo local de la Fase 3 queda cerrado**, pero la fase no debe declararse validada comercial ni legalmente.
