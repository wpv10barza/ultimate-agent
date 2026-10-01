# -*- coding: utf-8 -*-
"""
MINEXcellence 2025 - Diseno Las Aguilas
Aplicacion Tkinter integrada con Ollama local:
- functiongemma: extraccion/auditoria estructurada de variables.
- qwen3.5:4b: auditoria tecnica del diseno de voladura.
"""

import os
import json
import math
import platform
import queue
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime

# Opcional: para redimensionar la imagen del banner
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Intentamos importar pandas para Excel.
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Integracion local con Ollama / pocket-ai
try:
    from tool_ai import auditar_con_ollama, procesar_input_minero, enviar_a_tts_piper
    TOOL_AI_AVAILABLE = True
except Exception:
    TOOL_AI_AVAILABLE = False

# --- CONFIGURACION DE COLORES (ESTILO BLANCO/ROJO/AZUL) ---
COLOR_FONDO = "#FFFFFF"       # Blanco puro
COLOR_TEXTO = "#000000"       # Negro
COLOR_BORDE_AZUL = "#004B87"  # Azul fuerte
COLOR_BORDE_ROJO = "#D32F2F"  # Rojo intenso
COLOR_BTN_AZUL = "#0056b3"
COLOR_BTN_ROJO = "#c62828"
COLOR_BTN_VERDE = "#2E7D32"

# Ruta de imagen de cabecera. Si no existe, se despliega el banner textual azul.
RUTA_IMAGEN = os.environ.get("MINEXCELLENCE_BANNER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "Imagen1.png"))

# Ruta Windows solicitada para exportacion local del portatil.
RUTA_EXPORTACION = os.environ.get("MINEXCELLENCE_EXPORT_DIR", os.getcwd())

# Variables globales para guardar los ultimos resultados para Excel, TTS y voz
resultados_globales = {}
auditoria_global = {}
parametros_globales = {}
ultima_respuesta_tts = ""

# Cola para logs y respuestas del hilo de backend
log_queue = queue.Queue()


# -------------------------------------------------------------------
# 0. TERMINAL VISUAL / LOGS
# -------------------------------------------------------------------
def escribir_log(mensaje):
    """Encola mensajes de estado desde cualquier hilo sin bloquear Tkinter."""
    hora = datetime.now().strftime("%H:%M:%S")
    log_queue.put(("log", f"{hora} {mensaje}"))


def procesar_cola_logs():
    """Drena la cola de mensajes y actualiza la GUI en el hilo principal."""
    try:
        while True:
            item = log_queue.get_nowait()
            tipo = item[0]

            if tipo == "log":
                mensaje = item[1]
                txt_terminal.config(state=tk.NORMAL)
                txt_terminal.insert(tk.END, mensaje + "\n")
                txt_terminal.see(tk.END)
                txt_terminal.config(state=tk.DISABLED)

            elif tipo == "resultado":
                res_text, resultados, auditoria = item[1], item[2], item[3]
                global resultados_globales, auditoria_global, ultima_respuesta_tts
                resultados_globales = resultados
                auditoria_global = auditoria
                ultima_respuesta_tts = res_text

                lbl_resumen.config(text=res_text, fg=COLOR_BORDE_AZUL)
                btn_full.config(state=tk.NORMAL)
                btn_excel.config(state=tk.NORMAL)
                btn_calc.config(state=tk.NORMAL)
                btn_repetir.config(state=tk.NORMAL)
                escribir_log("[LOG - ROUTER]: Calculo finalizado. Interfaz actualizada.")
                canvas.yview_moveto(1)

            elif tipo == "voz":
                transcripcion, respuesta = item[1], item[2]
                btn_mic.config(state=tk.NORMAL)
                btn_repetir.config(state=tk.NORMAL)
                ultima_respuesta_tts = respuesta
                escribir_log(f"[LOG - MIC]: Transcripcion: {transcripcion}")
                escribir_log(f"[LOG - FUNCTIONGEMMA]: {respuesta}")

                prefijo = "EJECUTAR_CALCULO:"
                if isinstance(respuesta, str) and respuesta.startswith(prefijo):
                    try:
                        args = json.loads(respuesta[len(prefijo):].strip())
                        aplicar_parametros_extraidos(args)
                        lbl_resumen.config(
                            text="Datos extraidos por voz. Ejecutando calculo...",
                            fg=COLOR_BORDE_AZUL
                        )
                        root.after(250, calcular_voladura)
                    except Exception as exc:
                        lbl_resumen.config(text=f"No se pudo aplicar la extraccion: {exc}", fg=COLOR_BORDE_ROJO)
                else:
                    lbl_resumen.config(text=respuesta, fg=COLOR_BORDE_ROJO)
                    canvas.yview_moveto(1)

            elif tipo == "error":
                detalle = item[1]
                btn_calc.config(state=tk.NORMAL)
                lbl_resumen.config(text="Error durante el calculo.", fg=COLOR_BORDE_ROJO)
                escribir_log(f"[LOG - ERROR]: {detalle}")
                messagebox.showerror("Error", detalle)

    except queue.Empty:
        pass

    root.after(120, procesar_cola_logs)


# -------------------------------------------------------------------
# 1. LOGICA DE CALCULO (Kuz-Ram + Formato Minero)
# -------------------------------------------------------------------
def _get_float(entry, name):
    texto = entry.get().strip().replace(",", ".")
    if not texto:
        return 0.0
    try:
        return float(texto)
    except ValueError as exc:
        raise ValueError(f"El campo '{name}' debe ser numerico.") from exc


def leer_parametros_gui():
    """Extrae los 6 campos de entrada solicitados desde la interfaz."""
    parametros = {
        "ancho_seccion": _get_float(entry_ancho, "Ancho Seccion / Tajo (m)"),
        "avance": _get_float(entry_avance, "Avance / Altura (m)"),
        "diametro_taladro": _get_float(entry_diametro, "Diametro Taladro (mm)"),
        "densidad_explosivo": _get_float(entry_densidad_exp, "Densidad Explosivo (kg/m3)"),
        "densidad_roca": _get_float(entry_densidad_roca, "Densidad Roca (Ton/m3)"),
        "resistencia_roca": _get_float(entry_resistencia, "Resistencia Roca (MPa)"),
    }

    # El esquema de functiongemma recibe densidad_explosivo en g/cm3.
    # El nucleo Kuz-Ram interno trabaja en kg/m3. Si el usuario escribe 0.8, 1.0, 1.1, etc.,
    # se interpreta como g/cm3 y se convierte automaticamente a kg/m3.
    if 0 < parametros["densidad_explosivo"] <= 5:
        parametros["densidad_explosivo"] *= 1000.0

    reglas = {
        "ancho_seccion": "El ancho de seccion debe ser mayor que 0.",
        "avance": "El avance debe ser mayor que 0.",
        "diametro_taladro": "El diametro debe ser mayor que 0.",
        "densidad_explosivo": "La densidad del explosivo debe ser mayor que 0.",
        "densidad_roca": "La densidad de roca debe ser mayor que 0.",
        "resistencia_roca": "La resistencia de roca debe ser mayor que 0.",
    }
    for clave, mensaje in reglas.items():
        if parametros[clave] <= 0:
            raise ValueError(mensaje)

    return parametros


def ejecutar_nucleo_kuzram(parametros):
    """Nucleo deterministico con las formulas provistas por MINEXcellence."""
    d_mm = parametros["diametro_taladro"]
    resistencia_roca = parametros["resistencia_roca"]
    densidad_exp = parametros["densidad_explosivo"]
    densidad_roca = parametros["densidad_roca"]
    ancho_seccion = parametros["ancho_seccion"]
    avance = parametros["avance"]

    d_m²È="25¹Í¥„ˆ°€‰9¼¡…äÕ¹„É•ÍÁÕ•ÍÑ„Á…É„É•Á•Ñ¥È¸ˆ¤(€€€€€€€É•ÑÕÉ¸((€€€¥˜Q==1}%}Y%1	1è(€€€€€€€½¬€ô•¹Ù¥…É}…}ÑÑÍ}Á¥Á•È¡Ñ•áÑ¼°±½}…±±‰…¬õ•ÍÉ¥‰¥É}±½œ¤(€€€€€€€¥˜½¬è(€€€€€€€€€€€•ÍÉ¥‰¥É}±½œ ‰m1=€´QQMtèI•ÁÉ½‘Õ¥•¹‘¼Õ±Ñ¥µ„É•ÍÁÕ•ÍÑ„¸ˆ¤(€€€€€€€€€€€É•ÑÕÉ¸((€€€µ•ÍÍ…•‰½à¹Í¡½ÝÝ…É¹¥¹œ (€€€€€€€€‰QQL¹¼‘¥ÍÁ½¹¥‰±”ˆ°(€€€€€€€€‰9¼Í”ÁÕ‘¼É•ÁÉ½‘Õ¥ÈÙ½è¸Y•É¥™¥„ÅÕ”ÑÑÍ}Á¥Á•È¹Áä•ÍÑ”•¸±„…ÉÁ•Ñ„ä•©•ÕÑ„èÁåÑ¡½¸€µ´Á¥À¥¹ÍÑ…±°ÁåÑÑÍàÌ¸¸]¥¹‘½ÝÌÍ”¥¹Ñ•¹Ñ…É„MåÍÑ•´¹MÁ•• ½µ¼É•ÍÁ…±‘¼¸ˆ(€€€€¤(((Œ€´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´(Œ€Ð¸%9QIhI%€¡U$¤€¬	99H5%9a119(Œ€´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´´)É½½Ð€ôÑ¬¹Q¬ ¤)É½½Ð¹Ñ¥Ñ±” ‰5%9a•±±•¹”€ÈÀÈÔ€´¥Í•¹¼1…ÌÕ¥±…Ìˆ¤)É½½Ð¹½¹™¥ÕÉ”¡‰œõ=1=I}=9<¤((Œ€´´´´´´´´´	99HMUAI%=H=8%58€´´´´´´´´´´)‰…¹¹•É}™É…µ”€ôÑ¬¹É…µ”¡É½½Ð°‰œõ=1=I}=9<¤)‰…¹¹•É}™É…µ”¹Á…¬¡Í¥‘”ô‰Ñ½Àˆ°™¥±°ô‰àˆ¤()‰…¹¹•É}±…‰•°€ô9½¹”)¥µ…•¹}½É¥¥¹…°€ô9½¹”)½É¥}Ü€ô½É¥} €ô9½¹”()ÉÕÑ…}¥µ…•¹}±½…°€ô½Ì¹Á…Ñ ¹©½¥¸¡½Ì¹Á…Ñ ¹‘¥É¹…µ”¡½Ì¹Á…Ñ ¹…‰ÍÁ…Ñ ¡}}™¥±•}|¤¤°€‰%µ…•¸Ä¹Á¹œˆ¤)ÉÕÑ…}‰…¹¹•È€ôÉÕÑ…}¥µ…•¹}±½…°¥˜½Ì¹Á…Ñ ¹•á¥ÍÑÌ¡ÉÕÑ…}¥µ…•¹}±½…°¤•±Í”IUQ}%58()¥˜A%1}Y%1	1…¹½Ì¹Á…Ñ ¹•á¥ÍÑÌ¡ÉÕÑ…}‰…¹¹•È¤è(€€€¥µ…•¹}½É¥¥¹…°€ô%µ…”¹½Á•¸¡ÉÕÑ…}‰…¹¹•È¤(€€€½É¥}Ü°½É¥} €ô¥µ…•¹}½É¥¥¹…°¹Í¥é”((€€€É½½Ð¹•½µ•ÑÉä¡˜‰í½É¥}ÝõàÜØÀˆ¤((€€€¥µ…•¹}Ñ¬€ô%µ…•Q¬¹A¡½Ñ½%µ…”¡¥µ…•¹}½É¥¥¹…°¤(€€€‰…¹¹•É}±…‰•°€ôÑ¬¹1…‰•°¡‰…¹¹•É}™É…µ”°¥µ…”õ¥µ…•¹}Ñ¬°‰ôÀ¤(€€€‰…¹¹•É}±…‰•°¹¥µ…”€ô¥µ…•¹}Ñ¬(€€€‰…¹¹•É}±…‰•°¹Á…¬¡™¥±°ô‰àˆ°Í¥‘”ô‰Ñ½Àˆ¤((€€€‘•˜É•‘¥µ•¹Í¥½¹…É}‰…¹¹•È¡•Ù•¹Ð¤è(€€€€€€€¥˜•Ù•¹Ð¹Ý¥‘Ñ €ðô€À½È¥µ…•¹}½É¥¥¹…°¥Ì9½¹”è(€€€€€€€€€€€É•ÑÕÉ¸(€€€€€€€¹Õ•Ù½}…¹¡¼€ô•Ù•¹Ð¹Ý¥‘Ñ (€€€€€€€•Í…±„€ô¹Õ•Ù½}…¹¡¼€¼½É¥}Ü(€€€€€€€¹Õ•Ù½}…±Ñ¼€ô¥¹Ð¡½É¥} €¨•Í…±„¤(€€€€€€€¥µ}É•‘¥´€ô¥µ…•¹}½É¥¥¹…°¹É•Í¥é” (€€€€€€€€€€€€¡¹Õ•Ù½}…¹¡¼°¹Õ•Ù½}…±Ñ¼¤°(€€€€€€€€€€€%µ…”¹19i=L(€€€€€€€€¤(€€€€€€€¥µ}Ñ¬È€ô%µ…•Q¬¹A¡½Ñ½%µ…”¡¥µ}É•‘¥´¤(€€€€€€€‰…¹¹•É}±…‰•°¹½¹™¥œ¡¥µ…”õ¥µ}Ñ¬È¤(€€€€€€€‰…¹¹•É}±…‰•°¹¥µ…”€ô¥µ}Ñ¬È((€€€É½½Ð¹‰¥¹ ˆñ½¹™¥ÕÉ”øˆ°É•‘¥µ•¹Í¥½¹…É}‰…¹¹•È¤)•±Í”è(€€€‰…¹¹•É}±…‰•°€ôÑ¬¹1…‰•° (€€€€€€€‰…¹¹•É}™É…µ”°(€€€€€€€Ñ•áÐô‰5%9a•±±•¹”€ÈÀÈÔˆ°(€€€€€€€‰œõ=1=I}	=I}iU0°(€€€€€€€™œô‰Ý¡¥Ñ”ˆ°(€€€€€€€™½¹Ðô ‰É¥…°ˆ°€Äà°€‰‰½±ˆ¤°(€€€€€€€…¹¡½Èô‰Üˆ°(€€€€€€€Á…‘àôÈÀ°(€€€€€€€Á…‘äôÄÀ(€€€€¤(€€€‰…¹¹•É}±…‰•°¹Á…¬¡™¥±°ô‰àˆ°Í¥‘”ô‰Ñ½Àˆ¤((Œ€´´´´´´´´´IAI%9%A0MI=11	1€¡=I5Q<¤€´´´´´´´´´´)µ…¥¹}™É…µ”€ôÑ¬¹É…µ”¡É½½Ð°‰œõ=1=I}=9<¤)µ…¥¹}™É…µ”¹Á…¬¡™¥±°õÑ¬¹	=Q °•áÁ…¹õQÉÕ”¤()…¹Ù…Ì€ôÑ¬¹…¹Ù…Ì¡µ…¥¹}™É…µ”°‰œõ=1=I}=9<°¡¥¡±¥¡ÑÑ¡¥­¹•ÍÌôÀ¤)ÍÉ½±±‰…È€ôÑÑ¬¹MÉ½±±‰…È¡µ…¥¹}™É…µ”°½É¥•¹ÐõÑ¬¹YIQ%0°½µµ…¹õ…¹Ù…Ì¹åÙ¥•Ü¤)ÍÉ½±±‰…È¹Á…¬¡Í¥‘”õÑ¬¹I%!P°™¥±°õÑ¬¹d¤)…¹Ù…Ì¹Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹	=Q °•áÁ…¹õQÉÕ”¤()…¹Ù…Ì¹½¹™¥ÕÉ”¡åÍÉ½±±½µµ…¹õÍÉ½±±‰…È¹Í•Ð¤)½¹Ñ•¹Ñ}™É…µ”€ôÑ¬¹É…µ”¡…¹Ù…Ì°‰œõ=1=I}=9<°Á…‘àôÄÔ°Á…‘äôÄÔ¤)…¹Ù…Í}Ý¥¹‘½Ü€ô…¹Ù…Ì¹É•…Ñ•}Ý¥¹‘½Ü  À°€À¤°Ý¥¹‘½Üõ½¹Ñ•¹Ñ}™É…µ”°…¹¡½Èô‰¹Üˆ¤(()‘•˜½¹}½¹™¥ÕÉ”¡•Ù•¹Ð¤è(€€€…¹Ù…Ì¹½¹™¥ÕÉ”¡ÍÉ½±±É•¥½¸õ…¹Ù…Ì¹‰‰½à ‰…±°ˆ¤¤(€€€…¹Ù…Ì¹¥Ñ•µ½¹™¥œ¡…¹Ù…Í}Ý¥¹‘½Ü°Ý¥‘Ñ õ•Ù•¹Ð¹Ý¥‘Ñ ¤(()…¹Ù…Ì¹‰¥¹ ˆñ½¹™¥ÕÉ”øˆ°±…µ‰‘„”è…¹Ù…Ì¹¥Ñ•µ½¹™¥œ¡…¹Ù…Í}Ý¥¹‘½Ü°Ý¥‘Ñ õ”¹Ý¥‘Ñ ¤¤)½¹Ñ•¹Ñ}™É…µ”¹‰¥¹ ˆñ½¹™¥ÕÉ”øˆ°½¹}½¹™¥ÕÉ”¤((Œ€´´´MQ%1=LY%MU1L€´´´)™½¹Ñ}±‰°€ô€ ‰É¥…°ˆ°€ÄÀ°€‰‰½±ˆ¤)™½¹Ñ}•¹Ð€ô€ ‰É¥…°ˆ°€ÄÈ¤(()‘•˜É•…É}¥¹ÁÕÐ¡Á…É•¹Ð°±…‰•±}Ñ•áÐ°‘•™…Õ±Ð¤è(€€€™É…µ”€ôÑ¬¹É…µ” (€€€€€€€Á…É•¹Ð°(€€€€€€€‰œõ=1=I}=9<°(€€€€€€€¡¥¡±¥¡Ñ‰…­É½Õ¹õ=1=I}	=I}iU0°(€€€€€€€¡¥¡±¥¡ÑÑ¡¥­¹•ÍÌôÄ(€€€€¤(€€€™É…µ”¹Á…¬¡™¥±°õÑ¬¹`°Á…‘äôÔ¤((€€€±‰°€ôÑ¬¹1…‰•° (€€€€€€€™É…µ”°(€€€€€€€Ñ•áÐõ±…‰•±}Ñ•áÐ°(€€€€€€€‰œõ=1=I}=9<°(€€€€€€€™œõ=1=I}	=I}iU0°(€€€€€€€™½¹Ðõ™½¹Ñ}±‰°°(€€€€€€€…¹¡½Èô‰Üˆ(€€€€¤(€€€±‰°¹Á…¬¡™¥±°õÑ¬¹`°Á…‘àôÔ°Á…‘äô Ô°€À¤¤((€€€•¹Ð€ôÑ¬¹¹ÑÉä (€€€€€€€™É…µ”°(€€€€€€€‰œô‰Ý¡¥Ñ”ˆ°(€€€€€€€™œô‰‰±…¬ˆ°(€€€€€€€™½¹Ðõ™½¹Ñ}•¹Ð°(€€€€€€€É•±¥•˜õÑ¬¹1P(€€€€¤(€€€•¹Ð¹Á…¬¡™¥±°õÑ¬¹`°Á…‘àôÔ°Á…‘äôÔ°¥Á…‘äôÐ¤(€€€•¹Ð¹¥¹Í•ÉÐ À°‘•™…Õ±Ð¤(€€€É•ÑÕÉ¸•¹Ð(((Œ€´´´	I0=I5Q<€´´´)Ñ¬¹1…‰•° (€€€½¹Ñ•¹Ñ}™É…µ”°(€€€Ñ•áÐô‰%M9<Y=1UIˆ°(€€€‰œõ=1=I}=9<°(€€€™œõ=1=I}	=I}I=)<°(€€€™½¹Ðô ‰É¥…°ˆ°€ÄØ°€‰‰½±ˆ¤(¤¹Á…¬¡Á…‘äô À°€ÈÀ¤¤((Œ€´´´9QILQ=L€´´´)™É…µ•}‘…Ñ½Ì€ôÑ¬¹1…‰•±É…µ” (€€€½¹Ñ•¹Ñ}™É…µ”°(€€€Ñ•áÐôˆAI5QI=L€ˆ°(€€€‰œõ=1=I}=9<°(€€€™œõ=1=I}	=I}I=)<°(€€€™½¹Ðõ™½¹Ñ}±‰°°(€€€‰ôÈ°(€€€É•±¥•˜õÑ¬¹I==Y(¤)™É…µ•}‘…Ñ½Ì¹Á…¬¡™¥±°õÑ¬¹`¤()•¹ÑÉå}…¹¡¼€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰¹¡¼M•¥½¸€¼Q…©¼€¡´¤èˆ°€ˆÐ¸Àˆ¤)•¹ÑÉå}…Ù…¹”€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰Ù…¹”€¼±ÑÕÉ„€¡´¤èˆ°€ˆÄ¸Ôˆ¤)•¹ÑÉå}‘¥…µ•ÑÉ¼€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰¥…µ•ÑÉ¼Q…±…‘É¼€¡µ´¤èˆ°€ˆÐÔˆ¤)•¹ÑÉå}‘•¹Í¥‘…‘}•áÀ€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰•¹Í¥‘…áÁ±½Í¥Ù¼€¡­œ½´Ì¼œ½´Ì¤èˆ°€ˆÄÄÀÀˆ¤)•¹ÑÉå}‘•¹Í¥‘…‘}É½„€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰•¹Í¥‘…I½„€¡Q½¸½´Ì¤èˆ°€ˆÈ¸Üˆ¤)•¹ÑÉå}É•Í¥ÍÑ•¹¥„€ôÉ•…É}¥¹ÁÕÐ¡™É…µ•}‘…Ñ½Ì°€‰I•Í¥ÍÑ•¹¥„I½„€¡5A„¤èˆ°€ˆÄÈÀˆ¤((Œ€´´´	=Q=9L%=8€´´´)‰Ñ¹}…±Œ€ôÑ¬¹	ÕÑÑ½¸ (€€€½¹Ñ•¹Ñ}™É…µ”°(€€€Ñ•áÐô‰1U1HQ=Lˆ°(€€€‰œõ=1=I}	Q9}iU0°(€€€™œô‰Ý¡¥Ñ”ˆ°(€€€™½¹Ðô ‰É¥…°ˆ°€ÄÈ°€‰‰½±ˆ¤°(€€€½µµ…¹õ…±Õ±…É}Ù½±…‘ÕÉ„(¤)‰Ñ¹}…±Œ¹Á…¬¡™¥±°õÑ¬¹`°Á…‘äô ÈÀ°€ÄÀ¤°¥Á…‘äôÔ¤((Œ€´´´IMU1Q=LIMU5%=L€´´´)±‰±}É•ÍÕµ•¸€ôÑ¬¹1…‰•° (€€€½¹Ñ•¹Ñ}™É…µ”°(€€€Ñ•áÐô‰ÍÁ•É…¹‘¼…±Õ±¼¸¸¸ˆ°(€€€‰œôˆÁáˆ°(€€€™œôˆŒÔÔÔˆ°(€€€™½¹Ðô ‰½ÕÉ¥•È9•Üˆ°€ÄÈ°€‰‰½±ˆ¤°(€€€É•±¥•˜õÑ¬¹I%°(€€€Á…‘àôÄÀ°(€€€Á…‘äôÄÀ(¤)±‰±}É•ÍÕµ•¸¹Á…¬¡™¥±°õÑ¬¹`°Á…‘äôÄÀ¤((Œ€´´´	=Q=9LaQI€¡U11MI8€˜a0¤€´´´)™É…µ•}‰Ñ¹Ì€ôÑ¬¹É…µ”¡½¹Ñ•¹Ñ}™É…µ”°‰œõ=1=I}=9<¤)™É…µ•}‰Ñ¹Ì¹Á…¬¡™¥±°õÑ¬¹`°Á…‘äôÄÀ¤()‰Ñ¹}™Õ±°€ôÑ¬¹	ÕÑÑ½¸ (€€€™É…µ•}‰Ñ¹Ì°(€€€Ñ•áÐô‰YHU10MI8ˆ°(€€€‰œõ=1=I}	=I}iU0°(€€€™œô‰Ý¡¥Ñ”ˆ°(€€€ÍÑ…Ñ”õÑ¬¹%M	1°(€€€½µµ…¹õ…‰É¥É}™Õ±±ÍÉ••¸(¤)‰Ñ¹}™Õ±°¹Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹`°•áÁ…¹õQÉÕ”°Á…‘àô À°€Ð¤°¥Á…‘äôÔ¤()‰Ñ¹}•á•°€ôÑ¬¹	ÕÑÑ½¸ (€€€™É…µ•}‰Ñ¹Ì°(€€€Ñ•áÐô‰MIH€¹a1M`ˆ°(€€€‰œõ=1=I}	Q9}YI°(€€€™œô‰Ý¡¥Ñ”ˆ°(€€€ÍÑ…Ñ”õÑ¬¹%M	1°(€€€½µµ…¹õ•áÁ½ÉÑ…É}•á•°(¤)‰Ñ¹}•á•°¹Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹`°•áÁ…¹õQÉÕ”°Á…‘àôÐ°¥Á…‘äôÔ¤()‰Ñ¹}µ¥Œ€ôÑ¬¹	ÕÑÑ½¸ (€€€™É…µ•}‰Ñ¹Ì°(€€€Ñ•áÐô‹Â~:g¾â<!	1H€¡5%¤ˆ°(€€€‰œôˆŒÑÔÀˆ°(€€€™œô‰Ý¡¥Ñ”ˆ°(€€€™½¹Ðô ‰É¥…°ˆ°€ä°€‰‰½±ˆ¤°(€€€½µµ…¹õ…ÁÑÕÉ…É}…Õ‘¥½}ÕÍÕ…É¥¼(¤)‰Ñ¹}µ¥Œ¹Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹`°•áÁ…¹õQÉÕ”°Á…‘àôÐ°¥Á…‘äôÔ¤()‰Ñ¹}É•Á•Ñ¥È€ôÑ¬¹	ÕÑÑ½¸ (€€€™É…µ•}‰Ñ¹Ì°(€€€Ñ•áÐô‹Â~^¾â<IAQ%HY=hˆ°(€€€‰œôˆäàÀÀˆ°(€€€™œô‰Ý¡¥Ñ”ˆ°(€€€™½¹Ðô ‰É¥…°ˆ°€ä°€‰‰½±ˆ¤°(€€€ÍÑ…Ñ”õÑ¬¹%M	1°(€€€½µµ…¹õÉ•ÁÉ½‘Õ¥É}Õ±Ñ¥µ…}É•ÍÁÕ•ÍÑ„(¤)‰Ñ¹}É•Á•Ñ¥È¹Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹`°•áÁ…¹õQÉÕ”°Á…‘àô Ð°€À¤°¥Á…‘äôÔ¤((Œ€´´´QI5%90Y%MU0=1158Q%5A<I0€´´´)™É…µ•}Ñ•Éµ¥¹…°€ôÑ¬¹1…‰•±É…µ” (€€€½¹Ñ•¹Ñ}™É…µ”°(€€€Ñ•áÐôˆ=9M=11=0=115€¼I=UQH€ˆ°(€€€‰œõ=1=I}=9<°(€€€™œõ=1=I}	=I}I=)<°(€€€™½¹Ðõ™½¹Ñ}±‰°°(€€€‰ôÈ°(€€€É•±¥•˜õÑ¬¹I==Y(¤)™É…µ•}Ñ•Éµ¥¹…°¹Á…¬¡™¥±°õÑ¬¹	=Q °•áÁ…¹õ…±Í”°Á…‘äô ÄÈ°€Ô¤¤()Ñ•Éµ¥¹…±}ÍÉ½±°€ôÑ¬¹MÉ½±±‰…È¡™É…µ•}Ñ•Éµ¥¹…°¤)Ñ•Éµ¥¹…±}ÍÉ½±°¹Á…¬¡Í¥‘”õÑ¬¹I%!P°™¥±°õÑ¬¹d¤()ÑáÑ}Ñ•Éµ¥¹…°€ôÑ¬¹Q•áÐ (€€€™É…µ•}Ñ•Éµ¥¹…°°(€€€‰œôˆŒÀÀÀÀÀÀˆ°(€€€™œôˆŒÀÁØØˆ°(€€€¥¹Í•ÉÑ‰…­É½Õ¹ôˆŒÀÁØØˆ°(€€€™½¹Ðô ‰½¹Í½±…Ìˆ°€ä¤°(€€€¡•¥¡Ðôä°(€€€ÝÉ…ÀõÑ¬¹]=I°(€€€åÍÉ½±±½µµ…¹õÑ•Éµ¥¹…±}ÍÉ½±°¹Í•Ð°(€€€É•±¥•˜õÑ¬¹1P(¤)ÑáÑ}Ñ•Éµ¥¹…°¸Á…¬¡Í¥‘”õÑ¬¹1P°™¥±°õÑ¬¹	=Q °•áÁ…¹õQÉÕ”°Á…‘àôØ°Á…‘äôØ¤)Ñ•Éµ¥¹…±}ÍÉ½±°¹½¹™¥œ¡½µµ…¹õÑáÑ}Ñ•Éµ¥¹…°¹åÙ¥•Ü¤)ÑáÑ}Ñ•Éµ¥¹…°¹½¹™¥œ¡ÍÑ…Ñ”õÑ¬¹%M	1¤()Ñ¬¹1…‰•°¡½¹Ñ•¹Ñ}™É…µ”°Ñ•áÐôˆ€ˆ°‰œõ=1=I}=9<¤¹Á…¬¡Á…‘äôÄÈ¤()•ÍÉ¥‰¥É}±½œ ‰m1=€´MeMQ5tè5%9a•±±•¹”€ÈÀÈÔ±¥ÍÑ¼¸5…¹Õ…°°Ù½è°á•°ä‘…Ñ…Í•ÐP¡…‰¥±¥Ñ…‘½Ì¸ˆ¤)É½½Ð¹…™Ñ•È ÄÈÀ°ÁÉ½•Í…É}½±…}±½Ì¤)É½½Ð¹µ…¥¹±½½À ¤(