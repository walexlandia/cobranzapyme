param(
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
if (-not $resolvedOutput.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "El directorio de respaldo debe estar dentro del proyecto."
}
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$fileName = "recupera-$stamp.dump"
$containerPath = "/tmp/$fileName"
$databaseUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "recupera" }
$databaseName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "recupera" }

Push-Location $projectRoot
try {
    docker compose exec -T db pg_dump --format=custom --username $databaseUser --dbname $databaseName --file $containerPath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump falló con código $LASTEXITCODE" }
    docker compose cp "db:$containerPath" (Join-Path $resolvedOutput $fileName)
    if ($LASTEXITCODE -ne 0) { throw "No fue posible copiar el respaldo" }
    docker compose exec -T db rm -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw "No fue posible limpiar el temporal del contenedor" }
} finally {
    Pop-Location
}

$backup = Get-Item -LiteralPath (Join-Path $resolvedOutput $fileName)
if ($backup.Length -le 0) { throw "El respaldo generado está vacío" }
Write-Output $backup.FullName
