@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0CREAR_EXE_WINDOWS.ps1"
pause
