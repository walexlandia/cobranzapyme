param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
$backupRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
if (-not $resolvedBackup.StartsWith($backupRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Solo se verifican respaldos ubicados en el directorio backups del proyecto."
}
$suffix = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$restoreDatabaseName = "recupera_restore_verify_$suffix"
$containerPath = "/tmp/restore-$suffix.dump"
$databaseUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "recupera" }
if ($restoreDatabaseName -notmatch '^recupera_restore_verify_[0-9]{14}$') {
    throw "Nombre temporal inválido"
}

Push-Location $projectRoot
try {
    docker compose cp $resolvedBackup "db:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw "No fue posible copiar el respaldo al contenedor" }
    docker compose exec -T db createdb --username $databaseUser $restoreDatabaseName
    if ($LASTEXITCODE -ne 0) { throw "No fue posible crear la base temporal" }
    docker compose exec -T db pg_restore --exit-on-error --no-owner --username $databaseUser --dbname $restoreDatabaseName $containerPath
    if ($LASTEXITCODE -ne 0) { throw "La restauración falló" }
    $tableCount = docker compose exec -T db psql --username $databaseUser --dbname $restoreDatabaseName --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
    if ($LASTEXITCODE -ne 0 -or [int]$tableCount -lt 10) {
        throw "La base restaurada no contiene el esquema esperado"
    }
    Write-Output "PASS restore verified: $tableCount public tables"
} finally {
    docker compose exec -T db dropdb --if-exists --username $databaseUser $restoreDatabaseName | Out-Null
    docker compose exec -T db rm -f $containerPath | Out-Null
    Pop-Location
}
