"""
README.md — Snap OCR (Tray Hotkey Screenshot + OCR)

Overview
- Cross-platform background utility for macOS 12+ and Windows 10/11.
- Global hotkey (Ctrl+Shift+S by default) takes a full-screen screenshot (all monitors), performs OCR, and saves PNG + TXT.
- Stays in the system tray; no windows or focus stealing.
- Debounced triggers; Consecutive Mode overwrites files with fixed base name.
- YAML config with sensible defaults; logs with rotation; robust error surfaces and notifications.

Key Features
- Global hotkey via pynput: default "<ctrl>+<shift>+s" (configurable).
- Screenshot via mss across all displays (monitor 0 virtual screen).
- OCR via pytesseract; clear errors if Tesseract missing or language packs absent.
- Atomic writes for PNG and TXT.
- Tray actions: Take Screenshot, Toggle Consecutive Mode, Open Folders, Reload Config, View Log, View Last Error, Quit.
- Notifications via plyer; gracefully degrades if notifications unavailable.
- No network traffic; screenshots and OCR outputs stay local.

Installation (Python 3.10+)
1) Create and activate a virtual environment (recommended)
   - Windows (PowerShell): `py -3.10 -m venv .venv && .\\.venv\\Scripts\\Activate.ps1`
   - macOS: `python3.10 -m venv .venv && source .venv/bin/activate`
2) Install dependencies
   - `pip install -r requirements.txt`
   - or `pip install .` from project root (pyproject.toml)
3) Install Tesseract OCR
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
- Tray menu:
  - Take Screenshot Now
  - Toggle Consecutive Mode (✓/✗)
  - Open Images Folder
  - Open Text Folder
  - Reload Config
  - View Log File…
  - View Last Error…
  - Quit

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
- Consecutive mode: constant filenames overridden across multiple presses.
- OCR output non-empty for a window with visible text.
- macOS missing permissions: actionable guidance appears; after granting and relaunching app, works.
- Debounce prevents duplicates from rapid presses (500 ms default).

"""
from .app import App


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()

