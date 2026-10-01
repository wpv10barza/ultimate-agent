@echo off
setlocal
cd /d "%~dp0"
echo ---------------------------------------------
echo MINEXcellence - INSTALACION WINDOWS CMD V6
echo ---------------------------------------------

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 python -m venv .venv
)

set PY=.venv\Scripts\python.exe
%PY% -m pip install --upgrade pip setuptools wheel
%PY% -m pip install -r requirements.txt
%PY% -m pip install -r requirements-voice-windows.txt

echo.
%PY% verificar_entorno.py
echo.
echo Ejecuta:
echo   ollama pull functiongemma
echo   ollama pull qwen3.5:4b
echo   %PY% app.py
pause
