from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    MISSING_TESSERACT = "MISSING_TESSERACT"
    SCREENSHOT_PERMISSION = "SCREENSHOT_PERMISSION"
    SAVE_PERMISSION = "SAVE_PERMISSION"
    HOTKEY_REGISTER = "HOTKEY_REGISTER"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    OCR_FAILED = "OCR_FAILED"
    CONFIG_INVALID = "CONFIG_INVALID"
    OTHER = "OTHER"


@dataclass
class SnapOcrError(Exception):
    code: ErrorCode
    message: str
    cause: Optional[Exception] = None

    def __str__(self) -> str:
        return self.message

