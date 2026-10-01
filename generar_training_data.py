# -*- coding: utf-8 -*-
"""
Generador base del dataset JSONL para fine-tuning de functiongemma.
El archivo incluido training_data.jsonl ya contiene ejemplos completos e incompletos.
Amplia este script con frases reales de mina antes de entrenar.
"""
from pathlib import Path
import json

EJEMPLOS_BASE = [
    {
        "messages": [
            {"role": "user", "content": "Prepárame el tiro para una rampa. La sección es de 4 metros por 4, avance 3.5, taladro 45 milímetros, roca 2.7 t/m3, resistencia 120 MPa y anfo 0.8."},
            {"role": "assistant", "tool_calls": [{"name": "calcular_voladura", "arguments": {"ancho_seccion": 4.0, "avance": 3.5, "diametro_taladro": 45, "densidad_roca": 2.7, "resistencia_roca": 120, "densidad_explosivo": 0.8}}]}
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "Cálculo de malla: taladro 64mm, sección 5m, avance 4m. Densidad del explosivo 1.1 g/cc, roca 2.6 toneladas el cubo y 100 MPa."},
            {"role": "assistant", "tool_calls": [{"name": "calcular_voladura", "arguments": {"ancho_seccion": 5.0, "avance": 4.0, "diametro_taladro": 64, "densidad_roca": 2.6, "resistencia_roca": 100, "densidad_explosivo": 1.1}}]}
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "Solo tengo avance 3 metros y broca 45 mm."},
            {"role": "assistant", "tool_calls": [{"name": "calcular_voladura", "arguments": {"avance": 3.0, "diametro_taladro": 45}}]}
        ]
    }
]

def main():
    salida = Path("training_data_extra.jsonl")
    with salida.open("w", encoding="utf-8") as f:
        for ej in EJEMPLOS_BASE:
            f.write(json.dumps(ej, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Dataset generado: {salida.resolve()}")

if __name__ == "__main__":
    main()
