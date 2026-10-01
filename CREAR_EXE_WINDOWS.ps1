# ==========================================================
# MINEXcellence 2025 - Crear ejecutable EXE en Windows
# V9: corrige error runtime "ImportError: No module named app".
# Ejecutar desde PowerShell dentro de la carpeta del proyecto:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\CREAR_EXE_WINDOWS.ps1
# ==========================================================

$ErrorActionPreference = "Stop"

# 1. Ruta base del proyecto / libreria
$rutaLibreria = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rutaLibreria

$nombreExe = "MINEXcellence_2025"
$rutaVenv = Join-Path $rutaLibreria ".venv"
$rutaPythonVenv = Join-Path $rutaVenv "Scripts\python.exe"
$rutaScriptPy = Join-Path $rutaLibreria "launcher_minexcellence_temp.py"

Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "CREADOR DE EXE - MINEXcellence 2025" -ForegroundColor Cyan
Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "Carpeta del proyecto: $rutaLibreria" -ForegroundColor Gray

if (!(Test-Path (Join-Path $rutaLibreria "app.py"))) {
    Write-Host "[-] Error: no se encontro app.py en la carpeta del proyecto." -ForegroundColor Red
    Write-Host "    Ejecuta este script dentro de la carpeta donde estan app.py, tool_ai.py y tools.json." -ForegroundColor Red
    exit 1
}

# 2. Crear o reutilizar entorno virtual del proyecto
if (!(Test-Path $rutaPythonVenv)) {
    Write-Host "[+] Creando entorno virtual .venv..." -ForegroundColor Yellow
    try {
        py -3.11 -m venv .venv
    } catch {
        python -m venv .venv
    }
}

if (!(Test-Path $rutaPythonVenv)) {
    Write-Host "[-] Error: No se pudo crear .venv. Verifica Python 3.11 o superior." -ForegroundColor Red
    exit 1
}

# 3. Instalar dependencias base y PyInstaller en el venv correcto
Write-Host "[+] Actualizando pip, setuptools y wheel..." -ForegroundColor Yellow
& $rutaPythonVenv -m pip install --upgrade pip setuptools wheel

if (Test-Path "requirements.txt") {
    Write-Host "[+] Instalando requirements.txt..." -ForegroundColor Yellow
    & $rutaPythonVenv -m pip install -r requirements.txt
}

if (Test-Path "requirements-exe.txt") {
    Write-Host "[+] Instalando requirements-exe.txt..." -ForegroundColor Yellow
    & $rutaPythonVenv -m pip install -r requirements-exe.txt
} else {
    Write-Host "[+] Instalando PyInstaller..." -ForegroundColor Yellow
    & $rutaPythonVenv -m pip install pyinstaller
}

# Dependencias opcionales de voz. No se fuerza PyAudio para evitar romper la compilacion.
if (Test-Path "requirements-voice-windows.txt") {
    Write-Host "[i] Voz/Microfono opcional: PyAudio no se instala automaticamente para evitar fallos de build." -ForegroundColor DarkYellow
    Write-Host "    Si quieres microfono en el EXE, instala antes:" -ForegroundColor DarkYellow
    Write-Host "    .\.venv\Scripts\python.exe -m pip install -r requirements-voice-windows.txt" -ForegroundColor DarkYellow
}

# 4. Crear archivo .py temporal tipo launcher solucionado
# IMPORTANTE V9:
# El launcher ahora importa app de forma estatica: "import app".
# Antes usaba runpy.run_module("app"), y PyInstaller no detectaba ese import dinamico,
# por eso el EXE fallaba con: ImportError: No module named app.
$codigoPythonSolucionado = @'
# -*- coding: utf-8 -*-
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

# Permite que app.py encuentre archivos empaquetados en onefile y que los modulos locales se importen.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if EXE_DIR not in sys.path:
    sys.path.insert(0, EXE_DIR)

os.environ.setdefault("MINEXCELLENCE_BASE_DIR", BASE_DIR)
os.environ.setdefault("MINEXCELLENCE_EXE_DIR", EXE_DIR)
os.chdir(BASE_DIR)

# Import estatico para que PyInstaller incluya app.py y sus imports locales.
import app  # noqa: F401
'@

[System.IO.File]::WriteAllText($rutaScriptPy, $codigoPythonSolucionado, [System.Text.Encoding]::UTF8)

# 5. Compilar usando PyInstaller.
# Nota: en Windows el separador de --add-data es punto y coma (;).
Write-Host "[+] Compilando el ejecutable .EXE..." -ForegroundColor Yellow

$argumentos = @(
    "--clean",
    "--onefile",
    "--console",
    "--name=$nombreExe",
    "--add-data", "app.py;.",
    "--add-data", "tool_ai.py;.",
    "--add-data", "tts_piper.py;.",
    "--add-data", "tools.json;.",
    "--add-data", "training_data.jsonl;.",
    "--add-data", "diccionario_minero.json;.",
    "--hidden-import=app",
    "--hidden-import=tool_ai",
    "--hidden-import=tts_piper",
    "--hidden-import=ollama",
    "--hidden-import=pandas",
    "--hidden-import=openpyxl",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageTk",
    "--hidden-import=pyttsx3",
    "--hidden-import=pyttsx3.drivers",
    "--hidden-import=pyttsx3.drivers.sapi5",
    "--collect-submodules", "pyttsx3",
    "--collect-submodules", "openpyxl",
    $rutaScriptPy
)

# Si el modulo de microfono existe dentro del .venv, se agrega al EXE.
try {
    & $rutaPythonVenv -c "import speech_recognition" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $argumentos = @("--hidden-import=speech_recognition") + $argumentos
        Write-Host "[+] SpeechRecognition detectado: se incluira en el EXE." -ForegroundColor Green
    }
} catch {}

try {
    & $rutaPythonVenv -c "import pyaudio" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $argumentos = @("--hidden-import=pyaudio") + $argumentos
        Write-Host "[+] PyAudio detectado: se incluira en el EXE para microfono." -ForegroundColor Green
    } else {
        Write-Host "[i] PyAudio no detectado: el EXE funcionara, pero el microfono seguira como opcional." -ForegroundColor DarkYellow
    }
} catch {}

# Si existe Imagen1.png local, tambien se empaqueta.
if (Test-Path "Imagen1.png") {
    $argumentos = @("--add-data", "Imagen1.png;.") + $argumentos
}

# Elimina residuos anteriores para evitar que se ejecute un EXE viejo por error.
Remove-Item -Path "build", "dist", "$nombreExe.spec" -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $rutaLibreria "$nombreExe.exe") -Force -ErrorAction SilentlyContinue

& $rutaPythonVenv -m PyInstaller @argumentos

# 6. Mover el ejecutable y limpiar archivos residuales
$rutaExeGenerado = Join-Path $rutaLibreria "dist\$nombreExe.exe"
$rutaExeFinal = Join-Path $rutaLibreria "$nombreExe.exe"

if (Test-Path $rutaExeGenerado) {
    Move-Item -Path $rutaExeGenerado -Destination $rutaExeFinal -Force
    Remove-Item -Path "build", "dist", "$nombreExe.spec", $rutaScriptPy -Recurse -ErrorAction SilentlyContinue
    Write-Host "`n[+] Ejecutable creado con exito en:" -ForegroundColor Green
    Write-Host "    $rutaExeFinal" -ForegroundColor Green
    Write-Host "`n[i] Esta V9 corrige el error: ImportError: No module named app" -ForegroundColor Cyan
    Write-Host "[i] Antes de usar IA local, manten abierto Ollama y verifica modelos:" -ForegroundColor Cyan
    Write-Host "    ollama list" -ForegroundColor Gray
    Write-Host "    ollama pull functiongemma" -ForegroundColor Gray
    Write-Host "    ollama pull qwen3.5:4b" -ForegroundColor Gray
} else {
    Write-Host "[-] Error: No se pudo generar el archivo .exe." -ForegroundColor Red
    Write-Host "    Verifica que Python, pip y PyInstaller funcionen dentro de .venv." -ForegroundColor Red
    exit 1
}
