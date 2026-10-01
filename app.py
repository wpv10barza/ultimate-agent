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
                res_tts = item[4] if len(item) > 4 else res_text
                global resultados_globales, auditoria_global, ultima_respuesta_tts
                resultados_globales = resultados
                auditoria_global = auditoria
                ultima_respuesta_tts = res_tts

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

    d_m = d_mm / 1000.0

    # K_burden condicional provisto: roca <= 150 MPa usa 25; roca mas resistente usa 22.
    k_burden = 25.0 if resistencia_roca <= 150.0 else 22.0

    burden = k_burden * d_m
    espaciamiento = 1.2 * burden
    taco = 10.0 * d_m
    sobreperforacion = 5.0 * d_m

    longitud_taladro = avance + sobreperforacion
    longitud_carga = max(longitud_taladro - taco, 0.0)

    area_taladro = math.pi * (d_m / 2.0) ** 2
    volumen_carga = area_taladro * longitud_carga
    peso_explosivo_taladro = volumen_carga * densidad_exp

    volumen_roto_taladro = burden * espaciamiento * avance
    toneladas_rotas = volumen_roto_taladro * densidad_roca

    fc_volumetrico = (
        peso_explosivo_taladro / volumen_roto_taladro
        if volumen_roto_taladro > 0 else 0.0
    )
    fc_lineal = (
        peso_explosivo_taladro / longitud_carga
        if longitud_carga > 0 else 0.0
    )
    factor_potencia = (
        peso_explosivo_taladro / toneladas_rotas
        if toneladas_rotas > 0 else 0.0
    )

    # Fragmentacion X50 segun formula provista en el codigo original.
    x50_cm = 10.0 * burden * (fc_volumetrico ** 0.8) * 100.0

    resultados = {
        "Parametros": [
            "Ancho Seccion (Ref)", "Longitud Avance", "Diametro Taladro",
            "Resistencia Roca", "Densidad Explosivo", "Densidad Roca",
            "K Burden", "Burden (Calc)", "Espaciamiento (Calc)", "Taco",
            "Sobreperforacion", "Longitud Taladro", "Longitud Carga",
            "Area Taladro", "Volumen Carga", "Volumen Roto / Tal",
            "Toneladas Rotas", "Carga Operante (Kg/Tal)",
            "FACTOR DE CARGA", "FACTOR DE CARGA LINEAL",
            "FACTOR DE POTENCIA", "Fragmentacion X50"
        ],
        "Unidad": [
            "m", "m", "mm", "MPa", "kg/m3", "Ton/m3",
            "-", "m", "m", "m", "m", "m", "m", "m2", "m3", "m3",
            "Ton", "Kg", "Kg/m3", "Kg/m", "Kg/Ton", "cm"
        ],
        "Total": [
            round(ancho_seccion, 3), round(avance, 3), round(d_mm, 3),
            round(resistencia_roca, 3), round(densidad_exp, 3),
            round(densidad_roca, 3), round(k_burden, 2),
            round(burden, 3), round(espaciamiento, 3), round(taco, 3),
            round(sobreperforacion, 3), round(longitud_taladro, 3),
            round(longitud_carga, 3), round(area_taladro, 6),
            round(volumen_carga, 6), round(volumen_roto_taladro, 3),
            round(toneladas_rotas, 3), round(peso_explosivo_taladro, 3),
            round(fc_volumetrico, 3), round(fc_lineal, 3),
            round(factor_potencia, 3), round(x50_cm, 2)
        ]
    }

    return resultados, {
        "fc_volumetrico": fc_volumetrico,
        "fc_lineal": fc_lineal,
        "factor_potencia": factor_potencia,
        "peso_explosivo_taladro": peso_explosivo_taladro,
        "x50_cm": x50_cm,
        "burden": burden,
        "espaciamiento": espaciamiento,
    }


def _estado_modelo(auditoria, clave):
    datos = auditoria.get(clave, {}) if isinstance(auditoria, dict) else {}
    return datos.get("estado", "no ejecutado")


def _buscar_resultado_tabla(resultados, parametro_objetivo):
    """Busca un resultado por nombre exacto dentro de la tabla final PARAMETRO/UND/VALOR."""
    if not isinstance(resultados, dict):
        return None, None

    params = resultados.get("Parametros", [])
    unidades = resultados.get("Unidad", [])
    valores = resultados.get("Total", [])
    for nombre, unidad, valor in zip(params, unidades, valores):
        if str(nombre).strip().lower() == parametro_objetivo.strip().lower():
            return unidad, valor
    return None, None


def _formatear_valor(valor):
    """Formatea valores sin perder precision visual de la tabla completa."""
    try:
        numero = float(valor)
    except Exception:
        return str(valor)

    if abs(numero) >= 100:
        return f"{numero:.2f}"
    if abs(numero) >= 10:
        return f"{numero:.3f}".rstrip("0").rstrip(".")
    return f"{numero:.3f}".rstrip("0").rstrip(".")


def _unidad_para_voz(unidad):
    """Convierte abreviaturas de unidad en texto natural para no deletrear kg/m3 o kg/Ton."""
    mapa = {
        "Kg": "kilogramos por taladro",
        "kg": "kilogramos por taladro",
        "Kg/Tal": "kilogramos por taladro",
        "kg/tal": "kilogramos por taladro",
        "Kg/m3": "kilogramos por metro cubico",
        "kg/m3": "kilogramos por metro cubico",
        "Kg/m": "kilogramos por metro",
        "kg/m": "kilogramos por metro",
        "Kg/Ton": "kilogramos por tonelada",
        "kg/Ton": "kilogramos por tonelada",
        "cm": "centimetros",
        "m": "metros",
        "mm": "milimetros",
        "Ton": "toneladas",
        "Ton/m3": "toneladas por metro cubico",
        "MPa": "megapascales",
    }
    return mapa.get(str(unidad).strip(), str(unidad).strip())


def generar_codigo_respuesta(resultados, auditoria):
    """
    Genera la respuesta resumida desde la tabla completa, no desde abreviaturas.
    Se usa para pantalla, logica de API y altavoz.
    """
    filas = [
        ("Carga Operante", "Carga Operante (Kg/Tal)"),
        ("FACTOR DE CARGA", "FACTOR DE CARGA"),
        ("FACTOR DE CARGA LINEAL", "FACTOR DE CARGA LINEAL"),
        ("FACTOR DE POTENCIA", "FACTOR DE POTENCIA"),
        ("Fragmentacion X50", "Fragmentacion X50"),
    ]

    lineas = []
    partes_tts = ["Resultados de voladura."]
    for etiqueta, nombre_tabla in filas:
        unidad, valor = _buscar_resultado_tabla(resultados, nombre_tabla)
        if valor is None:
            continue
        valor_txt = _formatear_valor(valor)
        unidad_txt = str(unidad or "").strip()
        lineas.append(f"{etiqueta:<25} | {unidad_txt:<6} | {valor_txt}")
        partes_tts.append(f"{etiqueta.title()}: {valor_txt} {_unidad_para_voz(unidad_txt)}.")

    estado_functiongemma = _estado_modelo(auditoria, "functiongemma")
    estado_qwen = _estado_modelo(auditoria, "qwen3.5:4b")
    lineas.append(f"IA Local: functiongemma={estado_functiongemma} | qwen3.5:4b={estado_qwen}")
    partes_tts.append(
        f"IA local: functiongemma {estado_functiongemma}; qwen tres punto cinco, cuatro b, {estado_qwen}."
    )

    return "\n".join(lineas), " ".join(partes_tts)


def calcular_voladura_worker(parametros):
    """Hilo de calculo: audita con Ollama y ejecuta formulas sin congelar Tkinter."""
    try:
        auditoria = {}
        if TOOL_AI_AVAILABLE:
            escribir_log("[LOG - ROUTER]: Enviando variables al backend Ollama local...")
            auditoria = auditar_con_ollama(parametros, log_callback=escribir_log)
        else:
            auditoria = {
                "functiongemma": {
                    "estado": "omitido",
                    "mensaje": "tool_ai.py no pudo importarse."
                },
                "qwen3.5:4b": {
                    "estado": "omitido",
                    "mensaje": "tool_ai.py no pudo importarse."
                }
            }
            escribir_log("[LOG - ROUTER]: tool_ai.py no disponible. Se continua con calculo local.")

        escribir_log("[LOG - MATH]: Ejecutando nucleo Kuz-Ram deterministico...")
        resultados, indicadores = ejecutar_nucleo_kuzram(parametros)

        res_text, res_tts = generar_codigo_respuesta(resultados, auditoria)

        log_queue.put(("resultado", res_text, resultados, auditoria, res_tts))

    except Exception as exc:
        detalle = f"{exc}\n\n{traceback.format_exc()}"
        log_queue.put(("error", detalle))


def calcular_voladura():
    """Comando del boton CALCULAR DATOS."""
    try:
        parametros = leer_parametros_gui()
    except Exception as exc:
        messagebox.showerror("Error", str(exc))
        return

    global parametros_globales
    parametros_globales = dict(parametros)

    btn_calc.config(state=tk.DISABLED)
    btn_full.config(state=tk.DISABLED)
    btn_excel.config(state=tk.DISABLED)
    lbl_resumen.config(text="Procesando con Ollama local y nucleo Kuz-Ram...", fg=COLOR_BORDE_ROJO)

    escribir_log("[LOG - ROUTER]: Evaluando variables...")
    escribir_log(
        "[LOG - INPUT]: "
        f"ancho={parametros['ancho_seccion']} m, avance={parametros['avance']} m, "
        f"diametro={parametros['diametro_taladro']} mm, "
        f"rho_exp={parametros['densidad_explosivo']} kg/m3, "
        f"rho_roca={parametros['densidad_roca']} Ton/m3, "
        f"R={parametros['resistencia_roca']} MPa"
    )

    hilo = threading.Thread(
        target=calcular_voladura_worker,
        args=(parametros,),
        daemon=True
    )
    hilo.start()


# -------------------------------------------------------------------
# 2. FUNCION PANTALLA COMPLETA
# -------------------------------------------------------------------
def abrir_fullscreen():
    if not resultados_globales:
        return

    top = tk.Toplevel(root)
    top.title("Resultados Detallados")
    top.configure(bg=COLOR_FONDO)
    top.geometry("520x650")

    txt = tk.Text(
        top,
        font=("Courier New", 12),
        bg=COLOR_FONDO,
        fg=COLOR_TEXTO
    )
    txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    header = f"{'PARAMETRO':<25} | {'UND':<6} | {'VALOR':<8}\n"
    divider = "-" * 45 + "\n"
    txt.insert(tk.END, header + divider)

    params = resultados_globales["Parametros"]
    units = resultados_globales["Unidad"]
    vals = resultados_globales["Total"]

    for p, u, v in zip(params, units, vals):
        line = f"{p[:25]:<25} | {u:<6} | {v}\n"
        txt.insert(tk.END, line)

    if auditoria_global:
        txt.insert(tk.END, "\n" + "-" * 45 + "\n")
        txt.insert(tk.END, "AUDITORIA IA LOCAL\n")
        txt.insert(tk.END, "-" * 45 + "\n")
        for modelo, datos in auditoria_global.items():
            estado = datos.get("estado", "sin estado") if isinstance(datos, dict) else "sin estado"
            mensaje = datos.get("mensaje", "") if isinstance(datos, dict) else str(datos)
            txt.insert(tk.END, f"{modelo}: {estado}\n")
            if mensaje:
                txt.insert(tk.END, f"{mensaje[:900]}\n")

            # Si existe payload estructurado, se muestra para comunicarlo con API/backend.
            detalle = datos.get("detalle", None) if isinstance(datos, dict) else None
            if modelo == "payload_api" and detalle:
                try:
                    txt.insert(tk.END, "Payload JSON API:\n")
                    txt.insert(tk.END, json.dumps(detalle, ensure_ascii=False, indent=2)[:2500] + "\n")
                except Exception:
                    txt.insert(tk.END, str(detalle)[:2500] + "\n")

            txt.insert(tk.END, "\n")

    txt.config(state=tk.DISABLED)


# -------------------------------------------------------------------
# 3. FUNCIONES DE EXCEL, VOZ, TTS Y PREENTRENAMIENTO
# -------------------------------------------------------------------
def _df_parametros_extraidos(parametros_extraidos):
    """Convierte los parametros extraidos en una fila presentable para Excel."""
    if not parametros_extraidos:
        return pd.DataFrame()

    fila = dict(parametros_extraidos)
    if fila.get("densidad_explosivo", 0) and fila["densidad_explosivo"] > 5:
        fila["densidad_explosivo"] = fila["densidad_explosivo"] / 1000.0

    df = pd.DataFrame([fila])
    df.rename(columns={
        "ancho_seccion": "Ancho Seccion (m)",
        "avance": "Avance (m)",
        "diametro_taladro": "Diametro Taladro (mm)",
        "densidad_explosivo": "Dens. Explosivo (g/cm3)",
        "densidad_roca": "Dens. Roca (t/m3)",
        "resistencia_roca": "Resistencia Roca (MPa)",
    }, inplace=True)
    return df


def guardar_tabla_excel(parametros_extraidos):
    """Exporta solo la tabla de parametros extraidos, usando selector de archivo."""
    if not PANDAS_AVAILABLE:
        messagebox.showerror("Error", "La libreria 'pandas' no esta instalada.")
        return
    if not parametros_extraidos:
        messagebox.showwarning("Advertencia", "No hay datos extraidos para exportar.")
        return

    ruta_guardado = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Archivos de Excel", "*.xlsx")],
        title="Guardar Parametros de Voladura",
        initialfile=f"Parametros_Voladura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    )
    if not ruta_guardado:
        return

    try:
        df = _df_parametros_extraidos(parametros_extraidos)
        df.to_excel(ruta_guardado, index=False, engine="openpyxl")
        messagebox.showinfo("Exito", f"Tabla guardada en:\n{ruta_guardado}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")


def exportar_excel():
    """Exporta parametros extraidos, resultados calculados y auditoria IA a un .xlsx."""
    if not PANDAS_AVAILABLE:
        messagebox.showerror("Error", "La libreria 'pandas' no esta instalada.")
        return

    if not resultados_globales and not parametros_globales:
        messagebox.showwarning("Advertencia", "No hay datos para exportar.")
        return

    ruta_guardado = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Archivos de Excel", "*.xlsx")],
        title="Guardar Calculo de Voladura",
        initialdir=RUTA_EXPORTACION if os.path.isdir(RUTA_EXPORTACION) else os.getcwd(),
        initialfile=f"Voladura_Aguilas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    )
    if not ruta_guardado:
        return

    try:
        with pd.ExcelWriter(ruta_guardado, engine="openpyxl") as writer:
            if parametros_globales:
                _df_parametros_extraidos(parametros_globales).to_excel(
                    writer, sheet_name="Parametros_Extraidos", index=False
                )

            if resultados_globales:
                pd.DataFrame(resultados_globales).to_excel(
                    writer, sheet_name="Resultados_KuzRam", index=False
                )

            if auditoria_global:
                filas = []
                for modelo, datos in auditoria_global.items():
                    if isinstance(datos, dict):
                        filas.append({
                            "Modelo": modelo,
                            "Estado": datos.get("estado", ""),
                            "Mensaje": datos.get("mensaje", ""),
                            "Detalle": str(datos.get("detalle", ""))[:32000],
                        })
                if filas:
                    pd.DataFrame(filas).to_excel(writer, sheet_name="Auditoria_IA", index=False)

            ruta_training = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_data.jsonl")
            if os.path.exists(ruta_training):
                resumen = analizar_training_data(ruta_training)
                pd.DataFrame([resumen]).to_excel(writer, sheet_name="Dataset_FT", index=False)

        messagebox.showinfo("Exito", f"Archivo guardado en:\n{ruta_guardado}")
    except Exception as e:
        messagebox.showerror("Error Guardando", f"No se pudo guardar:\n{e}")


def analizar_training_data(ruta_training):
    """Resumen rapido del dataset JSONL para mostrarlo en Excel o consola."""
    requeridos = [
        "ancho_seccion", "avance", "diametro_taladro", "densidad_explosivo",
        "densidad_roca", "resistencia_roca",
    ]
    total = completos = incompletos = invalidos = 0
    cobertura = {k: 0 for k in requeridos}

    try:
        with open(ruta_training, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                total += 1
                try:
                    data = json.loads(linea)
                    mensajes = data.get("messages", [])
                    asistente = mensajes[-1] if mensajes else {}
                    calls = asistente.get("tool_calls", []) or []
                    args = calls[0].get("arguments", {}) if calls else {}
                    if all(k in args and args[k] not in (None, "") for k in requeridos):
                        completos += 1
                    else:
                        incompletos += 1
                    for k in requeridos:
                        if k in args and args[k] not in (None, ""):
                            cobertura[k] += 1
                except Exception:
                    invalidos += 1
    except FileNotFoundError:
        pass

    cobertura_txt = "; ".join([f"{k}={v}" for k, v in cobertura.items()])
    return {
        "archivo": os.path.basename(ruta_training),
        "total_lineas": total,
        "ejemplos_completos": completos,
        "ejemplos_incompletos": incompletos,
        "lineas_invalidas": invalidos,
        "cobertura_variables": cobertura_txt,
    }


def aplicar_parametros_extraidos(parametros):
    """Rellena el formulario con argumentos devueltos por functiongemma."""
    mapping = [
        ("ancho_seccion", entry_ancho),
        ("avance", entry_avance),
        ("diametro_taladro", entry_diametro),
        ("densidad_explosivo", entry_densidad_exp),
        ("densidad_roca", entry_densidad_roca),
        ("resistencia_roca", entry_resistencia),
    ]
    for clave, entry in mapping:
        if clave in parametros and parametros[clave] is not None:
            entry.delete(0, tk.END)
            entry.insert(0, str(parametros[clave]))


def capturar_audio_usuario():
    """Captura voz, transcribe y envia el texto a functiongemma sin bloquear Tkinter."""
    btn_mic.config(state=tk.DISABLED)
    lbl_resumen.config(text="Escuchando microfono...", fg=COLOR_BORDE_ROJO)
    escribir_log("[LOG - MIC]: Activando reconocimiento de voz.")

    hilo = threading.Thread(target=capturar_audio_worker, daemon=True)
    hilo.start()


def capturar_audio_worker():
    try:
        try:
            import speech_recognition as sr  # type: ignore
        except Exception as exc:
            mensaje = (
                "No se pudo importar SpeechRecognition. Ejecuta: "
                "python -m pip install SpeechRecognition. "
                f"Detalle: {exc}"
            )
            log_queue.put(("voz", "", mensaje))
            return

        # SpeechRecognition necesita PyAudio para abrir el microfono.
        try:
            import pyaudio  # noqa: F401  # type: ignore
        except Exception as exc:
            if platform.system().lower() == "windows":
                mensaje = (
                    "Error capturando audio: falta PyAudio en el .venv. "
                    "Ejecuta: .\\instalar_modulos_windows.ps1 o "
                    "python -m pip install -r requirements-voice-windows.txt. "
                    "Si falla, usa Python 3.11/3.12 o instala Microsoft C++ Build Tools. "
                    f"Detalle: {exc}"
                )
            else:
                mensaje = (
                    "Error capturando audio: falta PyAudio/PortAudio. "
                    "En Linux/Raspberry Pi ejecuta: sudo apt install portaudio19-dev python3-pyaudio "
                    "y crea el entorno con python3 -m venv .venv --system-site-packages. "
                    f"Detalle: {exc}"
                )
            log_queue.put(("voz", "", mensaje))
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.7)
                escribir_log("[LOG - MIC]: Microfono detectado. Habla ahora...")
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=14)
        except Exception as exc:
            mensaje = (
                "Error abriendo el microfono. Verifica que Windows tenga un microfono activo, "
                "que la app tenga permisos de microfono y que PyAudio este instalado. "
                f"Detalle: {exc}"
            )
            log_queue.put(("voz", "", mensaje))
            return

        try:
            transcripcion = recognizer.recognize_google(audio, language="es-PE")
        except Exception:
            transcripcion = recognizer.recognize_google(audio, language="es-ES")

        if not TOOL_AI_AVAILABLE:
            log_queue.put(("voz", transcripcion, "tool_ai.py no esta disponible para procesar la transcripcion."))
            return

        respuesta = procesar_input_minero(
            transcripcion,
            activar_tts=True,
            log_callback=escribir_log,
        )
        log_queue.put(("voz", transcripcion, respuesta))

    except Exception as exc:
        log_queue.put(("voz", "", f"Error capturando audio: {exc}"))


def reproducir_ultima_respuesta():
    """Repite por tts_piper.py la ultima respuesta visible."""
    global ultima_respuesta_tts
    texto = ultima_respuesta_tts or lbl_resumen.cget("text")
    if resultados_globales:
        try:
            _, texto = generar_codigo_respuesta(resultados_globales, auditoria_global)
        except Exception:
            pass
    if not texto or texto.strip() == "Esperando calculo...":
        messagebox.showwarning("Advertencia", "No hay una respuesta para repetir.")
        return

    if TOOL_AI_AVAILABLE:
        ok = enviar_a_tts_piper(texto, log_callback=escribir_log)
        if ok:
            escribir_log("[LOG - TTS]: Reproduciendo ultima respuesta.")
            return

    messagebox.showwarning(
        "TTS no disponible",
        "No se pudo reproducir voz. Verifica que tts_piper.py este en la carpeta y ejecuta: python -m pip install pyttsx3. En Windows se intentara System.Speech como respaldo."
    )


# -------------------------------------------------------------------
# 4. INTERFAZ GRAFICA (GUI) + BANNER MINEXCELLENCE
# -------------------------------------------------------------------
root = tk.Tk()
root.title("MINEXcellence 2025 - Diseno Las Aguilas")
root.configure(bg=COLOR_FONDO)

# --------- BANNER SUPERIOR CON IMAGEN ----------
banner_frame = tk.Frame(root, bg=COLOR_FONDO)
banner_frame.pack(side="top", fill="x")

banner_label = None
imagen_original = None
orig_w = orig_h = None

ruta_imagen_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Imagen1.png")
ruta_banner = ruta_imagen_local if os.path.exists(ruta_imagen_local) else RUTA_IMAGEN

if PIL_AVAILABLE and os.path.exists(ruta_banner):
    imagen_original = Image.open(ruta_banner)
    orig_w, orig_h = imagen_original.size

    root.geometry(f"{orig_w}x760")

    imagen_tk = ImageTk.PhotoImage(imagen_original)
    banner_label = tk.Label(banner_frame, image=imagen_tk, bd=0)
    banner_label.image = imagen_tk
    banner_label.pack(fill="x", side="top")

    def redimensionar_banner(event):
        if event.width <= 0 or imagen_original is None:
            return
        nuevo_ancho = event.width
        escala = nuevo_ancho / orig_w
        nuevo_alto = int(orig_h * escala)
        img_redim = imagen_original.resize(
            (nuevo_ancho, nuevo_alto),
            Image.LANCZOS
        )
        img_tk2 = ImageTk.PhotoImage(img_redim)
        banner_label.config(image=img_tk2)
        banner_label.image = img_tk2

    root.bind("<Configure>", redimensionar_banner)
else:
    banner_label = tk.Label(
        banner_frame,
        text="MINEXcellence 2025",
        bg=COLOR_BORDE_AZUL,
        fg="white",
        font=("Arial", 18, "bold"),
        anchor="w",
        padx=20,
        pady=10
    )
    banner_label.pack(fill="x", side="top")

# --------- AREA PRINCIPAL SCROLLEABLE (FORMATO) ----------
main_frame = tk.Frame(root, bg=COLOR_FONDO)
main_frame.pack(fill=tk.BOTH, expand=True)

canvas = tk.Canvas(main_frame, bg=COLOR_FONDO, highlightthickness=0)
scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

canvas.configure(yscrollcommand=scrollbar.set)
content_frame = tk.Frame(canvas, bg=COLOR_FONDO, padx=15, pady=15)
canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")


def on_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.itemconfig(canvas_window, width=event.width)


canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
content_frame.bind("<Configure>", on_configure)

# --- ESTILOS VISUALES ---
font_lbl = ("Arial", 10, "bold")
font_ent = ("Arial", 12)


def crear_input(parent, label_text, default):
    frame = tk.Frame(
        parent,
        bg=COLOR_FONDO,
        highlightbackground=COLOR_BORDE_AZUL,
        highlightthickness=1
    )
    frame.pack(fill=tk.X, pady=5)

    lbl = tk.Label(
        frame,
        text=label_text,
        bg=COLOR_FONDO,
        fg=COLOR_BORDE_AZUL,
        font=font_lbl,
        anchor="w"
    )
    lbl.pack(fill=tk.X, padx=5, pady=(5, 0))

    ent = tk.Entry(
        frame,
        bg="white",
        fg="black",
        font=font_ent,
        relief=tk.FLAT
    )
    ent.pack(fill=tk.X, padx=5, pady=5, ipady=4)
    ent.insert(0, default)
    return ent


# --- CABECERA DEL FORMATO ---
tk.Label(
    content_frame,
    text="DISENO DE VOLADURA",
    bg=COLOR_FONDO,
    fg=COLOR_BORDE_ROJO,
    font=("Arial", 16, "bold")
).pack(pady=(0, 20))

# --- ENTRADAS DE DATOS ---
frame_datos = tk.LabelFrame(
    content_frame,
    text=" PARAMETROS ",
    bg=COLOR_FONDO,
    fg=COLOR_BORDE_ROJO,
    font=font_lbl,
    bd=2,
    relief=tk.GROOVE
)
frame_datos.pack(fill=tk.X)

entry_ancho = crear_input(frame_datos, "Ancho Seccion / Tajo (m):", "4.0")
entry_avance = crear_input(frame_datos, "Avance / Altura (m):", "1.5")
entry_diametro = crear_input(frame_datos, "Diametro Taladro (mm):", "45")
entry_densidad_exp = crear_input(frame_datos, "Densidad Explosivo (kg/m3 o g/cm3):", "1100")
entry_densidad_roca = crear_input(frame_datos, "Densidad Roca (Ton/m3):", "2.7")
entry_resistencia = crear_input(frame_datos, "Resistencia Roca (MPa):", "120")

# --- BOTONES DE ACCION ---
btn_calc = tk.Button(
    content_frame,
    text="CALCULAR DATOS",
    bg=COLOR_BTN_AZUL,
    fg="white",
    font=("Arial", 12, "bold"),
    command=calcular_voladura
)
btn_calc.pack(fill=tk.X, pady=(20, 10), ipady=5)

# --- RESULTADOS RESUMIDOS ---
lbl_resumen = tk.Label(
    content_frame,
    text="Esperando calculo...",
    bg="#F0F8FF",
    fg="#555",
    font=("Courier New", 12, "bold"),
    relief=tk.RIDGE,
    padx=10,
    pady=10
)
lbl_resumen.pack(fill=tk.X, pady=10)

# --- BOTONES EXTRA (FULLSCREEN & EXCEL) ---
frame_btns = tk.Frame(content_frame, bg=COLOR_FONDO)
frame_btns.pack(fill=tk.X, pady=10)

btn_full = tk.Button(
    frame_btns,
    text="VER FULL SCREEN",
    bg=COLOR_BORDE_AZUL,
    fg="white",
    state=tk.DISABLED,
    command=abrir_fullscreen
)
btn_full.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4), ipady=5)

btn_excel = tk.Button(
    frame_btns,
    text="DESCARGAR .XLSX",
    bg=COLOR_BTN_VERDE,
    fg="white",
    state=tk.DISABLED,
    command=exportar_excel
)
btn_excel.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, ipady=5)

btn_mic = tk.Button(
    frame_btns,
    text="🎙️ HABLAR (MIC)",
    bg="#4CAF50",
    fg="white",
    font=("Arial", 9, "bold"),
    command=capturar_audio_usuario
)
btn_mic.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, ipady=5)

btn_repetir = tk.Button(
    frame_btns,
    text="🗣️ REPETIR VOZ",
    bg="#FF9800",
    fg="white",
    font=("Arial", 9, "bold"),
    state=tk.DISABLED,
    command=reproducir_ultima_respuesta
)
btn_repetir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0), ipady=5)

# --- TERMINAL VISUAL DE OLLAMA EN TIEMPO REAL ---
frame_terminal = tk.LabelFrame(
    content_frame,
    text=" CONSOLA LOCAL OLLAMA / ROUTER ",
    bg=COLOR_FONDO,
    fg=COLOR_BORDE_ROJO,
    font=font_lbl,
    bd=2,
    relief=tk.GROOVE
)
frame_terminal.pack(fill=tk.BOTH, expand=False, pady=(12, 5))

terminal_scroll = tk.Scrollbar(frame_terminal)
terminal_scroll.pack(side=tk.RIGHT, fill=tk.Y)

txt_terminal = tk.Text(
    frame_terminal,
    bg="#000000",
    fg="#00FF66",
    insertbackground="#00FF66",
    font=("Consolas", 9),
    height=9,
    wrap=tk.WORD,
    yscrollcommand=terminal_scroll.set,
    relief=tk.FLAT
)
txt_terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
terminal_scroll.config(command=txt_terminal.yview)
txt_terminal.config(state=tk.DISABLED)

tk.Label(content_frame, text=" ", bg=COLOR_FONDO).pack(pady=12)

escribir_log("[LOG - SYSTEM]: MINEXcellence 2025 listo. Manual, voz, Excel y dataset FT habilitados.")
root.after(120, procesar_cola_logs)
root.mainloop()
