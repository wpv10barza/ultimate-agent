# MIGRATION_MANIFEST

- source: Google Drive
- source_folder_current: `ultimate agent`
- source_folder_legacy: `ultimate agent 2`
- project_family: `Ultimate Agent / MINEXcellence`
- version_current: `Drive snapshot 2026-06-13 (V9 documentation present)`
- version_legacy: `Drive snapshot 2026-06-12`
- github_repository: `wpv10barza/ultimate-agent`
- github_branch: `main`
- github_commit: `a8ea73f5c12661abe6eeabaa9869bee1ea8c88e5`
- files_expected_current: `26`
- files_migrated_current: `26`
- verification_status: `VERIFIED`
- verified_at: `2026-10-01T05:54:19Z`
- deletion_allowed: `FALSE`
- drive_status: `CONSERVADO`

## Genealogía

- Los snapshots son una sola línea evolutiva.
- Comparación del contenido común: 19 archivos idénticos por SHA-256 y `app.py` diferente.
- El snapshot del 13 de junio agrega `CREAR_EXE_WINDOWS.bat`, `CREAR_EXE_WINDOWS.ps1`, `requirements-exe.txt` y documentación V7–V9.
- `training_data.jsonl` está mencionado por la documentación, pero no fue encontrado en el inventario real de ninguno de los snapshots auditados.

## Transformaciones de seguridad/portabilidad

- Se eliminaron configuraciones locales personales de `app.py` mediante variables de entorno `MINEXCELLENCE_BANNER` y `MINEXCELLENCE_EXPORT_DIR` con valores locales seguros.
- En la documentación se sustituyeron rutas locales personales por `<ruta-local>\ultimate agent`.
- No se encontraron API keys, tokens, contraseñas ni claves privadas en el conjunto migrado.
- No se suben ejecutables generados, entornos virtuales, cachés, modelos descargados ni secretos.

## Hashes SHA-256

| Archivo | SHA-256 origen Drive | SHA-256 canónico | Estado |
|---|---|---|---|
| `CREAR_EXE_WINDOWS.bat` | `27bc9e35e035c9e67b715dc1ea8f3ed77a8dc16b3019004fb81bfb753db5b2ea` | `27bc9e35e035c9e67b715dc1ea8f3ed77a8dc16b3019004fb81bfb753db5b2ea` | idéntico |
| `CREAR_EXE_WINDOWS.ps1` | `f7945374afc085a1addfa9a7f3f223ff548e181bcb7dc160198b07547f61c724` | `f7945374afc085a1addfa9a7f3f223ff548e181bcb7dc160198b07547f61c724` | idéntico |
| `INSTALAR_Y_VERIFICAR.bat` | `7f6ebf1d2f1d5d5f3f6597dd5d0ae3273f233358fc19e19dc049af3b8dc25b42` | `7f6ebf1d2f1d5d5f3f6597dd5d0ae3273f233358fc19e19dc049af3b8dc25b42` | idéntico |
| `app.py` | `4ceb6907829dc0d413f6e3293a002046e92fe5bf4565a3e1a7c99c48c9cb68df` | `9a2f27e55e52935ffebf9f4db82ab028257a8c768e41072665f7fc842ecce4ce` | saneado/parametrizado |
| `diccionario_minero.json` | `b5066735c026df46ebf4f8538bbd1fb27443e00d2959bcda28d47ded4e4ba76a` | `b5066735c026df46ebf4f8538bbd1fb27443e00d2959bcda28d47ded4e4ba76a` | idéntico |
| `docs/LEEME_CORRECCION_API_V4.txt` | `8a9ec714fc46e3f72e772b8a41597d744331a1184cd21b8175d0bfd7a962edac` | `8a9ec714fc46e3f72e772b8a41597d744331a1184cd21b8175d0bfd7a962edac` | idéntico |
| `docs/LEEME_CORRECCION_EXE_V9.txt` | `b58ddcda49f99eaa8e8ecf8a029c1e683d74beb0922153afe77ac1c91b5a885a` | `b58ddcda49f99eaa8e8ecf8a029c1e683d74beb0922153afe77ac1c91b5a885a` | idéntico |
| `docs/LEEME_CORRECCION_TTS_RESULTADOS_V7.txt` | `834bfb4b24951cfcbf0b775e46e16c5bd128d6fb4ef1a2b94984b3045c9d15fe` | `cd20857ff1a4fe7c03dd7ae8cc8554e2c81fb81cf1c8f36b806c047109e71b7c` | saneado/parametrizado |
| `docs/LEEME_CREAR_EXE_V8.txt` | `dc30e3a455eb124c508543f1ddb13b8f89ad777a1a95cef85916c5905e2d4c58` | `3381dec520ca36f4311ab28b2f490aec45c055c9352e51b1ea6b9f33ef7c93a7` | saneado/parametrizado |
| `docs/LEEME_INSTALACION_MODULOS_V6.txt` | `d68b4e1db5c2f0e03f4e4040f7bd536fdb99db286f6569c0b79addf2c6c6496a` | `4c665b12443f0c8fa4a00fed6a57e987e69a0f42f17cd8d96fec1e8f6015279f` | saneado/parametrizado |
| `docs/LEEME_MODULOS_VOZ_TTS_V5.txt` | `d68b4e1db5c2f0e03f4e4040f7bd536fdb99db286f6569c0b79addf2c6c6496a` | `4c665b12443f0c8fa4a00fed6a57e987e69a0f42f17cd8d96fec1e8f6015279f` | saneado/parametrizado |
| `docs/LEEME_NUEVA_VERSION.txt` | `7495533d9b2ac4836aad1fee478a842ce1720015ec657855ea654bc76d9c3f09` | `b46c175938fd6ce521ed83754a7bb533fe49020c7be8b8a598858e934596c02f` | saneado/parametrizado |
| `generar_training_data.py` | `802521e2270524337fa2a344beb89df8e69e030ab342af30af80779ab0ffbcc1` | `802521e2270524337fa2a344beb89df8e69e030ab342af30af80779ab0ffbcc1` | idéntico |
| `instalar_modulos_linux_pi.sh` | `b07eb201c4756b19dd67cee844a27a8237d28a68913d6f4f3fba089319a2ee70` | `b07eb201c4756b19dd67cee844a27a8237d28a68913d6f4f3fba089319a2ee70` | idéntico |
| `instalar_modulos_windows.ps1` | `d8d743f56305daa517465ce5cdc5d90bce03c8a8c681cfcc0d21dc98a882d512` | `d8d743f56305daa517465ce5cdc5d90bce03c8a8c681cfcc0d21dc98a882d512` | idéntico |
| `pretraining_status.py` | `33e123784e5298d67b0ca7e2e45d7b661724795ed983b7c7aa0f3e3d05ed22ef` | `33e123784e5298d67b0ca7e2e45d7b661724795ed983b7c7aa0f3e3d05ed22ef` | idéntico |
| `requirements-exe.txt` | `5a4eece01540b941f8295113419854ea879575b156cd9c34b0461292ceaede3c` | `5a4eece01540b941f8295113419854ea879575b156cd9c34b0461292ceaede3c` | idéntico |
| `requirements-router.txt` | `1fc32158fd3ab324ee92d7f05feb0620c84f9aa3de7c093f7c5222628c2e3724` | `1fc32158fd3ab324ee92d7f05feb0620c84f9aa3de7c093f7c5222628c2e3724` | idéntico |
| `requirements-voice-windows.txt` | `8f76b97037a582e6fc5a27b652b19ec122519c0450603692ec8800c7b26e5d80` | `8f76b97037a582e6fc5a27b652b19ec122519c0450603692ec8800c7b26e5d80` | idéntico |
| `requirements.txt` | `5b9ac12b0e430bae528da9061774cbc327cd32877bab0a59a460dc23e433a749` | `5b9ac12b0e430bae528da9061774cbc327cd32877bab0a59a460dc23e433a749` | idéntico |
| `tool_ai.py` | `88d6779d39869bda3092e69ffd68e9013f7a21f96a72c238940bd419eb6fad53` | `88d6779d39869bda3092e69ffd68e9013f7a21f96a72c238940bd419eb6fad53` | idéntico |
| `tools.json` | `9894dcf8112a48059f240b76cd1843806a6557d3dee24af42b8fa32ecad3d828` | `9894dcf8112a48059f240b76cd1843806a6557d3dee24af42b8fa32ecad3d828` | idéntico |
| `tts_piper.py` | `b30bafe7d344f73593a80ac4fa997bf9e2b977c97dbf94850b3f5e2bd294154d` | `b30bafe7d344f73593a80ac4fa997bf9e2b977c97dbf94850b3f5e2bd294154d` | idéntico |
| `ver_modulos_voz_tts.ps1` | `3b8f0b46eed12b01c35b6eaafea000d5e81816094805b5ee13a7d595c62f1d24` | `3b8f0b46eed12b01c35b6eaafea000d5e81816094805b5ee13a7d595c62f1d24` | idéntico |
| `ver_preentrenamiento.ps1` | `8fd720e54d7a0b49352c5974e66e636baf17455a575317c04e2c02e80a937f36` | `8fd720e54d7a0b49352c5974e66e636baf17455a575317c04e2c02e80a937f36` | idéntico |
| `verificar_entorno.py` | `a43d71054f02ccb608b23e3ebf180e341f1c4a556ab8720c4a04bf4d2ff58589` | `a43d71054f02ccb608b23e3ebf180e341f1c4a556ab8720c4a04bf4d2ff58589` | idéntico |
