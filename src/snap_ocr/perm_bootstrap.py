from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
import subprocess
from functools import lru_cache


def _load_library(name: str) -> ctypes.CDLL | None:
    path = ctypes.util.find_library(name)
    if not path:
        return None
    try:
        return ctypes.CDLL(path)
    except OSError:
        return None


@lru_cache(maxsize=1)
def _core_graphics() -> ctypes.CDLL | None:
    return _load_library("CoreGraphics")


@lru_cache(maxsize=1)
def _app_services() -> ctypes.CDLL | None:
    return _load_library("ApplicationServices")


def ensure_screen_recording() -> None:
    """Trigger the Screen Recording prompt on macOS."""
    if platform.system() != "Darwin":
        return
    cg = _core_graphics()
    if not cg:
        return
    try:
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
        cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool
    except AttributeError:
        return
    try:
        if not cg.CGPreflightScreenCaptureAccess():
            cg.CGRequestScreenCaptureAccess()
    except Exception:
        pass


def ensure_accessibility() -> None:
    """Open System Settings if Accessibility permission is missing."""
    if platform.system() != "Darwin":
        return
    app = _app_services()
    if not app:
        return
    try:
        app.AXIsProcessTrusted.restype = ctypes.c_bool
        trusted = app.AXIsProcessTrusted()
    except AttributeError:
        return
    except Exception:
        return
    if trusted:
        return
    subprocess.run([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    ], check=False)


def bootstrap_permissions() -> None:
    if platform.system() != "Darwin":
        return
    ensure_screen_recording()
    ensure_accessibility()
