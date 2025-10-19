from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def _get_monitor_under_point_with_index(x: int, y: int) -> Optional[Tuple[int, Dict[str, int]]]:
    with mss.mss() as sct:
        monitors = sct.monitors
        if not monitors:
            return None
        if len(monitors) > 1:
            physical = list(enumerate(monitors[1:], start=0))
        else:
            physical = [(0, monitors[0])]
        for idx, mon in physical:
            left = int(mon.get("left", 0))
            top = int(mon.get("top", 0))
            width = int(mon.get("width", 0))
            height = int(mon.get("height", 0))
            if x >= left and y >= top and x < left + width and y < top + height:
                return idx, mon
        return physical[0] if physical else None


def _get_monitor_under_point(x: int, y: int) -> Optional[Dict[str, int]]:
    info = _get_monitor_under_point_with_index(x, y)
    if info is None:
        return None
    return info[1]


def _fz_dir() -> str:
    if sys.platform != "win32":
        raise SnapOcrError(ErrorCode.OTHER, "FancyZones only available on Windows.")
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "PowerToys", "FancyZones")


def _load_json(path: str) -> Optional[Any]:
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


def _macsyzones_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "MeowingCat.MacsyZones"


def _load_macsyzones_layouts(base: Path) -> Dict[str, List[Dict[str, float]]]:
    layouts: Dict[str, List[Dict[str, float]]] = {}
    data = _load_json(str(base / "UserLayouts.json"))
    if isinstance(data, dict):
        for name, zones in data.items():
            if not isinstance(zones, list):
                continue
            parsed: List[Dict[str, float]] = []
            for zone in zones:
                if not isinstance(zone, dict):
                    continue
                try:
                    xp = float(zone.get("xPercentage", zone.get("x", 0.0)) or 0.0)
                    yp = float(zone.get("yPercentage", zone.get("y", 0.0)) or 0.0)
                    wp = float(zone.get("widthPercentage", zone.get("width", 0.0)) or 0.0)
                    hp = float(zone.get("heightPercentage", zone.get("height", 0.0)) or 0.0)
                except (TypeError, ValueError):
                    continue
                parsed.append({"x": xp, "y": yp, "width": wp, "height": hp})
            if parsed:
                layouts[name] = parsed
    return layouts


def _load_macsyzones_screen_layouts(base: Path) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    data = _load_json(str(base / "SpaceLayoutPreferences.json"))
    if isinstance(data, list):
        it = iter(data)
        for meta, layout_name in zip(it, it):
            if not isinstance(meta, dict) or not isinstance(layout_name, str):
                continue
            screen_val = meta.get("screen")
            if isinstance(screen_val, (int, float)):
                mapping[int(screen_val)] = layout_name
    return mapping


def get_macsyzones_region(
    prefer_under_cursor: bool = True,
    zone_index: int = 0,
    layout_name: Optional[str] = None,
) -> Optional[Dict[str, int]]:
    if sys.platform != "darwin":
        raise SnapOcrError(ErrorCode.OTHER, "MacsyZones capture is only available on macOS.")

    cursor_x, cursor_y = _get_cursor_pos()
    monitor_info = _get_monitor_under_point_with_index(cursor_x, cursor_y)
    if not monitor_info:
        return None
    screen_index, monitor = monitor_info

    width = int(monitor.get("width", 0))
    height = int(monitor.get("height", 0))
    if width <= 0 or height <= 0:
        return None

    base = _macsyzones_dir()
    if not base.exists():
        return None

    layouts = _load_macsyzones_layouts(base)
    if not layouts:
        return None

    selected_layout_name: Optional[str] = layout_name
    if not selected_layout_name:
        screen_layouts = _load_macsyzones_screen_layouts(base)
        selected_layout_name = screen_layouts.get(screen_index)

    if not selected_layout_name or selected_layout_name not in layouts:
        if "Default" in layouts:
            selected_layout_name = "Default"
        else:
            selected_layout_name = next(iter(layouts.keys()))

    zones = layouts.get(selected_layout_name)
    if not zones:
        return None

    mon_left = int(monitor.get("left", 0))
    mon_top = int(monitor.get("top", 0))
    scaled: List[Dict[str, int]] = []
    for zone in zones:
        try:
            zx = float(zone.get("x", 0.0))
            zy = float(zone.get("y", 0.0))
            zw = float(zone.get("width", 0.0))
            zh = float(zone.get("height", 0.0))
        except (TypeError, ValueError):
            continue
        zx = max(0.0, min(1.0, zx))
        zy = max(0.0, min(1.0, zy))
        zw = max(0.0, min(1.0, zw))
        zh = max(0.0, min(1.0, zh))
        left = mon_left + int(round(zx * width))
        top = mon_top + int(round(zy * height))
        w_px = max(1, int(round(zw * width)))
        h_px = max(1, int(round(zh * height)))
        scaled.append({"x": left, "y": top, "width": w_px, "height": h_px})

    if not scaled:
        return None

    if prefer_under_cursor:
        for z in scaled:
            if cursor_x >= z["x"] and cursor_y >= z["y"] and cursor_x < z["x"] + z["width"] and cursor_y < z["y"] + z["height"]:
                return {
                    "left": z["x"],
                    "top": z["y"],
                    "width": z["width"],
                    "height": z["height"],
                }

    idx = zone_index if 0 <= zone_index < len(scaled) else (len(scaled) - 1)
    z = scaled[idx]
    return {
        "left": z["x"],
        "top": z["y"],
        "width": z["width"],
        "height": z["height"],
    }
