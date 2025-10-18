from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from platformdirs import user_config_dir, user_state_dir


APP_NAME = "snap-ocr"


def get_config_dir() -> str:
    return user_config_dir(APP_NAME, ensure_exists=True)


def get_state_dir() -> str:
    path = user_state_dir(APP_NAME, ensure_exists=True)
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> str:
    path = os.path.join(get_state_dir(), "logs")
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_log_file_path() -> Optional[str]:
    # Conventional path: logs/app.log
    path = os.path.join(get_logs_dir(), "app.log")
    return path if os.path.exists(path) else None


def get_config_path() -> str:
    return os.path.join(get_config_dir(), "config.yaml")


def default_images_dir() -> str:
    home = Path.home()
    # Prefer Pictures/snap-ocr if Pictures exists
    pictures = home / "Pictures"
    if pictures.exists():
        return str(pictures / "snap-ocr")
    return str(Path(get_state_dir()) / "images")


def default_text_dir() -> str:
    home = Path.home()
    documents = home / "Documents"
    if documents.exists():
        return str(documents / "snap-ocr")
    return str(Path(get_state_dir()) / "text")


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def open_in_text_editor(path: str) -> None:
    """
    Open a file in the user's default text editor, creating it first if needed.
    On macOS this uses `open -t` so Launch Services routes it to the default editor
    (TextEdit, VS Code, etc.) instead of Finder. On Linux it prefers $VISUAL/$EDITOR,
    falling back to xdg-open. On Windows it uses os.startfile.
    """
    p = Path(path)
    # Ensure parent exists and the file exists so OS launchers don't silently fail.
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.touch()
    if sys.platform == "win32":
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        # -t = open in the default text editor
        subprocess.run(["open", "-t", str(p)], check=False)
    else:
        # Prefer a real editor if the environment defines one, else fall back.
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
        if editor:
            subprocess.run([editor, str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p)], check=False)


def open_in_file_manager(path: str) -> None:
    p = Path(path)
    # If this looks like a file path (either it exists as a file or has an extension),
    # open it in the default text editor. Otherwise treat it as a directory.
    if (p.exists() and p.is_file()) or (p.suffix and not p.is_dir()):
        open_in_text_editor(str(p))
        return
    if sys.platform == "win32":
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(p)], check=False)
    else:
        subprocess.run(["xdg-open", str(p)], check=False)


def open_file(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", "-t", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
