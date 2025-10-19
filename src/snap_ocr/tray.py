from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps
import pystray


def _candidate_icon_paths() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.getenv("SNAP_OCR_ICON")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    try:
        from importlib import resources

        resource_path = resources.files("snap_ocr") / "assets" / "icon.png"  # type: ignore[attr-defined]
        candidates.append(Path(resource_path))
    except Exception:
        pass
    here = Path(__file__).resolve()
    candidates.append(here.parent / "assets" / "icon.png")
    candidates.append(here.parents[1] / "assets" / "icon.png")
    candidates.append(Path.cwd() / "assets" / "icon.png")
    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        try:
            key = candidate.resolve()
        except Exception:
            key = candidate
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _load_custom_icon(size: int) -> Optional[Image.Image]:
    pad_ratio_env = os.getenv("SNAP_OCR_ICON_PAD")
    try:
        pad_ratio = float(pad_ratio_env) if pad_ratio_env is not None else 0.05
    except ValueError:
        pad_ratio = 0.05

    for candidate in _candidate_icon_paths():
        try:
            if candidate.is_file():
                with candidate.open("rb") as fh:
                    img = Image.open(fh).convert("RGBA")
            else:
                continue
        except Exception:
            continue
        else:
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            if pad_ratio > 0:
                w, h = img.size
                pad_w = max(1, int(w * pad_ratio))
                pad_h = max(1, int(h * pad_ratio))
                canvas = Image.new("RGBA", (w + pad_w * 2, h + pad_h * 2), (0, 0, 0, 0))
                canvas.paste(img, (pad_w, pad_h))
                img = canvas
            img = ImageOps.fit(img, (size, size), method=Image.LANCZOS, centering=(0.5, 0.5))
            return img
    return None


def _make_icon(size: int = 32) -> Image.Image:
    custom = _load_custom_icon(size)
    if custom is not None:
        return custom

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Simple monochrome circle with S glyph
    draw.ellipse((1, 1, size - 2, size - 2), fill=(30, 30, 30, 255))
    # Draw S letter; fallback to default PIL font
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None  # type: ignore[assignment]
    text = "S"
    # Pillow 10+ removed textsize; use textbbox for dimensions
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        # Fallback approximate size if textbbox is unavailable
        w = h = int(size * 0.5)
    draw.text(((size - w) / 2, (size - h) / 2), text, fill=(255, 255, 255, 255), font=font)
    return img


class TrayManager:
    def __init__(self, app: "App") -> None:
        self.app = app
        self._icon = pystray.Icon("Snap OCR", icon=_make_icon(), title="Snap OCR")

        capture_items = [
            pystray.MenuItem("Full", self._wrap(lambda: self.app.set_capture_mode("full")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "full"),
            pystray.MenuItem("Region", self._wrap(lambda: self.app.set_capture_mode("region")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "region"),
        ]
        if sys.platform == "win32":
            capture_items.append(
                pystray.MenuItem("FancyZones", self._wrap(lambda: self.app.set_capture_mode("fancyzones")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "fancyzones")
            )
        elif sys.platform == "darwin":
            capture_items.append(
                pystray.MenuItem("MacsyZones", self._wrap(lambda: self.app.set_capture_mode("macsyzones")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "macsyzones")
            )

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Take Screenshot Now", self._wrap(self.app.take_screenshot_now)),
            pystray.MenuItem(
                "Capture Mode",
                pystray.Menu(*capture_items),
            ),
            pystray.MenuItem("Pick Region…", self._wrap(self.app.pick_region, run_async=False)),
            pystray.MenuItem(
                "Overwrite Mode",
                self._wrap(self.app.toggle_overwrite_mode),
                checked=lambda item: getattr(self.app, "overwrite_mode", False),
            ),
            pystray.MenuItem("Open Images Folder", self._wrap(self.app.open_images_folder)),
            pystray.MenuItem("Open Text Folder", self._wrap(self.app.open_text_folder)),
            pystray.MenuItem("Open Config File", self._wrap(self.app.open_config_file)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reload Config", self._wrap(self.app.reload_config)),
            pystray.MenuItem("View Log File…", self._wrap(self.app.view_log_file)),
            pystray.MenuItem("View Last Error…", self._wrap(self.app.view_last_error)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._wrap(self.app.quit)),
        )

    def _wrap(self, func: Callable[[], None], run_async: bool = True) -> Callable:
        def _inner(icon: pystray.Icon, item: Optional[pystray.MenuItem] = None) -> None:  # type: ignore[type-arg]
            if run_async:
                threading.Thread(target=func, daemon=True).start()
            else:
                func()
        return _inner

    def run(self) -> None:
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()
