param(
    [string]$Destination = (Join-Path $PSScriptRoot "..\backups")
)

$ErrorActionPreference = "Stop"
$resolvedRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backupRoot = [System.IO.Path]::GetFullPath($Destination)
if (-not $backupRoot.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "El destino debe permanecer dentro del repositorio: $resolvedRoot"
}
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$databaseFile = Join-Path $backupRoot "database-$stamp.dump"
$receiptsFile = Join-Path $backupRoot "receipts-$stamp.tar.gz"
$databaseUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "miedificio" }
$databaseName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "miedificio" }

$dbContainer = docker compose ps -q db
$backendContainer = docker compose ps -q backend
if (-not $dbContainer -or -not $backendContainer) {
    throw "Los servicios db y backend deben estar ejecutándose."
}

docker exec $dbContainer pg_dump -U $databaseUser -d $databaseName -Fc -f /tmp/miedificio.dump
docker cp "${dbContainer}:/tmp/miedificio.dump" $databaseFile
docker exec $dbContainer rm -f /tmp/miedificio.dump

docker exec $backendContainer tar -czf /tmp/miedificio-receipts.tar.gz -C /data/uploads .
docker cp "${backendContainer}:/tmp/miedificio-receipts.tar.gz" $receiptsFile
docker exec $backendContainer rm -f /tmp/miedificio-receipts.tar.gz

Write-Output "Backup creado: $databaseFile"
Write-Output "Backup creado: $receiptsFile"
