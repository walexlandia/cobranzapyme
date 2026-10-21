param(
    [switch]$IncludeRestoreRehearsal,
    [string]$WebImage = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-Checked {
    param([scriptblock]$Command, [string]$FailureMessage)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

Push-Location $projectRoot
try {
    Invoke-Checked { python -m compileall backend/app backend/tests scripts } "Falló compileall."
    Invoke-Checked { python scripts/release_readiness.py } "Falló release readiness local."
    Invoke-Checked { python scripts/generate_dependency_inventory.py --check } "El inventario de dependencias está desactualizado."
    Invoke-Checked { python scripts/offline_checks.py } "Fallaron las comprobaciones offline."
    Invoke-Checked {
        docker compose --env-file .env.example -f compose.yaml -f compose.secure.yaml -f compose.pilot.yaml config --quiet
    } "La configuración Compose del piloto es inválida."
    $pilotConfigJson = docker compose --env-file .env.example -f compose.yaml -f compose.secure.yaml -f compose.pilot.yaml config --format json
    if ($LASTEXITCODE -ne 0) { throw "No fue posible inspeccionar Compose del piloto." }
    $pilotConfig = $pilotConfigJson | ConvertFrom-Json
    foreach ($serviceName in @("db", "minio")) {
        $publishedPorts = $pilotConfig.services.$serviceName.ports
        if ($null -ne $publishedPorts -and @($publishedPorts).Count -ne 0) {
            throw "$serviceName no debe publicar puertos en el perfil piloto."
        }
    }
    foreach ($serviceName in @("api", "worker", "web")) {
        $mountedVolumes = $pilotConfig.services.$serviceName.volumes
        if ($null -ne $mountedVolumes -and @($mountedVolumes).Count -ne 0) {
            throw "$serviceName no debe usar bind mounts en el perfil piloto."
        }
    }
    $apiCommand = [string]::Join(" ", @($pilotConfig.services.api.command))
    if ($apiCommand -match "app\.seed|--reload") {
        throw "El perfil piloto no puede ejecutar seed ni reload."
    }
    if ($WebImage) {
        Invoke-Checked {
            docker image inspect $WebImage | Out-Null
        } "La imagen web local indicada no existe."
        $webWorkdir = docker image inspect --format "{{.Config.WorkingDir}}" $WebImage
        if ($LASTEXITCODE -ne 0) { throw "No fue posible inspeccionar el directorio de trabajo de la imagen web." }
        $webWorkdir = ([string]$webWorkdir).Trim()
        if ([string]::IsNullOrWhiteSpace($webWorkdir) -or $webWorkdir -eq "/") {
            $webWorkdir = "/app"
        }
        Invoke-Checked {
            docker run --rm -v "${projectRoot}/web/package-lock.json:${webWorkdir}/package-lock.json:ro" $WebImage node -e "const path=require('path'); const root=process.cwd(); const lock=require(path.join(root,'package-lock.json')); for (const name of ['next','react','react-dom']) { const expected=lock.packages['node_modules/'+name].version; const actual=require(path.join(root,'node_modules',name,'package.json')).version; if(actual!==expected) throw new Error(name+': expected '+expected+', got '+actual); }"
        } "La imagen web no coincide con las dependencias directas fijadas."
        Invoke-Checked {
            docker run --rm -v "${projectRoot}/web/app:${webWorkdir}/app:ro" -v "${projectRoot}/web/next.config.mjs:${webWorkdir}/next.config.mjs:ro" -v "${webWorkdir}/.next" $WebImage npm run build
        } "Falló el build web de producción."
    } else {
        Write-Output "SKIP web build: indique -WebImage para validar con una imagen local."
    }
    if ($IncludeRestoreRehearsal) {
        & (Join-Path $PSScriptRoot "rehearse-release.ps1")
        if ($LASTEXITCODE -ne 0) { throw "Falló el ensayo de restauración." }
    } else {
        Write-Output "SKIP restore rehearsal: use -IncludeRestoreRehearsal para ejecutarlo."
    }
    Write-Output "PASS local release verification"
} finally {
    Pop-Location
}
