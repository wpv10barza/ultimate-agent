# Ultimate Agent — snapshot legacy de Drive (2026-06-12)

Snapshot histórico real de la carpeta `ultimate agent 2`, preservado como rama `legacy/drive-2026-06-12` dentro del repositorio canónico `wpv10barza/ultimate-agent`.

La comparación SHA-256 contra el snapshot del 13 de junio demostró una sola línea evolutiva: 19 archivos comunes eran idénticos y solo `app.py` difería. Los seis archivos relacionados con V7–V9/EXE no existían todavía en este snapshot y se excluyen de esta rama.

Las rutas locales personales de `app.py` fueron parametrizadas igual que en la rama canónica; la lógica histórica se conserva y el hash del origen Drive está registrado en `MIGRATION_MANIFEST.md`.

Esta rama es histórica y no debe fusionarse sobre `main` como estado activo.