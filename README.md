# Snap OCR

Tray hotkey background screenshot + OCR utility for macOS and Windows.

For full documentation, see the embedded README in `src/snap_ocr/__main__.py`.

## Installation Options

### pipx (recommended)
```bash
pipx install .
snap-ocr  # launches the tray app
```
- Pipx keeps the tool isolated in its own virtualenv and adds a `snap-ocr` command to your `PATH`.
- macOS: after launch, look for the tray icon (dark circle with an “S”) in the menu bar and click it to access controls.

### From source (virtualenv)
```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
python -m pip install -r requirements.txt
python -m pip install -e .
python -m snap_ocr
```
- Windows PowerShell: ``py -3.10 -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.txt``.

## Command-line Shortcuts
- `snap-ocr --capture-once` grabs one screenshot + OCR and exits (no tray).
- `snap-ocr --show-config-path` prints the active `config.yaml` path.
- `snap-ocr --open-config` opens `config.yaml` in Finder/File Explorer for quick edits.

## Configuration
- First run creates `config.yaml` in the user config directory (`~/Library/Application Support/snap-ocr/config.yaml` on macOS, `%APPDATA%\snap-ocr\config.yaml` on Windows).
- Edit the file to change the hotkey (`hotkey`), output folders, OCR languages, or enable `consecutive_mode` to overwrite the same filename on every capture.
- Use the tray menu’s “Reload Config” item or restart the app to apply edits.

## Customisation
- Place a PNG icon at `assets/icon.png` (or set the `SNAP_OCR_ICON` env var) and the tray will use it automatically.
- Set `SNAP_OCR_ICON` to an absolute path if you keep the icon elsewhere (useful when packaging).

## Tray Menu Highlights
- Take Screenshot Now – trigger immediately without the hotkey.
- Capture Mode – choose full screen, saved region, or FancyZones (Windows PowerToys).
- Consecutive Mode – toggles overwrite behaviour.
- Open Images/Text Folder – jump straight to output locations.
- Reload Config / View Log File / Quit.

## Auto-start at Login (macOS)
- Create `~/Library/LaunchAgents/com.brandon.snap-ocr.plist` pointing to the pipx interpreter:
  ```
  /Users/brandon/.local/pipx/venvs/snap-ocr/bin/python -m snap_ocr
  ```
- Load it once with `launchctl load ~/Library/LaunchAgents/com.brandon.snap-ocr.plist`. The tray app will now start automatically each login. Adjust the path if your username differs.

## Troubleshooting
- macOS permissions: grant Screen Recording, Accessibility, and Input Monitoring to Terminal/Python if screenshots are black or the hotkey does not fire.
- Ensure Tesseract OCR is installed (`brew install tesseract` on macOS, UB Mannheim installer on Windows) or set `tesseract_cmd` in `config.yaml`.
