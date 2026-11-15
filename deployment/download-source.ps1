$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$target = Join-Path $root 'data/backups/WideWorldImporters-Full.bak'
if (Test-Path -LiteralPath $target) { throw 'El backup ya existe; verificarlo antes de descargar de nuevo.' }
New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null
$partial = "$target.partial"
curl.exe -fL -C - --retry 2 --connect-timeout 30 --speed-time 180 --speed-limit 1024 -o $partial 'https://github.com/microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak'
if ($LASTEXITCODE -ne 0) { throw 'Descarga fallida; no restaurar un archivo parcial.' }
Move-Item -LiteralPath $partial -Destination $target
Get-FileHash -LiteralPath $target -Algorithm SHA256
