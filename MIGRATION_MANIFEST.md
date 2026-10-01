# MIGRATION_MANIFEST — legacy/drive-2026-06-12

- source: Google Drive
- source_folder: `ultimate agent 2`
- source_folder_id: `1r1_yqJeI69QbXMEd-fyUkFnvRZ8-qGeB`
- project_family: `Ultimate Agent / MINEXcellence`
- snapshot_date: `2026-06-12`
- github_repository: `wpv10barza/ultimate-agent`
- github_branch: `legacy/drive-2026-06-12`
- relation: `snapshot anterior de la misma línea evolutiva`
- source_files: `20`
- common_with_2026_06_13: `20`
- common_identical_sha256: `19`
- common_different: `app.py`
- app_source_sha256: `6b52140a2705ab457154e42350a223b830a3d9f7a29c2028c1495a3922a4ec82`
- app_published_sha256: `6afd27004978e66b9a4b6543899cdf78ea2c7245d192373b183b1f093d0d043a`
- verification_status: `PENDING_BRANCH_CI`
- deletion_allowed: `FALSE`
- drive_status: `CONSERVADO`

## Diferencias frente al snapshot 2026-06-13

El snapshot posterior agrega seis archivos que no se incluyen aquí:

- `CREAR_EXE_WINDOWS.bat`
- `CREAR_EXE_WINDOWS.ps1`
- `requirements-exe.txt`
- `docs/LEEME_CORRECCION_TTS_RESULTADOS_V7.txt`
- `docs/LEEME_CREAR_EXE_V8.txt`
- `docs/LEEME_CORRECCION_EXE_V9.txt`

## Publicación segura

`app.py` conserva la lógica del snapshot del 12 de junio, pero las rutas locales personales fueron sustituidas por `MINEXCELLENCE_BANNER` y `MINEXCELLENCE_EXPORT_DIR`. No se incluyen ejecutables generados, secretos, entornos virtuales, cachés ni modelos descargados.
