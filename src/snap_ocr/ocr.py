from __future__ import annotations

import re
from typing import Optional

from PIL import Image, ImageEnhance
import pytesseract
from pytesseract import TesseractNotFoundError

from .errors import ErrorCode, SnapOcrError


def _prepare_for_ocr(img: Image.Image) -> Image.Image:
    """Convert to grayscale and boost contrast to help OCR."""
    gray = img.convert("L")
    enhancer = ImageEnhance.Contrast(gray)
    return enhancer.enhance(1.8)


def _normalize_choices(text: str) -> str:
    """Collapse duplicated choice prefixes like 'Cc.' to 'C.'."""
    pattern = re.compile(r"^([A-Ha-h])([A-Ha-h])([.)])(\s*)", re.MULTILINE)

    def repl(match: re.Match[str]) -> str:
        first = match.group(1)
        second = match.group(2)
        punct = match.group(3)
        spacing = match.group(4)
        if first.lower() == second.lower():
            return f"{first.upper()}{punct}{spacing}"
        return match.group(0)

    return pattern.sub(repl, text)


def perform_ocr(img: Image.Image, lang: str, tesseract_cmd: Optional[str] = None) -> str:
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        processed = _prepare_for_ocr(img)
        text = pytesseract.image_to_string(processed, lang=lang, config="--psm 6")
        return _normalize_choices(text)
    except TesseractNotFoundError as e:
        raise SnapOcrError(ErrorCode.MISSING_TESSERACT, build_tesseract_missing_message(tesseract_cmd), e)
    except Exception as e:
        raise SnapOcrError(ErrorCode.OCR_FAILED, build_ocr_failed_message(e), e)


def build_tesseract_missing_message(tesseract_cmd: Optional[str]) -> str:
    cmd_note = f"Currently configured tesseract_cmd: {tesseract_cmd}" if tesseract_cmd else "No tesseract_cmd configured."
    return (
        "Tesseract not found. Install and ensure it’s on PATH, or set 'tesseract_cmd' in config.yaml.\n"
        "- macOS: brew install tesseract\n"
        "- Windows: install official Tesseract, then add its install folder (with tesseract.exe) to PATH.\n"
        f"{cmd_note}"
    )


def build_ocr_failed_message(exc: Exception) -> str:
    return (
        f"OCR failed: {exc}\n"
        "Possible causes: missing language data (set 'ocr_lang' correctly, e.g., 'eng+spa'), tiny fonts, or unusual scaling.\n"
        "Try installing needed language packs or adjusting 'ocr_lang' in config.yaml."
    )
