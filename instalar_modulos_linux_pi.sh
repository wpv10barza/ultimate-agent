#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "---------------------------------------------"
echo "MINEXcellence - INSTALACION LINUX / RASPBERRY PI V6"
echo "---------------------------------------------"

echo "Instalando paquetes del sistema para audio..."
sudo apt update
sudo apt install -y portaudio19-dev python3-pyaudio espeak alsa-utils

echo "Creando entorno virtual .venv con paquetes del sistema visibles..."
python3 -m venv .venv --system-site-packages || python3 -m venv .venv
source .venv/bin/activate

echo "Actualizando pip..."
python -m pip install --upgrade pip setuptools wheel

echo "Instalando dependencias base..."
python -m pip install -r requirements.txt

echo "Verificando entorno..."
python verificar_entorno.py
python pretraining_status.py

echo "Listo. Ejecuta: python app.py"
