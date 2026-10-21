# Evidencia del ensayo de release 0.8.4

**Fecha:** 21 de octubre de 2026

**Entorno:** Docker local, PostgreSQL 16 Alpine, proyecto aislado `recupera-release-rehearsal`

**Resultado:** PASS

## Secuencia ejecutada

1. Se creó una red y un volumen exclusivos del ensayo, sin publicar el puerto de PostgreSQL.
2. Se renderizó y aplicó el esquema completo de la aplicación.
3. Se creó una tabla temporal de control y se insertó el marcador `phase-8.4`.
4. Se generó un `pg_dump` en formato custom y se copió fuera del contenedor.
5. Se eliminó la copia interna, se reingresó el archivo portable y se restauró en otra base.
6. Se comparó el número de tablas y se leyó el marcador desde la base restaurada.
7. Se eliminaron contenedor, volumen, red y archivos temporales.

## Resultado observado

| Control | Resultado |
|---|---|
| Tablas de origen | 38: 37 de aplicación + 1 marcador del ensayo |
| Tablas restauradas | 38 |
| Marcador restaurado | `phase-8.4` |
| Respaldo no vacío y hasheable | PASS |
| Recursos temporales eliminados | PASS |

La huella del dump cambia legítimamente entre ejecuciones por metadatos internos de PostgreSQL; se calcula para confirmar integridad durante cada ensayo, pero no se conserva el dump ni se usa como artefacto de release.

## Repetición

```powershell
.\scripts\rehearse-release.ps1
```

El script admite únicamente nombres de proyecto con el prefijo reservado `recupera-release-rehearsal`, usa una base desechable y ejecuta su limpieza en `finally`, incluso ante errores.
