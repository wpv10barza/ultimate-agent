# -*- coding: utf-8 -*-
"""
Indicador local de preparacion de fine-tuning/preentrenamiento para functiongemma.
No entrena el modelo: valida dataset, cobertura de variables y disponibilidad en Ollama.
"""
import argparse
import json
import subprocess
from pathlib import Path

REQUERIDOS = ["ancho_seccion", "avance", "diametro_taladro", "densidad_explosivo", "densidad_roca", "resistencia_roca"]

def barra(pct, ancho=24):
    pct = max(0, min(100, int(round(pct))))
    llenos = int(round(ancho * pct / 100))
    return "[" + "#" * llenos + "-" * (ancho - llenos) + f"] {pct}%"

def analizar_dataset(path):
    total = completos = incompletos = invalidos = 0
    cobertura = {k: 0 for k in REQUERIDOS}
    errores = []
    p = Path(path)
    if not p.exists():
        return {"existe": False, "archivo": str(p), "total": 0, "completos": 0, "incompletos": 0, "invalidos": 0, "cobertura": cobertura, "errores": []}
    with p.open("r", encoding="utf-8") as f:
        for nro, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                data = json.loads(line)
                mensajes = data.get("messages", [])
                if len(mensajes) < 2:
                    raise ValueError("messages incompleto")
                calls = mensajes[-1].get("tool_calls", []) or []
                args = calls[0].get("arguments", {}) if calls else {}
                for k in REQUERIDOS:
                    if k in args and args[k] not in (None, ""):
                        cobertura[k] += 1
                if all(k in args and args[k] not in (None, "") for k in REQUERIDOS):
                    completos += 1
                else:
                    incompletos += 1
            except Exception as exc:
                invalidos += 1
                if len(errores) < 5:
                    errores.append(f"linea {nro}: {exc}")
    return {"existe": True, "archivo": str(p), "total": total, "completos": completos, "incompletos": incompletos, "invalidos": invalidos, "cobertura": cobertura, "errores": errores}

def estado_ollama(modelo):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return "error", (r.stderr or r.stdout).strip()
        salida = r.stdout or ""
        presente = any((line.split()[0] == modelo or line.split()[0].split(":")[0] == modelo.split(":")[0]) for line in salida.splitlines()[1:] if line.split())
        return ("ok" if presente else "faltante"), salida.strip()
    except FileNotFoundError:
        return "faltante", "No se encontro el comando ollama. Abre/instala Ollama Desktop."
    except Exception as exc:
        return "error", str(exc)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="training_data.jsonl")
    parser.add_argument("--model", default="functiongemma")
    args = parser.parse_args()
    ds = analizar_dataset(args.dataset)
    print("---------------------------------------------")
    print("INDICADOR DE PREENTRENAMIENTO / FINE-TUNING")
    print("---------------------------------------------")
    print("Nota: este indicador valida preparacion local; no ejecuta entrenamiento.")
    print(f"Dataset: {ds['archivo']}")
    if not ds["existe"]:
        print("Estado dataset: FALTANTE")
    else:
        total = ds["total"] or 1
        print(f"Lineas JSONL: {ds['total']}")
        print(f"Completas: {ds['completos']} | Incompletas controladas: {ds['incompletos']} | Invalidas: {ds['invalidos']}")
        print("Calidad estructural:", barra(100 * (ds['total'] - ds['invalidos']) / total))
        print("Ejemplos completos:", barra(100 * ds['completos'] / total))
        print("Cobertura por variable:")
        for k in REQUERIDOS:
            print(f"  - {k:<20} {barra(100 * ds['cobertura'][k] / total, 18)} ({ds['cobertura'][k]}/{ds['total']})")
        if ds["errores"]:
            print("Errores de muestra:")
            for e in ds["errores"]:
                print("  ", e)
    estado, detalle = estado_ollama(args.model)
    print("\n---------------------------------------------")
    print("MODELO LOCAL OLLAMA")
    print("---------------------------------------------")
    print(f"Modelo esperado: {args.model}")
    print(f"Estado: {estado}")
    if estado != "ok":
        print("Accion sugerida: ollama pull functiongemma")
    print("\nResumen ollama list:")
    print(detalle or "Sin salida")

if __name__ == "__main__":
    main()
