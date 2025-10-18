from __future__ import annotations

import threading
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont
import pystray


def _make_icon(size: int = 32) -> Image.Image:
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
