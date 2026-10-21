param(
    [string]$ProjectName = "recupera-release-rehearsal"
)

$ErrorActionPreference = "Stop"
if ($ProjectName -notmatch '^recupera-release-rehearsal(-[a-z0-9]+)?$') {
    throw "El proyecto debe usar el prefijo recupera-release-rehearsal."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $projectRoot "compose.yaml"
$verifyFile = Join-Path $projectRoot "compose.verify.yaml"
$temporaryRoot = Join-Path $projectRoot ".release-rehearsal"
$schemaPath = Join-Path $temporaryRoot "schema.sql"
$backupPath = Join-Path $temporaryRoot "recupera-release.dump"
$restoreDatabase = "recupera_release_restore"

New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null

function Invoke-Checked {
    param([scriptblock]$Command, [string]$FailureMessage)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

Push-Location $projectRoot
try {
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile up -d --wait db
    } "No fue posible iniciar PostgreSQL para el ensayo."

    $schema = & python scripts/render_schema_sql.py
    if ($LASTEXITCODE -ne 0) { throw "No fue posible renderizar el esquema." }
    [System.IO.File]::WriteAllLines($schemaPath, $schema, [System.Text.UTF8Encoding]::new($false))
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile cp $schemaPath db:/tmp/schema.sql
    } "No fue posible copiar el esquema al contenedor."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db psql --username recupera --dbname recupera --set ON_ERROR_STOP=1 --file /tmp/schema.sql
    } "La creación del esquema falló."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db psql --username recupera --dbname recupera --set ON_ERROR_STOP=1 --command "CREATE TABLE release_rehearsal_marker (value text PRIMARY KEY); INSERT INTO release_rehearsal_marker VALUES ('phase-8.4');"
    } "No fue posible insertar el marcador del ensayo."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db pg_dump --format=custom --username recupera --dbname recupera --file /tmp/release.dump
    } "No fue posible generar el respaldo."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile cp db:/tmp/release.dump $backupPath
    } "No fue posible extraer el respaldo."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db rm -f /tmp/release.dump
    } "No fue posible limpiar el respaldo temporal del contenedor."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile cp $backupPath db:/tmp/restore.dump
    } "No fue posible reingresar el respaldo para restaurarlo."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db createdb --username recupera $restoreDatabase
    } "No fue posible crear la base de restauración."
    Invoke-Checked {
        docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db pg_restore --exit-on-error --no-owner --username recupera --dbname $restoreDatabase /tmp/restore.dump
    } "La restauración del respaldo falló."

    $sourceCount = docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db psql --username recupera --dbname recupera --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
    if ($LASTEXITCODE -ne 0) { throw "No fue posible contar las tablas de origen." }
    $restoredCount = docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db psql --username recupera --dbname $restoreDatabase --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
    if ($LASTEXITCODE -ne 0) { throw "No fue posible contar las tablas restauradas." }
    $marker = docker compose -p $ProjectName -f $composeFile -f $verifyFile exec -T db psql --username recupera --dbname $restoreDatabase --tuples-only --no-align --command "SELECT value FROM release_rehearsal_marker;"
    if ($LASTEXITCODE -ne 0) { throw "No fue posible leer el marcador restaurado." }
    if ([int]$sourceCount -lt 38 -or [int]$sourceCount -ne [int]$restoredCount) {
        throw "El conteo de tablas no coincide: origen=$sourceCount restauración=$restoredCount."
    }
    if ($marker.Trim() -ne "phase-8.4") { throw "El marcador de datos no fue restaurado." }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backupPath).Hash.ToLowerInvariant()
    Write-Output "PASS release rehearsal"
    Write-Output "Tables: $($sourceCount.Trim())"
    Write-Output "Marker: $($marker.Trim())"
    Write-Output "Backup SHA-256: $hash"
} finally {
    docker compose -p $ProjectName -f $composeFile -f $verifyFile down --volumes --remove-orphans | Out-Null
    Pop-Location
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
