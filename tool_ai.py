# -*- coding: utf-8 -*-
"""
tool_ai.py
Modulo de ejecucion e intercepcion para pocket-ai / Ultimate Agent.

Correccion v4:
- Acepta texto libre, transcripcion de voz, JSON, logs y la tabla PARAMETRO | UND | VALOR.
- Carga tools.json con esquema estandar de Ollama.
- Llama a functiongemma cuando corresponde.
- Si functiongemma no devuelve tool_call pero los parametros ya estan en el formulario,
  valida localmente y genera un payload API estructurado para evitar advertencias falsas.
- Detecta parametros faltantes y genera instrucciones con la palabra clave "selecciona".
"""

import json
import os
import re
import sys
import traceback
import unicodedata
from datetime import datetime

try:
    import ollama  # type: ignore
except Exception:
    ollama = None  # type: ignore

MODELO_FUNCION = "functiongemma"
NOMBRE_FUNCION = "calcular_voladura"

PARAMETROS_REQUERIDOS = [
    "ancho_seccion",
    "avance",
    "diametro_taladro",
    "densidad_explosivo",
    "densidad_roca",
    "resistencia_roca",
]

ALIASES_PARAMETROS = {
    "ancho_seccion": [
        "ancho seccion", "ancho seccion ref", "ancho sección", "ancho sección ref",
        "seccion", "sección", "ancho", "ancho tajo", "ancho labor", "ancho de seccion",
    ],
    "avance": [
        "longitud avance", "avance", "altura", "longitud de avance", "avance altura",
    ],
    "diametro_taladro": [
        "diametro taladro", "diámetro taladro", "diametro", "diámetro",
        "broca", "diametro broca", "diámetro broca",
    ],
    "densidad_explosivo": [
        "densidad explosivo", "dens exp", "rho exp", "rho_exp", "densidad del explosivo",
        "dens explosivo", "densidad anfo",
    ],
    "densidad_roca": [
        "densidad roca", "dens roca", "rho roca", "rho_roca", "densidad de roca",
        "densidad macizo", "densidad mineral",
    ],
    "resistencia_roca": [
        "resistencia roca", "resistencia a la roca", "ucs",
        "resistencia a la compresion", "resistencia a la compresión",
    ],
}

CLAVES_LOG = {
    "ancho": "ancho_seccion",
    "ancho_seccion": "ancho_seccion",
    "avance": "avance",
    "diametro": "diametro_taladro",
    "diametro_taladro": "diametro_taladro",
    "rho_exp": "densidad_explosivo",
    "densidad_exp": "densidad_explosivo",
    "densidad_explosivo": "densidad_explosivo",
    "rho_roca": "densidad_roca",
    "densidad_roca": "densidad_roca",
    "r": "resistencia_roca",
    "resistencia": "resistencia_roca",
    "resistencia_roca": "resistencia_roca",
}


# -------------------------------------------------------------------
# 1. Carga de herramientas
# -------------------------------------------------------------------
def _base_dir():
    return os.path.dirname(os.path.abspath(__file__))


def cargar_esquema_herramientas(ruta_archivo="tools.json"):
    """Carga tools.json desde la carpeta del modulo, aunque se ejecute desde otra ruta."""
    ruta = ruta_archivo
    if not os.path.isabs(ruta):
        ruta = os.path.join(_base_dir(), ruta_archivo)

    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_parametros_requeridos(herramientas=None):
    if herramientas:
        try:
            return herramientas[0]["function"]["parameters"]["required"]
        except Exception:
            pass
    return list(PARAMETROS_REQUERIDOS)


# -------------------------------------------------------------------
# 2. Normalizacion, parsing y payload API
# -------------------------------------------------------------------
def _sin_tildes(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return texto.lower().strip()


def _limpiar_clave(texto):
    texto = _sin_tildes(texto)
    texto = re.sub(r"\([^)]*\)", " ", texto)
    texto = re.sub(r"[^a-z0-9_ ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _mapear_nombre_parametro(nombre):
    limpio = _limpiar_clave(nombre)
    for canonico, aliases in ALIASES_PARAMETROS.items():
        for alias in aliases:
            a = _limpiar_clave(alias)
            if not a:
                continue
            if limpio == a:
                return canonico
            # Evita falsos positivos por alias muy cortos como "r".
            if len(a) >= 4 and (a in limpio or limpio in a):
                return canonico
    return None


def _numero_desde_texto(texto):
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)
    s = str(texto).strip().replace(",", ".")
    # Captura numeros como -1, 4, 4.0, .8
    m = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def normalizar_parametros(parametros):
    """Convierte aliases y valores numericos a un dict canonico de 6 parametros."""
    salida = {}
    if not isinstance(parametros, dict):
        return salida

    for clave, valor in parametros.items():
        canonica = clave if clave in PARAMETROS_REQUERIDOS else _mapear_nombre_parametro(clave)
        if not canonica:
            continue
        numero = _numero_desde_texto(valor)
        if numero is not None:
            salida[canonica] = numero
    return salida


def parsear_parametros_desde_tabla(texto):
    """
    Lee tablas tipo:
    PARAMETRO | UND | VALOR
    Ancho Seccion (Ref) | m | 4.0

    Tambien soporta logs tipo:
    ancho=4.0 m, avance=1.5 m, diametro=45.0 mm, rho_exp=1100.0 kg/m3...
    """
    if not isinstance(texto, str) or not texto.strip():
        return {}

    encontrados = {}

    # 1) Si llega JSON directo o un string EJECUTAR_CALCULO
    s = texto.strip()
    if s.startswith("EJECUTAR_CALCULO:"):
        s = s.split(":", 1)[1].strip()
    if s.startswith("{"):
        try:
            return normalizar_parametros(json.loads(s))
        except Exception:
            pass

    # 2) Tabla PARAMETRO | UND | VALOR
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or "|" not in linea:
            continue
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) < 3:
            continue
        nombre = partes[0]
        valor = partes[-1]
        canonica = _mapear_nombre_parametro(nombre)
        if canonica:
            numero = _numero_desde_texto(valor)
            if numero is not None:
                encontrados[canonica] = numero

    # 3) Logs de entrada con clave=valor
    patron = re.compile(r"([A-Za-z_ÁÉÍÓÚáéíóúñÑ]+)\s*=\s*([-+]?\d+(?:[\.,]\d+)?)")
    for clave, valor in patron.findall(texto):
        clave_norm = _limpiar_clave(clave).replace(" ", "_")
        canonica = CLAVES_LOG.get(clave_norm)
        if canonica:
            numero = _numero_desde_texto(valor)
            if numero is not None:
                encontrados[canonica] = numero

    return encontrados


def construir_payload_api(parametros, incluir_metadatos=True):
    """Genera un payload JSON estable para comunicar con Ollama/API o un backend externo."""
    args = normalizar_parametros(parametros)
    payload = {
        "tool": NOMBRE_FUNCION,
        "arguments": {k: args.get(k) for k in PARAMETROS_REQUERIDOS},
        "missing": calcular_faltantes(args, PARAMETROS_REQUERIDOS),
    }
    if incluir_metadatos:
        dens_exp = args.get("densidad_explosivo")
        payload["metadata"] = {
            "origen": "MINEXcellence_Tkinter",
            "modelo_esperado": MODELO_FUNCION,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "densidad_explosivo_unidad_detectada": "kg/m3" if dens_exp and dens_exp > 5 else "g/cm3",
            "tools_schema": "tools.json",
        }
    return payload


# -------------------------------------------------------------------
# 3. Utilidades de Ollama / tool_calls
# -------------------------------------------------------------------
def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _obtener_mensaje(respuesta):
    return _get(respuesta, "message", {}) or {}


def _obtener_tool_calls(respuesta):
    mensaje = _obtener_mensaje(respuesta)
    return _get(mensaje, "tool_calls", []) or []


def _normalizar_argumentos(argumentos):
    """Ollama puede devolver arguments como dict o como string JSON."""
    if argumentos is None:
        return {}
    if isinstance(argumentos, dict):
        return normalizar_parametros(argumentos)
    if isinstance(argumentos, str):
        texto = argumentos.strip()
        if not texto:
            return {}
        try:
            data = json.loads(texto)
            return normalizar_parametros(data) if isinstance(data, dict) else {}
        except Exception:
            return parsear_parametros_desde_tabla(texto)
    return {}


def _argumentos_de_tool_call(tool_call):
    funcion = _get(tool_call, "function", {}) or {}
    nombre = _get(funcion, "name", "")
    argumentos = _normalizar_argumentos(_get(funcion, "arguments", {}))
    return nombre, argumentos


def calcular_faltantes(args_recibidos, parametros_requeridos=None):
    """Calcula los campos ausentes, nulos, vacios o <= 0."""
    parametros_requeridos = parametros_requeridos or PARAMETROS_REQUERIDOS
    args_recibidos = normalizar_parametros(args_recibidos)
    faltantes = []
    for param in parametros_requeridos:
        if param not in args_recibidos:
            faltantes.append(param)
            continue
        valor = args_recibidos.get(param)
        try:
            if valor is None or float(valor) <= 0:
                faltantes.append(param)
        except Exception:
            faltantes.append(param)
    return faltantes


def armar_string_tts_faltantes(faltantes):
    """Genera la instruccion imperativa requerida: selecciona ... por cada dato."""
    instrucciones = ", ".join([f"selecciona {p.replace('_', ' ')}" for p in faltantes])
    return f"Faltan datos para el cálculo. Por favor, {instrucciones}."


def enviar_a_tts_piper(texto, log_callback=None):
    """
    Envia el texto a tts_piper.py si existe en el proyecto.
    Soporta nombres de funcion comunes sin romper el flujo si no esta disponible.
    """
    try:
        import tts_piper  # type: ignore

        funcion = None
        for nombre in ("speak", "decir", "reproducir_texto", "text_to_speech"):
            if hasattr(tts_piper, nombre):
                funcion = getattr(tts_piper, nombre)
                break

        if funcion is None:
            if log_callback:
                log_callback("[LOG - TTS]: tts_piper.py encontrado, pero no tiene funcion compatible.")
            return False

        resultado = funcion(texto)
        if resultado is False:
            if log_callback:
                log_callback("[LOG - TTS]: tts_piper.py se ejecuto, pero no encontro motor de voz disponible.")
            return False

        if log_callback:
            log_callback("[LOG - TTS]: String enviado a tts_piper.py.")
        return True

    except Exception as exc:
        if log_callback:
            log_callback(f"[LOG - TTS]: tts_piper.py no disponible o fallo: {exc}")
        return False


# -------------------------------------------------------------------
# 4. Funcion principal para texto, voz, tabla o JSON
# -------------------------------------------------------------------
def procesar_input_minero(texto_usuario, activar_tts=True, log_callback=None):
    """
    Procesa texto/transcripcion/tabla/log con functiongemma y fallback local.

    Retorna:
    - "Faltan datos... selecciona ..." si faltan parametros.
    - "EJECUTAR_CALCULO: {...}" si los 6 datos requeridos estan completos.
    - Mensaje de error o solicitud si no hay datos suficientes.
    """
    try:
        herramientas = cargar_esquema_herramientas()
    except Exception as exc:
        return f"Error cargando tools.json: {exc}"

    parametros_requeridos = obtener_parametros_requeridos(herramientas)

    # Fallback/lectura directa para tablas y logs ya generados por la propia app.
    args_directos = parsear_parametros_desde_tabla(texto_usuario)
    if args_directos:
        faltantes_directos = calcular_faltantes(args_directos, parametros_requeridos)
        if not faltantes_directos:
            return f"EJECUTAR_CALCULO: {json.dumps(args_directos, ensure_ascii=False)}"

    if ollama is None:
        if args_directos:
            string_tts = armar_string_tts_faltantes(calcular_faltantes(args_directos, parametros_requeridos))
            if activar_tts:
                enviar_a_tts_piper(string_tts, log_callback=log_callback)
            return string_tts
        return (
            "Error de ejecución con Ollama: No se pudo importar la librería 'ollama'. "
            "Ejecuta: python -m pip install ollama"
        )

    try:
        respuesta = ollama.chat(
            model=MODELO_FUNCION,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extrae parámetros mineros desde texto libre, tablas o transcripciones. "
                        "Cuando el usuario entregue datos para voladura, usa la herramienta calcular_voladura. "
                        "No inventes valores faltantes. Si el texto contiene una tabla PARAMETRO UND VALOR, "
                        "usa esos valores para los argumentos."
                    ),
                },
                {"role": "user", "content": str(texto_usuario)},
            ],
            tools=herramientas,
        )

        tool_calls = _obtener_tool_calls(respuesta)
        if tool_calls:
            for tool in tool_calls:
                nombre_funcion, args_recibidos = _argumentos_de_tool_call(tool)
                if nombre_funcion == NOMBRE_FUNCION:
                    faltantes = calcular_faltantes(args_recibidos, parametros_requeridos)
                    if faltantes:
                        string_tts = armar_string_tts_faltantes(faltantes)
                        if activar_tts:
                            enviar_a_tts_piper(string_tts, log_callback=log_callback)
                        return string_tts
                    return f"EJECUTAR_CALCULO: {json.dumps(args_recibidos, ensure_ascii=False)}"

        # Si Ollama no uso herramientas, pero la tabla/log tenia datos parciales, reportamos faltantes reales.
        if args_directos:
            faltantes = calcular_faltantes(args_directos, parametros_requeridos)
            string_tts = armar_string_tts_faltantes(faltantes)
            if activar_tts:
                enviar_a_tts_piper(string_tts, log_callback=log_callback)
            return string_tts

        return "Por favor, especifica los parámetros para calcular la voladura."

    except Exception as e:
        # Si la API local de Ollama falla, igual aprovechamos tabla/log si ya habia datos.
        if args_directos:
            faltantes = calcular_faltantes(args_directos, parametros_requeridos)
            if not faltantes:
                return f"EJECUTAR_CALCULO: {json.dumps(args_directos, ensure_ascii=False)}"
        return f"Error de ejecución con Ollama: {str(e)}"


# -------------------------------------------------------------------
# 5. Compatibilidad con app.py final
# -------------------------------------------------------------------
def validar_parametros_locales(parametros):
    observaciones = []
    args = normalizar_parametros(parametros)
    for clave in PARAMETROS_REQUERIDOS:
        try:
            valor = float(args.get(clave, 0))
        except Exception:
            valor = 0.0
        if valor <= 0:
            observaciones.append(f"{clave}: debe ser mayor que cero.")
    return observaciones


def _texto_desde_parametros(parametros):
    args = normalizar_parametros(parametros)
    dens_exp = args.get("densidad_explosivo")
    if dens_exp is not None and dens_exp > 5:
        dens_exp_txt = f"{dens_exp} kg/m3 equivalente a {dens_exp / 1000.0:.3f} g/cm3"
    else:
        dens_exp_txt = f"{dens_exp} g/cm3"

    return (
        "Calcular voladura con los siguientes datos ya ingresados en el formulario: "
        f"ancho sección {args.get('ancho_seccion')} metros, "
        f"avance {args.get('avance')} metros, "
        f"diámetro taladro {args.get('diametro_taladro')} milímetros, "
        f"densidad explosivo {dens_exp_txt}, "
        f"densidad roca {args.get('densidad_roca')} toneladas por metro cúbico, "
        f"resistencia roca {args.get('resistencia_roca')} MPa. "
        "Devuelve tool_call calcular_voladura sin inventar datos."
    )


def _parsear_ejecutar_calculo(resultado):
    prefijo = "EJECUTAR_CALCULO:"
    if not isinstance(resultado, str) or not resultado.startswith(prefijo):
        return None
    try:
        return normalizar_parametros(json.loads(resultado[len(prefijo):].strip()))
    except Exception:
        return None


def auditar_con_ollama(parametros, log_callback=None):
    """
    Wrapper compatible con app.py.
    Corrige el caso mostrado en la captura: si la tabla/formulario ya contiene los 6 datos,
    la auditoria queda OK aunque functiongemma no emita tool_call.
    """
    args_locales = normalizar_parametros(parametros)
    observaciones_locales = validar_parametros_locales(args_locales)
    payload_api = construir_payload_api(args_locales)

    if log_callback:
        log_callback("[LOG - FUNCTIONGEMMA]: Enviando payload estructurado con esquema tools.json a Ollama/API local...")
        log_callback("[LOG - API]: " + json.dumps(payload_api["arguments"], ensure_ascii=False))

    if ollama is None:
        mensaje = (
            "No se pudo importar la librería 'ollama'. Ejecuta: "
            "python -m pip install -r requirements.txt o python -m pip install ollama."
        )
        return {
            "functiongemma": {"estado": "error", "mensaje": mensaje, "detalle": payload_api},
            "validacion_local": {
                "estado": "ok" if not observaciones_locales else "advertencia",
                "mensaje": "; ".join(observaciones_locales),
            },
            "payload_api": {
                "estado": "ok" if not payload_api["missing"] else "advertencia",
                "mensaje": "Payload generado para comunicacion con API local.",
                "detalle": payload_api,
            },
        }

    try:
        texto_usuario = _texto_desde_parametros(args_locales)
        resultado = procesar_input_minero(texto_usuario, activar_tts=False, log_callback=log_callback)

        detalle_modelo = _parsear_ejecutar_calculo(resultado)
        if detalle_modelo is not None:
            estado = "ok"
            mensaje = "Parámetros completos leídos por functiongemma mediante calcular_voladura."
            detalle = construir_payload_api(detalle_modelo)
        elif not observaciones_locales:
            # Correccion clave: el formulario/tabla ya trae todos los datos.
            estado = "ok"
            mensaje = (
                "Parámetros completos validados desde el formulario/respuesta. "
                "Payload API generado correctamente; no se requiere pedir datos nuevamente."
            )
            detalle = payload_api
        elif isinstance(resultado, str) and resultado.startswith("Faltan datos"):
            estado = "advertencia"
            mensaje = resultado
            detalle = payload_api
        else:
            estado = "advertencia"
            mensaje = resultado
            detalle = payload_api

        if log_callback:
            log_callback(f"[LOG - FUNCTIONGEMMA]: {mensaje}")

        return {
            "functiongemma": {
                "estado": estado,
                "mensaje": mensaje,
                "detalle": detalle,
                "respuesta_modelo": resultado,
            },
            "validacion_local": {
                "estado": "ok" if not observaciones_locales else "advertencia",
                "mensaje": "; ".join(observaciones_locales),
            },
            "payload_api": {
                "estado": "ok" if not payload_api["missing"] else "advertencia",
                "mensaje": "Payload generado para comunicacion con API local.",
                "detalle": payload_api,
            },
        }

    except Exception as exc:
        if log_callback:
            log_callback(f"[LOG - FUNCTIONGEMMA]: Error controlado: {exc}")
        return {
            "functiongemma": {
                "estado": "error",
                "mensaje": f"No se pudo consultar functiongemma: {exc}",
                "detalle": traceback.format_exc(),
            },
            "validacion_local": {
                "estado": "ok" if not observaciones_locales else "advertencia",
                "mensaje": "; ".join(observaciones_locales),
            },
            "payload_api": {
                "estado": "ok" if not payload_api["missing"] else "advertencia",
                "mensaje": "Payload generado localmente aunque fallo functiongemma.",
                "detalle": payload_api,
            },
        }


# -------------------------------------------------------------------
# 6. Prueba rapida desde terminal
# -------------------------------------------------------------------
if __name__ == "__main__":
    test_input = "Quiero hacer una voladura con avance de 3 metros y diametro de taladro 45"
    if len(sys.argv) > 1:
        test_input = " ".join(sys.argv[1:])

    resultado = procesar_input_minero(test_input)
    print("Salida para TTS o Sistema:", resultado)
