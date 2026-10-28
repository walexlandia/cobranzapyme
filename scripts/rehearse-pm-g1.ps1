param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $projectRoot "compose.pm-g1-rehearsal.yaml"
$projectName = "recupera-pm-g1-rehearsal"
$upSucceeded = $false

function Invoke-Checked {
    param([scriptblock]$Command, [string]$FailureMessage)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

Push-Location $projectRoot
try {
    Invoke-Checked {
        docker compose -p $projectName -f $composeFile config --quiet
    } "La configuración del ensayo PM-G1 es inválida."
    Invoke-Checked {
        docker compose -p $projectName -f $composeFile up `
            --build `
            --abort-on-container-exit `
            --exit-code-from pm_g1_rehearsal
    } "Falló el ensayo integral de PM-G1."
    $upSucceeded = $true
} finally {
    docker compose -p $projectName -f $composeFile down --volumes --remove-orphans
    $downExitCode = $LASTEXITCODE
    Pop-Location
    if ($downExitCode -ne 0) {
        throw "No fue posible destruir el entorno temporal de PM-G1."
    }
}

$containers = @(docker ps -aq --filter "label=com.docker.compose.project=$projectName")
if ($LASTEXITCODE -ne 0 -or $containers.Count -ne 0) {
    throw "El ensayo dejó contenedores persistentes."
}
$networks = @(docker network ls -q --filter "label=com.docker.compose.project=$projectName")
if ($LASTEXITCODE -ne 0 -or $networks.Count -ne 0) {
    throw "El ensayo dejó redes persistentes."
}
$volumes = @(docker volume ls -q --filter "label=com.docker.compose.project=$projectName")
if ($LASTEXITCODE -ne 0 -or $volumes.Count -ne 0) {
    throw "El ensayo dejó volúmenes persistentes."
}
if (-not $upSucceeded) {
    throw "El ensayo PM-G1 no llegó a completarse."
}

Write-Output "PASS PM-G1 rehearsal: approved -> revoked -> blocked; entorno destruido"
