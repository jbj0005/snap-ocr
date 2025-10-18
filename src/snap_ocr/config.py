from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import yaml

from .paths import (
    default_images_dir,
    default_text_dir,
    get_config_dir,
    get_config_path,
    ensure_dir,
)


@dataclass
class Config:
    save_dir_images: str
    save_dir_text: str
    base_filename: str
    consecutive_mode: bool
    hotkey: str
    image_format: str
    ocr_lang: str
    notify_on_success: bool
    debounce_ms: int
    log_level: str
    tesseract_cmd: Optional[str] = None
    # Capture options
    capture_mode: str = "full"  # "full" | "region" | "fancyzones"
    region: Dict[str, int] = field(default_factory=lambda: {"left": 100, "top": 100, "width": 1280, "height": 720})
    fancyzones_prefer_under_cursor: bool = True
    fancyzones_zone_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "save_dir_images": self.save_dir_images,
            "save_dir_text": self.save_dir_text,
            "base_filename": self.base_filename,
            "consecutive_mode": self.consecutive_mode,
            "hotkey": self.hotkey,
            "image_format": self.image_format,
            "ocr_lang": self.ocr_lang,
            "notify_on_success": self.notify_on_success,
            "debounce_ms": self.debounce_ms,
            "log_level": self.log_level,
            "tesseract_cmd": self.tesseract_cmd,
            "capture_mode": self.capture_mode,
            "region": self.region,
            "fancyzones_prefer_under_cursor": self.fancyzones_prefer_under_cursor,
            "fancyzones_zone_index": self.fancyzones_zone_index,
        }


DEFAULTS = {
    "save_dir_images": default_images_dir(),
    "save_dir_text": default_text_dir(),
    "base_filename": "screenshot",
    "consecutive_mode": False,
    "hotkey": "<ctrl>+<shift>+s",
    "image_format": "PNG",
    "ocr_lang": "eng",
    "notify_on_success": False,
    "debounce_ms": 500,
    "log_level": "INFO",
    "tesseract_cmd": None,
    # New defaults
    "capture_mode": "full",
    "region": {"left": 100, "top": 100, "width": 1280, "height": 720},
    "fancyzones_prefer_under_cursor": True,
    "fancyzones_zone_index": 0,
}


def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = DEFAULTS.copy()
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def _validate(cfg: Dict[str, Any]) -> None:
    if not cfg["save_dir_images"] or not cfg["save_dir_text"]:
        raise ValueError("Output directories cannot be empty.")
    if not cfg["base_filename"]:
        raise ValueError("base_filename cannot be empty.")
    if not isinstance(cfg["debounce_ms"], int) or cfg["debounce_ms"] < 0:
        raise ValueError("debounce_ms must be a non-negative integer.")
    if cfg["image_format"].upper() != "PNG":
        # We only officially support PNG for now; keep this strict and clear.
        raise ValueError("image_format must be 'PNG'.")
    if cfg.get("capture_mode") not in ("full", "region", "fancyzones"):
        raise ValueError("capture_mode must be one of: full | region | fancyzones.")
    reg = cfg.get("region") or {}
    for k in ("left", "top", "width", "height"):
        if k not in reg:
            raise ValueError("region must include left/top/width/height")


def load_or_create_config() -> Config:
    ensure_dir(get_config_dir())
    path = get_config_path()
    data: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
            if not isinstance(raw, dict):
                raise ValueError("Invalid YAML: expected a mapping at top level.")
            data = raw
    merged = _merge_defaults(data)
    _validate(merged)
    # Ensure directories exist or create them
    ensure_dir(merged["save_dir_images"])
    ensure_dir(merged["save_dir_text"])
    return Config(**merged)


def save_config_if_first_run(cfg: Config) -> None:
    """
    If config file does not exist, create it now with the current values.
    """
    path = get_config_path()
    if not os.path.exists(path):
        ensure_dir(get_config_dir())
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg.to_dict(), f, sort_keys=False, allow_unicode=True)


def load_config_example() -> str:
    return """# Example configuration for Snap OCR
# Paths (writable recommended)
save_dir_images: {}
save_dir_text: {}
# Naming
base_filename: screenshot
consecutive_mode: false
# Hotkey (pynput syntax)
hotkey: "<ctrl>+<shift>+s"
# Format and OCR
image_format: PNG
ocr_lang: "eng"
# Behavior
notify_on_success: true
debounce_ms: 500
log_level: INFO
# Optional: set a full path to tesseract executable if not on PATH
# tesseract_cmd: "C:\\\Program Files\\\\Tesseract-OCR\\\\tesseract.exe"
""".format(default_images_dir(), default_text_dir())
