param(
    [string]$Modelo = "functiongemma",
    [string]$Dataset = "training_data.jsonl"
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "MINEXcellence - Indicador de preentrenamiento" -ForegroundColor Cyan
Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "Carpeta: $PSScriptRoot"
Write-Host "Modelo:  $Modelo"
Write-Host "Dataset: $Dataset"
Write-Host ""

python .\pretraining_status.py --model $Modelo --dataset $Dataset

Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor Yellow
Write-Host "  ollama pull functiongemma"
Write-Host "  python tool_ai.py 'avance 3 metros, taladro 45 mm'"
Write-Host "  python app.py"
