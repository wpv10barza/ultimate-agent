# MINEXcellence - Indicator for voice, TTS and local models.
$ErrorActionPreference = "Continue"
Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "INDICADOR DE MODULOS VOZ / TTS / OLLAMA V6" -ForegroundColor Cyan
Write-Host "---------------------------------------------" -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\python.exe") {
    $py = ".\.venv\Scripts\python.exe"
} else {
    $py = "python"
}

$code = @'
import importlib.util, sys, platform
mods = [
    ('ollama','Cliente local Ollama','base'),
    ('pandas','Exportacion Excel','base'),
    ('openpyxl','Motor .xlsx','base'),
    ('speech_recognition','Reconocimiento voz base','voice'),
    ('pyaudio','Microfono con SpeechRecognition','voice_optional'),
    ('pyttsx3','TTS local Windows','tts'),
    ('tts_piper','Modulo puente TTS del proyecto','tts'),
    ('semantic_router','Router semantico opcional','optional'),
]
print('Sistema:', platform.system())
for mod, desc, kind in mods:
    ok = importlib.util.find_spec(mod) is not None
    bar = '[########################]' if ok else '[------------------------]'
    label = 'ok' if ok else ('opcional faltante' if kind in ('voice_optional','optional') else 'faltante')
    print(f'{mod:22s} {bar} {label:18s} - {desc}')
print('Python usado:', sys.executable)
'@
& $py -c $code

Write-Host ""
Write-Host "---------------------------------------------" -ForegroundColor Cyan
Write-Host "OLLAMA LIST" -ForegroundColor Cyan
Write-Host "---------------------------------------------" -ForegroundColor Cyan
try { ollama list } catch { Write-Host "Ollama CLI no encontrado o no abierto." -ForegroundColor Yellow }

Write-Host ""
Write-Host "Instalacion corregida recomendada en Windows:" -ForegroundColor Yellow
Write-Host "  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass"
Write-Host "  .\instalar_modulos_windows.ps1"
Write-Host ""
Write-Host "Si solo falta PyAudio:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python -m pip install -r requirements-voice-windows.txt"
Write-Host ""
Write-Host "Si usas Linux/Raspberry Pi:" -ForegroundColor Yellow
Write-Host "  sudo apt install -y portaudio19-dev python3-pyaudio espeak alsa-utils"
Write-Host "  python3 -m venv .venv --system-site-packages"
Write-Host ""
Write-Host "Router semantico opcional:" -ForegroundColor Yellow
Write-Host "  python -m pip install -r requirements-router.txt"
