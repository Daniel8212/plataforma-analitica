$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $projectRoot 'data/tools/ollama-v0.40.16/ollama.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Ejecutar python -m deployment.prepare_ollama primero.' }
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $projectRoot 'data/ollama/models'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_KEEP_ALIVE = '2m'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_CONTEXT_LENGTH = '2048'
$env:OLLAMA_VULKAN = 'false'
& $runtime serve
