"""
README.md — Snap OCR (Tray Hotkey Screenshot + OCR)

Overview
- Cross-platform background utility for macOS 12+ and Windows 10/11.
- Global hotkey (Ctrl+Shift+S by default) takes a full-screen screenshot (all monitors), performs OCR, and saves PNG + TXT.
- Stays in the system tray; no windows or focus stealing.
- Debounced triggers; Overwrite Mode keeps only the most recent capture (previous files are deleted).
- YAML config with sensible defaults; logs with rotation; robust error surfaces and notifications.

Key Features
- Global hotkey via pynput: default "<ctrl>+<shift>+s" (configurable).
- Screenshot via mss across all displays (monitor 0 virtual screen).
- OCR via pytesseract; clear errors if Tesseract missing or language packs absent.
- Atomic writes for PNG and TXT.
- Tray actions: Take Screenshot, Toggle Overwrite Mode, Open Folders, Reload Config, View Log, View Last Error, Quit.
- Notifications via plyer; gracefully degrades if notifications unavailable.
- No network traffic; screenshots and OCR outputs stay local.

Installation (Python 3.10+)
1) Preferred: `pipx install .` from the project root (adds `snap-ocr` to PATH).
   - Alternative: create and activate a venv (`python -m venv .venv`), then `pip install -r requirements.txt` and `pip install -e .`.
2) Install Tesseract OCR
   - macOS (Homebrew):
     - `brew install tesseract`
     - Optional languages: `brew install tesseract-lang`
   - Windows:
     - Download and install “Tesseract OCR” from the official source (UB Mannheim build recommended).
     - Add the `tesseract.exe` install folder to PATH (e.g., `C:\\Program Files\\Tesseract-OCR\\`) or set `tesseract_cmd` in config.
4) First run creates a config file at platform config dir (see path in logs).
   - Edit `ocr_lang`, directories, hotkey, etc., then use tray “Reload Config”.

macOS Permissions (Ventura/Sonoma)
- On first screenshot attempt, you may get black images if Screen Recording is not allowed.
- Grant:
  - System Settings → Privacy & Security → Screen Recording → enable for Terminal/Python/your app.
  - System Settings → Privacy & Security → Accessibility → enable for Terminal/Python/your app (hotkeys).
  - System Settings → Privacy & Security → Input Monitoring → enable if macOS prompts for keyboard hooks.
- After changing permissions, quit & relaunch the app (no OS restart required).

Windows Notes
- Windows 10/11: No special screen recording permission; ensure Tesseract is installed and on PATH.
- Defender SmartScreen: Use “Run anyway” if warned.
- Optional: Run once as Administrator to fix folder permissions if needed.

Usage
- Start: `python -m snap_ocr` (tray icon appears).
- Trigger: Press Ctrl+Shift+S anywhere; PNG + TXT saved.
- Tray menu: Take Screenshot, toggle Overwrite Mode, open output folders, reload the config, view logs, or quit.

Troubleshooting Matrix
- Hotkey doesn’t fire on macOS → Accessibility permission needed.
  - System Settings → Privacy & Security → Accessibility → enable for Terminal/Python.
- Black images on macOS → Screen Recording permission missing.
  - System Settings → Privacy & Security → Screen Recording → enable for Terminal/Python. Then quit and relaunch the app.
- “Tesseract not found” → Install + PATH, or set `tesseract_cmd` in config.
  - macOS: `brew install tesseract`
  - Windows: Install official Tesseract, add folder to PATH.
- OCR empty → Wrong language or tiny font or HiDPI scaling.
  - Set `ocr_lang` correctly (e.g., `eng+spa`); zoom or enlarge text.
- PermissionError on save → Choose a writable dir, fix ACL, or run once as admin.
- Hotkey conflict → Change `hotkey` in config to a different combination.
- Notifications missing → Logs still record success; tray “View Last Error…” shows failures.

Security & Privacy
- Screenshots and text never leave local disk.
- No network calls.
- Logs avoid sensitive content (only file paths and error messages).

Uninstall & Data Purge
- Stop the app (Quit from tray).
- Remove the installed package (if installed): `pip uninstall snap-ocr` or delete the project folder if running from source.
- Delete config and logs:
  - Config dir: platform-specific (see logs or `config.py`).
  - State dir: contains logs; remove that folder to purge logs and cached state.

Packaging
- Pipx: `pipx install .` then run `python -m snap_ocr`.
- PyInstaller (single-file)
  - Windows: `pyinstaller --onefile --noconsole -n snap-ocr src/snap_ocr/__main__.py`
  - macOS: `pyinstaller --onefile -n snap-ocr src/snap_ocr/__main__.py`
  - For macOS codesign/notarize: sign the app bundle post-build (optional).

Acceptance Tests (Manual)
- Hotkey triggers screenshot while focusing another app → PNG+TXT saved correctly.
- Normal mode: filenames with timestamp suffix (YYYYMMDD_HHMMSS).
- Overwrite mode: constant filenames overridden across multiple presses.
- OCR output non-empty for a window with visible text.
- macOS missing permissions: actionable guidance appears; after granting and relaunching app, works.
- Debounce prevents duplicates from rapid presses (500 ms default).

"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Optional, Sequence

from snap_ocr.app import App, Job
from snap_ocr.config import ConfigValidationError, load_or_create_config, save_config_if_first_run
from snap_ocr.paths import get_config_path, open_in_file_manager
from snap_ocr.perm_bootstrap import bootstrap_permissions


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snap OCR tray utility")
    parser.add_argument(
        "--capture-once",
        action="store_true",
        help="Take a capture immediately and exit (no tray).",
    )
    parser.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the active config.yaml path and exit.",
    )
    parser.add_argument(
        "--open-config",
        action="store_true",
        help="Open config.yaml in the default file manager.",
    )
    args = parser.parse_args(argv)
    selected = sum(bool(flag) for flag in (args.capture_once, args.show_config_path, args.open_config))
    if selected > 1:
        parser.error("Options are mutually exclusive; choose only one.")
    return args


def _ensure_config() -> str:
    cfg = load_or_create_config()
    save_config_if_first_run(cfg)
    return get_config_path()


def _print_config_error(message: str) -> None:
    path = get_config_path()
    print(
        f"Configuration error: {message}\n"
        f"Fix: Edit {path} (use 'snap-ocr --open-config') to correct the value, then retry.",
        file=sys.stderr,
    )


def _capture_once() -> int:
    app = App()
    try:
        result = app._process_job(Job(reason="cli", requested_at=time.monotonic()))
    finally:
        try:
            app.hotkey.stop()
        except Exception:
            pass
    if result:
        img_path, txt_path = result
        print(f"Saved image: {img_path}")
        print(f"Saved text:  {txt_path}")
        return 0
    print("Capture failed; see the log for details.", file=sys.stderr)
    return 1


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    try:
        bootstrap_permissions()
        if args.show_config_path:
            print(_ensure_config())
            return
        if args.open_config:
            open_in_file_manager(_ensure_config())
            return
        if args.capture_once:
            raise SystemExit(_capture_once())

        app = App()
        app.run()
    except ConfigValidationError as exc:
        _print_config_error(str(exc))
        config_path = get_config_path()
        if args.show_config_path:
            print(config_path)
            return
        if args.open_config:
            open_in_file_manager(config_path)
            return
        raise SystemExit(1)


if __name__ == "__main__":
    main()
