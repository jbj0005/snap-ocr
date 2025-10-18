from __future__ import annotations

from PIL import Image
import mss

from .errors import ErrorCode, SnapOcrError


def capture_full_screenshot() -> Image.Image:
    """
    Capture the full virtual screen across all monitors (monitor 0 in mss).
    Returns a PIL Image in RGB.
    """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return img
    except mss.exception.ScreenShotError as e:  # type: ignore[attr-defined]
        # Common on macOS without permissions
        raise SnapOcrError(
            ErrorCode.SCREENSHOT_PERMISSION,
            "Screen capture failed; likely missing Screen Recording permission.",
            e,
        )


def capture_region(left: int, top: int, width: int, height: int) -> Image.Image:
    bbox = {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
    if bbox["width"] <= 0 or bbox["height"] <= 0:
        raise SnapOcrError(ErrorCode.CAPTURE_FAILED, f"Invalid region size: {bbox}")
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(bbox)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return img
    except mss.exception.ScreenShotError as e:  # type: ignore[attr-defined]
        raise SnapOcrError(
            ErrorCode.SCREENSHOT_PERMISSION,
            "Region capture failed; likely missing permission or invalid region.",
            e,
        )
    except Exception as e:
        raise SnapOcrError(ErrorCode.CAPTURE_FAILED, f"Failed to capture region: {e}", e)
    except Exception as e:
        raise SnapOcrError(
            ErrorCode.CAPTURE_FAILED,
            f"Failed to capture screen: {e}",
            e,
        )
