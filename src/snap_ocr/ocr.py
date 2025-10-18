from __future__ import annotations

from typing import Optional

from PIL import Image
import pytesseract
from pytesseract import TesseractNotFoundError

from .errors import ErrorCode, SnapOcrError


def perform_ocr(img: Image.Image, lang: str, tesseract_cmd: Optional[str] = None) -> str:
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        text = pytesseract.image_to_string(img, lang=lang)
        return text
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

