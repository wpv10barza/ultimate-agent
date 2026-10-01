# MINEXcellence Ultimate Agent

Repositorio canónico de la familia **Ultimate Agent** reconstruida desde los snapshots reales de Google Drive `ultimate agent 2` (12 de junio de 2026) y `ultimate agent` (13 de junio de 2026).

## Propósito

Aplicación local en Python/Tkinter para apoyar el diseño y auditoría de cálculos de voladura minera. El código integra Ollama local para extracción/auditoría estructurada de variables, exportación a Excel y funciones opcionales de voz/TTS.

## Tecnologías observadas en el proyecto

- Python y Tkinter.
- Ollama local (`functiongemma`; la aplicación también referencia `qwen3.5:4b`).
- `pandas` y `openpyxl` para exportación Excel.
- Pillow para imagen de interfaz.
- SpeechRecognition, PyAudio opcional y `pyttsx3`/Piper para voz y TTS.
- Scripts PowerShell/BAT para instalación, verificación y generación de ejecutable en Windows.

## Ejecución documentada

La documentación original indica crear un entorno virtual, instalar `requirements.txt`, disponer de Ollama local y ejecutar:

```text
python verificar_entorno.py
python app.py
```

Para el modelo principal documentado se usa `ollama pull functiongemma`. Los archivos de `docs/` conservan las instrucciones históricas V4–V9, con rutas locales personales sustituidas por marcadores genéricos.

## Estructura principal

- `app.py`: interfaz Tkinter y flujo principal.
- `tool_ai.py`: extracción, auditoría y payloads para Ollama/herramientas.
- `tools.json`: definición de herramientas.
- `diccionario_minero.json`: sinónimos de variables mineras.
- `pretraining_status.py`: indicador de preparación local del dataset/modelo.
- `generar_training_data.py`: generador/plantilla de datos de entrenamiento.
- `tts_piper.py`: integración TTS.
- `verificar_entorno.py`: verificación de dependencias/entorno.
- `docs/`: documentación histórica del proyecto.

## Genealogía verificada

El snapshot `ultimate agent 2` del 12 de junio de 2026 contiene 20 archivos. Al compararlo por SHA-256 con el snapshot `ultimate agent` del 13 de junio, 19 archivos son idénticos y `app.py` cambia. El snapshot posterior agrega seis archivos relacionados con V7–V9 y empaquetado EXE. La copia anterior se conserva en la rama `legacy/drive-2026-06-12`.

## Archivo documentado pero no encontrado

`LEEME_NUEVA_VERSION.txt` menciona `training_data.jsonl`, pero ese archivo **no aparece en el inventario real del snapshot auditado de Google Drive**. Por esa razón no se ha creado ni reconstruido artificialmente.

## Archivos excluidos

No se versionan entornos virtuales, cachés, `build/`, `dist/`, ejecutables generados, modelos descargados, archivos `.env`, credenciales ni configuraciones locales personales. Las rutas locales encontradas en `app.py` y en la documentación fueron parametrizadas o sustituidas por marcadores genéricos; sus hashes originales quedan registrados en `MIGRATION_MANIFEST.md`.

## Repositorio canónico

`wpv10barza/ultimate-agent`
