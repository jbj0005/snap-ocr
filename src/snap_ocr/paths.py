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


def open_in_file_manager(path: str, reveal: bool = False) -> None:
    if sys.platform == "win32":
        if reveal and os.path.isfile(path):
            subprocess.run(["explorer", "/select,", path.replace("/", "\\")], check=False)
        else:
            os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        if reveal and os.path.exists(path):
            result = subprocess.run(["open", "-R", path], check=False)
            if result.returncode == 0:
                return
        subprocess.run(["open", path], check=False)
    else:
        target = path
        if reveal and os.path.isfile(path):
            target = os.path.dirname(path) or "."
        subprocess.run(["xdg-open", target], check=False)



def open_file(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
