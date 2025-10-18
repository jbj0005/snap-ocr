from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from pynput import mouse
import mss

from .errors import ErrorCode, SnapOcrError


def pick_region_overlay() -> Optional[Dict[str, int]]:
    try:
        import tkinter as tk
    except Exception as e:
        raise SnapOcrError(ErrorCode.OTHER, f"Region picker requires Tkinter: {e}", e)

    region: Dict[str, int] = {}
    start = {"x": 0, "y": 0}
    rect_id = {"id": None}

    root = tk.Tk()
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.3)
    except Exception:
        pass
    try:
        root.attributes("-fullscreen", True)
    except Exception:
        root.state('zoomed')
    root.configure(bg="black")

    canvas = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    def on_press(event):
        start["x"], start["y"] = event.x, event.y
        if rect_id["id"] is not None:
            canvas.delete(rect_id["id"])
        rect_id["id"] = canvas.create_rectangle(start["x"], start["y"], start["x"], start["y"], outline="red", width=2)

    def on_drag(event):
        if rect_id["id"] is not None:
            canvas.coords(rect_id["id"], start["x"], start["y"], event.x, event.y)

    def on_release(event):
        x1, y1 = start["x"], start["y"]
        x2, y2 = event.x, event.y
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        region.update({"left": int(left), "top": int(top), "width": int(width), "height": int(height)})
        root.quit()

    def on_escape(event):
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass
    return region if region else None


def _get_cursor_pos() -> Tuple[int, int]:
    try:
        ctrl = mouse.Controller()
        x, y = ctrl.position  # type: ignore[assignment]
        return int(x), int(y)
    except Exception:
        return (0, 0)


def _get_monitor_under_point(x: int, y: int) -> Optional[Dict[str, int]]:
    with mss.mss() as sct:
        for mon in sct.monitors[1:]:  # skip virtual at index 0
            if x >= mon["left"] and y >= mon["top"] and x < mon["left"] + mon["width"] and y < mon["top"] + mon["height"]:
                return mon
        return sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]


def _fz_dir() -> str:
    if sys.platform != "win32":
        raise SnapOcrError(ErrorCode.OTHER, "FancyZones only available on Windows.")
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "PowerToys", "FancyZones")


def _load_json(path: str) -> Optional[Dict]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _extract_canvas_info(dev: Dict) -> Optional[Tuple[List[Dict[str, int]], int, int]]:
    """Return (zones, ref_width, ref_height) for a Canvas layout device entry.
    Supports newer schema where zones are under appliedLayout.info.
    Fallbacks to older keys when present.
    """
    # Newer schema
    applied = dev.get("appliedLayout") or {}
    if isinstance(applied, dict) and str(applied.get("type", "")).lower() == "canvas":
        info = applied.get("info") or {}
        zones = info.get("zones") or []
        if isinstance(zones, list) and zones:
            refw = int(info.get("ref-width", info.get("refWidth", 0)) or 0)
            refh = int(info.get("ref-height", info.get("refHeight", 0)) or 0)
            out: List[Dict[str, int]] = []
            for z in zones:
                if all(k in z for k in ("width", "height")):
                    x = int(z.get("x", z.get("X", 0)))
                    y = int(z.get("y", z.get("Y", 0)))
                    out.append({"x": x, "y": y, "width": int(z["width"]), "height": int(z["height"])})
            if out:
                return (out, refw, refh)
    # Older/alternate schema used earlier
    canvas = dev.get("canvas-layout") or {}
    zones = canvas.get("zones") if isinstance(canvas, dict) else None
    if isinstance(zones, list) and zones:
        out2: List[Dict[str, int]] = []
        for z in zones:
            if all(k in z for k in ("width", "height")):
                x = int(z.get("x", z.get("X", 0)))
                y = int(z.get("y", z.get("Y", 0)))
                out2.append({"x": x, "y": y, "width": int(z["width"]), "height": int(z["height"])})
        if out2:
            return (out2, 0, 0)
    if "zones" in dev and isinstance(dev["zones"], list) and dev["zones"]:
        out3 = [{"x": int(z.get("x", 0)), "y": int(z.get("y", 0)), "width": int(z["width"]), "height": int(z["height"])} for z in dev["zones"]]
        return (out3, 0, 0)
    return None


def _get_zones_info_for_any_canvas() -> Optional[Tuple[List[Dict[str, int]], int, int]]:
    base = _fz_dir()
    # First attempt: legacy zones-settings.json with appliedLayout
    zs_path = os.path.join(base, "zones-settings.json")
    data_zs = _load_json(zs_path)
    if isinstance(data_zs, dict):
        devices = data_zs.get("devices") or []
        for dev in devices:
            info = _extract_canvas_info(dev)
            if info:
                return info
    # Newer schema: applied-layouts.json + custom-layouts.json
    app_path = os.path.join(base, "applied-layouts.json")
    cust_path = os.path.join(base, "custom-layouts.json")
    data_app = _load_json(app_path)
    data_cust = _load_json(cust_path)
    if not (isinstance(data_app, dict) and isinstance(data_cust, dict)):
        return None
    applied = data_app.get("applied-layouts") or []
    customs = data_cust.get("custom-layouts") or []
    # Map uuid -> layout entry (only canvas)
    uuid_to_canvas: Dict[str, Dict] = {}
    for layout in customs:
        if str(layout.get("type", "")).lower() == "canvas":
            uuid = layout.get("uuid")
            if uuid:
                uuid_to_canvas[uuid] = layout
    # Find an applied entry that references a canvas layout
    for ap in applied:
        ap_layout = ap.get("applied-layout") or {}
        if str(ap_layout.get("type", "")).lower() == "custom":
            uuid = ap_layout.get("uuid")
            if uuid and uuid in uuid_to_canvas:
                info = uuid_to_canvas[uuid].get("info") or {}
                zones = info.get("zones") or []
                if isinstance(zones, list) and zones:
                    refw = int(info.get("ref-width", info.get("refWidth", 0)) or 0)
                    refh = int(info.get("ref-height", info.get("refHeight", 0)) or 0)
                    out: List[Dict[str, int]] = []
                    for z in zones:
                        if all(k in z for k in ("width", "height")):
                            x = int(z.get("x", z.get("X", 0)))
                            y = int(z.get("y", z.get("Y", 0)))
                            out.append({"x": x, "y": y, "width": int(z["width"]), "height": int(z["height"])})
                    if out:
                        return (out, refw, refh)
    return None


def get_fancyzones_region(prefer_under_cursor: bool = True, zone_index: int = 0) -> Optional[Dict[str, int]]:
    x, y = _get_cursor_pos()
    mon = _get_monitor_under_point(x, y)
    if not mon:
        return None
    info = _get_zones_info_for_any_canvas()
    if not info:
        return None
    zones, refw, refh = info
    # Scale zones if ref dims present
    scale_x = mon["width"] / refw if refw else 1.0
    scale_y = mon["height"] / refh if refh else 1.0
    scaled: List[Dict[str, int]] = []
    for z in zones:
        sx = int(round(z["x"] * scale_x))
        sy = int(round(z["y"] * scale_y))
        sw = int(round(z["width"] * scale_x))
        sh = int(round(z["height"] * scale_y))
        scaled.append({"x": sx, "y": sy, "width": sw, "height": sh})
    if not scaled:
        return None
    if prefer_under_cursor:
        rel_x, rel_y = x - mon["left"], y - mon["top"]
        for z in scaled:
            if rel_x >= z["x"] and rel_y >= z["y"] and rel_x < z["x"] + z["width"] and rel_y < z["y"] + z["height"]:
                return {
                    "left": mon["left"] + z["x"],
                    "top": mon["top"] + z["y"],
                    "width": z["width"],
                    "height": z["height"],
                }
    idx = zone_index if 0 <= zone_index < len(scaled) else (len(scaled) - 1)
    z = scaled[idx]
    return {
        "left": mon["left"] + z["x"],
        "top": mon["top"] + z["y"],
        "width": z["width"],
        "height": z["height"],
    }
