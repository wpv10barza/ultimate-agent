# MINEXcellence - Corrected Windows installer for modules, voice and TTS.
# Run inside the project folder.
# Usage:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\instalar_modulos_windows.ps1
# Optional:
#   .\instalar_modulos_windows.ps1 -InstallRouter

param(
    [switch]$InstallRouter
)

$ErrorActionPreference = "Continue"
Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "MINEXcellence - INSTALACION WINDOWS V6" -ForegroundColor Cyan
Write-Host "---------------------------------------------" -ForegroundColor Cyan

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv..." -ForegroundColor Yellow
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        python -m venv .venv
    }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "ERROR: no se pudo crear .venv. Verifica tu instalacion de Python." -ForegroundColor Red
    exit 1
}

$py = ".\.venv\Scripts\python.exe"

Write-Host "Actualizando pip, setuptools y wheel..." -ForegroundColor Yellow
& $py -m pip install --upgrade pip setuptools wheel

Write-Host "Instalando dependencias base desde requirements.txt..." -ForegroundColor Yellow
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: fallo la instalacion base. Revisa el log anterior." -ForegroundColor Red
    exit 1
}

Write-Host "Instalando PyAudio para el boton HABLAR (MIC)..." -ForegroundColor Yellow
& $py -m pip install -r requirements-voice-windows.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: PyAudio no se pudo instalar automaticamente." -ForegroundColor Yellow
    Write-Host "La app funciona sin microfono, pero el boton HABLAR necesitara PyAudio." -ForegroundColor Yellow
    Write-Host "Soluciones recomendadas en Windows:" -ForegroundColor Yellow
    Write-Host "  1) Usa Python 3.11 o 3.12 en .venv."
    Write-Host "  2) Ejecuta: .\.venv\Scripts\python.exe -m pip install PyAudio"
    Write-Host "  3) Si compila y falla, instala Microsoft C++ Build Tools."
}

if ($InstallRouter) {
    Write-Host "Instalando semantic-router opcional..." -ForegroundColor Yellow
    & $py -m pip install -r requirements-router.txt
}

Write-Host ""
Write-Host "Verificando entorno..." -ForegroundColor Cyan
& $py verificar_entorno.py

Write-Host ""
Write-Host "Indicador de preentrenamiento..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\ver_preentrenamiento.ps1

Write-Host ""
Write-Host "Indicador de voz y TTS..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\ver_modulos_voz_tts.ps1

Write-Host ""
Write-Host "Comandos finales recomendados:" -ForegroundColor Green
Write-Host "  ollama pull functiongemma"
Write-Host "  ollama pull qwen3.5:4b"
Write-Host "  .\.venv\Scripts\python.exe app.py"
