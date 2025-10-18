from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont
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
            if img.size != (size, size):
                img = img.resize((size, size), Image.LANCZOS)
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
        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Take Screenshot Now", self._wrap(self.app.take_screenshot_now)),
            pystray.MenuItem(
                "Capture Mode",
                pystray.Menu(
                    pystray.MenuItem("Full", self._wrap(lambda: self.app.set_capture_mode("full")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "full"),
                    pystray.MenuItem("Region", self._wrap(lambda: self.app.set_capture_mode("region")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "region"),
                    pystray.MenuItem("FancyZones", self._wrap(lambda: self.app.set_capture_mode("fancyzones")), checked=lambda _: getattr(self.app, "capture_mode", "full") == "fancyzones"),
                ),
            ),
            pystray.MenuItem("Pick Region…", self._wrap(self.app.pick_region, run_async=False)),
            pystray.MenuItem(
                "Consecutive Mode",
                self._wrap(self.app.toggle_consecutive_mode),
                checked=lambda item: self.app.consecutive_mode,
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
