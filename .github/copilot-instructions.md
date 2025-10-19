## Snap OCR — Copilot instructions (concise)

This repository is a small tray utility (macOS/Windows) that captures screenshots, runs Tesseract OCR, and writes image + text files.
Keep suggestions focused, actionable, and tied to the files listed below.

Key concepts (what you should know immediately)

- Entry point: `snap-ocr` CLI entry point -> `src/snap_ocr/__main__.py` (packaged in `pyproject.toml` as `snap-ocr`).
- Main runtime: `src/snap_ocr/app.py` (App class). Hotkey triggers or tray menu enqueue Jobs processed on a worker thread.
- Capture code: `src/snap_ocr/screenshot.py` (full & region capture via mss) and `src/snap_ocr/region_capture.py` (region picker + Windows FancyZones integration).
- OCR: `src/snap_ocr/ocr.py` (wraps pytesseract). Tesseract must be installed or `tesseract_cmd` set in config.
- Config: `src/snap_ocr/config.py` (DEFAULTS, validation). Important: `image_format` is enforced to "PNG".
- Tray UI: `src/snap_ocr/tray.py` (pystray icon + menu). Hotkey handling lives in `src/snap_ocr/hotkey.py`.
- Errors: `src/snap_ocr/errors.py` (SnapOcrError + ErrorCode). Prefer raising or returning those for consistent messages.

Developer workflows & commands

- Run from source (recommended for dev):
  - Create venv, install deps: `python -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt && python -m pip install -e .`
  - Launch: `python -m snap_ocr` or `snap-ocr --capture-once` for a headless capture + exit.
- Packaging macOS (existing scripts):
  - Build: `scripts/build_mac_app.sh` (produces `dist/Snap OCR.app`).
  - Sign & notarize: `scripts/sign_and_notarize.sh` — update `IDENTITY` and `PROFILE` in the script before running.

Project-specific patterns and constraints (do not break these)

- Atomic writes: images/text are written with `util.atomic_write_bytes` / `atomic_write_text`; preserve that pattern to avoid partial files.
- PNG-only: `config._validate` enforces `image_format == 'PNG'`. Do not silently switch formats; update validation and tests if changing.
- Debounce and consecutive mode: triggering is debounced (`debounce_ms`) in `App._is_debounced()`. `consecutive_mode` toggles timestamped filenames vs constant filename.
- Permission bootstrap on macOS: `src/snap_ocr/perm_bootstrap.py` contains logic to trigger Screen Recording / Accessibility prompts. Use it rather than manual OS hints when possible.
- Windows FancyZones: `region_capture.get_fancyzones_region` reads PowerToys JSON files; keep imports deferred (this code expects Windows-only data files).

Where to look for concrete examples

- How capture→OCR→save is implemented: `App._process_job` in `src/snap_ocr/app.py` (this shows capture selection, save paths, OCR call, and notifications).
- Hotkey lifecycle and update behavior: `src/snap_ocr/hotkey.py` (start/stop/update_hotkey). Use `HotkeyManager.update_hotkey(...)` when applying config changes.
- Tray menu wiring: `src/snap_ocr/tray.py` — menu callbacks call `App` public methods (e.g., `take_screenshot_now`, `pick_region`, `reload_config`).

Debugging hints an AI should recommend (concrete)

- If screenshots are black or fail on macOS, point to `perm_bootstrap.ensure_screen_recording()` and recommend granting Screen Recording, Accessibility, Input Monitoring to the Python interpreter or the built `.app`.
- If OCR returns empty or raises missing Tesseract, recommend installing Tesseract and/or setting `tesseract_cmd` in the config; refer to `ocr.build_tesseract_missing_message()` for wording.
- For hotkey registration errors, inspect current `config.hotkey` and suggest changing it; App will call `HotkeyManager.update_hotkey()` on reload.

Testing & safety notes for edits

- There are no unit tests in the repo; prefer small, local verification: run `snap-ocr --capture-once` in a dev venv to validate changes end-to-end.
- Avoid changing global defaults silently. Update `src/snap_ocr/config.py::DEFAULTS` and add migration/docs for users.

If you change packaging or macOS entitlements

- Update `packaging/entitlements.plist` and the `scripts/sign_and_notarize.sh` template values. The build script expects `assets/icon.png` for icon conversion.

Where logs/config live (for user-visible output)

- Config path helpers: `src/snap_ocr/paths.py` (use `get_config_path()` / `get_log_file_path()` when producing guidance).
- First run creates `config.yaml` in the platform config dir (see `config.save_config_if_first_run`).

When to ask the human

- If a change affects default behavior (capture format, default hotkey, save dirs) request explicit approval and a short migration note.

Keep the edits small, self-contained, and linked to the files above. If you need to add a new dependency, mention it and update `pyproject.toml`.
