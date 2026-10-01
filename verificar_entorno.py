# -*- coding: utf-8 -*-
"""Verificacion rapida del entorno local para MINEXcellence Ultimate Agent."""
import importlib.util
import json
import os
import platform
import subprocess
import sys

paquetes = [
    ("ollama", "ollama", "base"),
    ("pandas", "pandas", "base"),
    ("openpyxl", "openpyxl", "base"),
    ("PIL", "pillow", "base"),
    ("speech_recognition", "SpeechRecognition", "voz"),
    ("pyaudio", "PyAudio", "voz_opcional"),
    ("pyttsx3", "pyttsx3", "tts"),
    ("tts_piper", "tts_piper.py local", "tts"),
    ("semantic_router", "semantic-router[local]", "opcional"),
]
print("---------------------------------------------")
print("VERIFICACION DE ENTORNO PYTHON V6")
print("---------------------------------------------")
print("Sistema:", platform.system())
for modulo, nombre_pip, tipo in paquetes:
    estado = "ok" if importlib.util.find_spec(modulo) else "faltante"
    etiqueta = estado
    if estado == "faltante" and tipo in {"voz_opcional", "opcional"}:
        etiqueta = "opcional faltante"
    print(f"{modulo}: {etiqueta}")
    if estado == "faltante":
        if modulo == "pyaudio":
            if platform.system().lower() == "windows":
                print("  instalar dentro de .venv: python -m pip install -r requirements-voice-windows.txt")
                print("  si falla: usa Python 3.11/3.12 o instala Microsoft C++ Build Tools")
            else:
                print("  Linux/Pi: sudo apt install portaudio19-dev python3-pyaudio")
                print("  crea .venv con: python3 -m venv .venv --system-site-packages")
        elif modulo == "tts_piper":
            print("  debe existir el archivo tts_piper.py en esta carpeta")
        elif modulo == "semantic_router":
            print("  opcional: python -m pip install -r requirements-router.txt")
        else:
            print(f"  instalar: python -m pip install {nombre_pip}")

print("\n---------------------------------------------")
print("VERIFICACION ARCHIVOS BASE")
print("---------------------------------------------")
for archivo in [
    "tools.json", "tool_ai.py", "tts_piper.py", "training_data.jsonl",
    "pretraining_status.py", "ver_preentrenamiento.ps1", "ver_modulos_voz_tts.ps1",
    "requirements.txt", "requirements-voice-windows.txt", "requirements-router.txt"
]:
    print(f"{archivo}: {'ok' if os.path.exists(archivo) else 'faltante'}")

try:
    with open("tools.json", "r", encoding="utf-8") as f:
        herramientas = json.load(f)
    req = herramientas[0]["function"]["parameters"].get("required", [])
    print("required tools.json:", ", ".join(req))
except Exception as exc:
    print("tools.json: error", exc)

print("\n---------------------------------------------")
print("VERIFICACION OLLAMA CLI")
print("---------------------------------------------")
try:
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
    if r.returncode == 0:
        print("ollama cli: ok")
        print(r.stdout.strip() or "Sin modelos listados.")
    else:
        print("ollama cli: error")
        print((r.stderr or r.stdout).strip())
except FileNotFoundError:
    print("ollama cli: faltante. Instala Ollama Desktop y abrelo antes de ejecutar la app.")
except Exception as exc:
    print(f"ollama cli: error - {exc}")

print("\n---------------------------------------------")
print("PRUEBA TTS LOCAL")
print("---------------------------------------------")
try:
    import tts_piper  # type: ignore
    funciones = [n for n in ("speak", "decir", "reproducir_texto", "text_to_speech") if hasattr(tts_piper, n)]
    print("tts_piper funciones:", ", ".join(funciones) if funciones else "sin funciones compatibles")
except Exception as exc:
    print("tts_piper import: error", exc)

print("\nPython usado:", sys.executable)
