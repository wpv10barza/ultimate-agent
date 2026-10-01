
# -*- coding: utf-8 -*-
"""
tts_piper.py
Modulo TTS compatible con MINEXcellence / pocket-ai.

Objetivo:
- Evitar el error: No module named 'tts_piper'.
- Exponer funciones compatibles con tool_ai.py: speak, decir, reproducir_texto y text_to_speech.
- En Windows usa pyttsx3 si esta instalado; si falla, usa System.Speech via PowerShell.
- En Linux/Raspberry Pi intenta comandos del sistema si existen: spd-say, espeak o pico2wave.

Nota:
Este archivo es un puente local. Si luego instalas Piper real, puedes reemplazar internamente
la funcion speak() por tu llamada a Piper, manteniendo el mismo nombre de funcion.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from typing import Optional


def _limpiar_texto(texto: object) -> str:
    txt = str(texto or "").strip()
    if not txt:
        return "Sin texto para reproducir."
    if len(txt) > 1800:
        txt = txt[:1800] + "..."
    return txt


def _speak_pyttsx3(texto: str) -> bool:
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.say(texto)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _speak_windows_powershell(texto: str) -> bool:
    if platform.system().lower() != "windows":
        return False
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return False
    safe = texto.replace("'", "''").replace("\r", " ").replace("\n", " ")
    comando = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = 0; $s.Volume = 100; "
        f"$s.Speak('{safe}')"
    )
    try:
        subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _speak_linux_basico(texto: str) -> bool:
    sistema = platform.system().lower()
    if sistema not in {"linux", "darwin"}:
        return False

    for cmd in ("spd-say", "espeak"):
        exe = shutil.which(cmd)
        if exe:
            try:
                subprocess.run([exe, texto], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass

    pico = shutil.which("pico2wave")
    aplay = shutil.which("aplay")
    if pico and aplay:
        wav_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                wav_path = tmp.name
            subprocess.run([pico, "-w", wav_path, texto], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([aplay, wav_path], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
    return False


def speak(texto: object) -> bool:
    """Funcion principal de voz. Retorna True si pudo intentar/reproducir TTS."""
    txt = _limpiar_texto(texto)
    if _speak_pyttsx3(txt):
        return True
    if _speak_windows_powershell(txt):
        return True
    if _speak_linux_basico(txt):
        return True
    print("[TTS] No hay motor de voz disponible. Texto:", txt)
    return False


def decir(texto: object) -> bool:
    return speak(texto)


def reproducir_texto(texto: object) -> bool:
    return speak(texto)


def text_to_speech(texto: object) -> bool:
    return speak(texto)


if __name__ == "__main__":
    import sys
    mensaje = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Prueba de voz MINEXcellence correcta."
    ok = speak(mensaje)
    print("tts_piper:", "ok" if ok else "no disponible")
