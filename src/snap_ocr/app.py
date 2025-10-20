from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .config import Config, ConfigValidationError, load_or_create_config, save_config_if_first_run
from .errors import ErrorCode, SnapOcrError
from .hotkey import HotkeyManager
from .logging_conf import configure_logging
from .ocr import perform_ocr, build_tesseract_missing_message, build_ocr_failed_message
from .paths import (
    ensure_dir,
    get_log_file_path,
    get_config_path,
    open_in_file_manager,
    open_in_text_editor,
    get_logs_dir,
)
from .screenshot import capture_full_screenshot, capture_region
from .tray import TrayManager
from .util import atomic_write_bytes, atomic_write_text, build_timestamped_name
from .region_capture import pick_region_overlay


@dataclass
class Job:
    reason: str  # 'hotkey' or 'tray'
    requested_at: float


class App:
    def __init__(self) -> None:
        # Config and logging
        self.config: Config = load_or_create_config()
        save_config_if_first_run(self.config)  # Ensure default config exists on first run

        self.logger = configure_logging(self.config.log_level)
        self.logger.info("Starting Snap OCR")

        # State
        self.last_trigger_ts: float = 0.0
        self.last_error_message: Optional[str] = None
        self._stopping = threading.Event()
        self.overwrite_mode = self.config.overwrite_mode
        self.consecutive_mode = self.overwrite_mode  # legacy alias
        setattr(self.config, "consecutive_mode", self.overwrite_mode)  # legacy attribute for compatibility
        self.last_saved_paths: Optional[Tuple[str, str]] = None
        self.capture_mode = getattr(self.config, "capture_mode", "full")
        self.worker_queue: queue.Queue[Optional[Job]] = queue.Queue()

        # Components
        self.hotkey = HotkeyManager(
            hotkey_str=self.config.hotkey,
            on_activate=self.on_hotkey_triggered,
            on_error=self._on_hotkey_error,
        )
        self.tray = TrayManager(app=self)

        # Worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, name="snap-ocr-worker", daemon=True)

    # Public API used by tray/hotkey
    def on_hotkey_triggered(self) -> None:
        if self._is_debounced():
            return
        self._enqueue_job("hotkey")

    def take_screenshot_now(self) -> None:
        if self._is_debounced():
            return
        self._enqueue_job("tray")

    def toggle_overwrite_mode(self) -> None:
        self.overwrite_mode = not self.overwrite_mode
        self.consecutive_mode = self.overwrite_mode  # legacy alias
        self.config.overwrite_mode = self.overwrite_mode
        setattr(self.config, "consecutive_mode", self.overwrite_mode)  # keep legacy attribute updated
        self.logger.info("Overwrite Mode set to %s", self.overwrite_mode)

    def toggle_consecutive_mode(self) -> None:  # pragma: no cover - legacy alias
        self.toggle_overwrite_mode()

    def set_capture_mode(self, mode: str) -> None:
        if mode in ("full", "region", "fancyzones", "macsyzones"):
            self.capture_mode = mode
            self.logger.info("Capture mode set to %s", mode)

    def pick_region(self) -> None:
        try:
            region = pick_region_overlay()
            if region:
                # Store in config runtime; persisted if user saves config manually
                self.config.region = region  # type: ignore[attr-defined]
                self.logger.info("Region selected: %s", region)
        except Exception as e:
            self._record_error(SnapOcrError(ErrorCode.OTHER, f"Failed to pick region: {e}", e))

    def open_images_folder(self) -> None:
        ensure_dir(self.config.save_dir_images)
        open_in_file_manager(self.config.save_dir_images)

    def open_text_folder(self) -> None:
        ensure_dir(self.config.save_dir_text)
        open_in_file_manager(self.config.save_dir_text)

    def view_log_file(self) -> None:
        log_path = get_log_file_path()
        if log_path:
            open_in_file_manager(log_path)
        else:
            # Open logs directory if file not present yet
            open_in_file_manager(get_logs_dir())

    def view_last_error(self) -> None:
        # Avoid OS alerts; open log file/directory for user to inspect
        self.view_log_file()

    def open_config_file(self) -> None:
        path = get_config_path()
        open_in_text_editor(path)

    def reload_config(self) -> None:
        try:
            new_cfg = load_or_create_config()
            # Apply updates
            self._apply_config(new_cfg)
            self._notify("Snap OCR", "Configuration reloaded.")
        except ConfigValidationError as e:
            msg = f"{e}\nFix the configuration at {get_config_path()} and try again."
            self._record_error(
                SnapOcrError(ErrorCode.CONFIG_INVALID, msg, e)
            )
        except Exception as e:
            self._record_error(
                SnapOcrError(ErrorCode.CONFIG_INVALID, f"Failed to reload config: {e}", e)
            )

    def quit(self) -> None:
        self.logger.info("Shutting down Snap OCR")
        try:
            self.hotkey.stop()
        except Exception:
            pass
        self._stopping.set()
        self.worker_queue.put(None)
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass

    # Lifecycle
    def run(self) -> None:
        self.worker_thread.start()
        self.hotkey.start()
        self.tray.run()  # blocking until quit

        # Join worker on exit
        self.worker_thread.join(timeout=2)

    # Internal
    def _apply_config(self, new_cfg: Config) -> None:
        # Update logging level
        if new_cfg.log_level != self.config.log_level:
            logging.getLogger("snap_ocr").setLevel(new_cfg.log_level)  # type: ignore[arg-type]

        # Apply directories (ensure exist)
        for d in (new_cfg.save_dir_images, new_cfg.save_dir_text):
            ensure_dir(d)

        # Update hotkey mapping if changed
        if new_cfg.hotkey != self.config.hotkey:
            self.hotkey.update_hotkey(new_cfg.hotkey)

        # Keep current runtime overwrite mode; update default based on new config's flag
        self.config = new_cfg
        self.overwrite_mode = self.config.overwrite_mode
        self.consecutive_mode = self.overwrite_mode
        setattr(self.config, "consecutive_mode", self.overwrite_mode)
        self.last_saved_paths = None

    def _enqueue_job(self, reason: str) -> None:
        self.last_trigger_ts = time.monotonic()
        self.worker_queue.put(Job(reason=reason, requested_at=time.monotonic()))

    def _is_debounced(self) -> bool:
        now = time.monotonic()
        if (now - self.last_trigger_ts) * 1000.0 < self.config.debounce_ms:
            self.logger.debug("Trigger ignored due to debounce")
            return True
        return False

    def _worker_loop(self) -> None:
        while not self._stopping.is_set():
            job = self.worker_queue.get()
            if job is None:
                break
            try:
                self._process_job(job)
            except Exception as e:
                # Unhandled errors get logged and surfaced
                self._record_error(
                    SnapOcrError(ErrorCode.OTHER, f"Unexpected error: {e}", e)
                )

    def _process_job(self, job: Job) -> Optional[Tuple[str, str]]:
        logger = self.logger
        cfg = self.config

        # Ensure output dirs
        ensure_dir(cfg.save_dir_images)
        ensure_dir(cfg.save_dir_text)

        # Resolve capture
        mode = getattr(self, "capture_mode", "full")
        # Capture
        try:
            if mode == "full":
                img = capture_full_screenshot()
            elif mode == "region":
                r = getattr(self.config, "region", {"left": 100, "top": 100, "width": 1280, "height": 720})
                img = capture_region(int(r["left"]), int(r["top"]), int(r["width"]), int(r["height"]))
            elif mode == "fancyzones":
                # Defer import to avoid Windows-only dependency at import time
                from .region_capture import get_fancyzones_region
                region = get_fancyzones_region(
                    prefer_under_cursor=getattr(self.config, "fancyzones_prefer_under_cursor", True),
                    zone_index=getattr(self.config, "fancyzones_zone_index", 0),
                )
                if not region:
                    raise SnapOcrError(ErrorCode.CAPTURE_FAILED, "No FancyZones region available (cursor not in zone?)")
                img = capture_region(region["left"], region["top"], region["width"], region["height"])
            elif mode == "macsyzones":
                from .region_capture import get_macsyzones_region

                region = get_macsyzones_region(
                    prefer_under_cursor=getattr(self.config, "macsyzones_prefer_under_cursor", True),
                    zone_index=getattr(self.config, "macsyzones_zone_index", 0),
                    layout_name=getattr(self.config, "macsyzones_layout_name", None),
                )
                if not region:
                    raise SnapOcrError(
                        ErrorCode.CAPTURE_FAILED,
                        "No MacsyZones region available. Ensure MacsyZones is installed and a layout is assigned to this display.",
                    )
                logger.debug(
                    "MacsyZones resolved region: left=%s top=%s width=%s height=%s (layout=%s prefer=%s index=%s)",
                    region.get("left"),
                    region.get("top"),
                    region.get("width"),
                    region.get("height"),
                    getattr(self.config, "macsyzones_layout_name", None),
                    getattr(self.config, "macsyzones_prefer_under_cursor", True),
                    getattr(self.config, "macsyzones_zone_index", 0),
                )
                img = capture_region(region["left"], region["top"], region["width"], region["height"])
                logger.debug("Captured region image size: %s×%s", *img.size)
            else:
                img = capture_full_screenshot()
        except SnapOcrError as se:
            self._record_error(se)
            return
        except Exception as e:
            # Likely permissions on macOS or unknown capture failure
            msg = self._mac_screenshot_help() if sys.platform == "darwin" else "Screen capture failed."
            self._record_error(SnapOcrError(ErrorCode.CAPTURE_FAILED, f"{msg} Details: {e}", e))
            return

        # File naming
        pattern = getattr(cfg, "filename_pattern", "{base}_{timestamp}") or "{base}_{timestamp}"
        timestamp_token = build_timestamped_name()
        context = {
            "base": cfg.base_filename,
            "timestamp": timestamp_token,
        }
        try:
            stem_raw = pattern.format(**context)
        except KeyError as exc:
            self._record_error(
                SnapOcrError(
                    ErrorCode.CONFIG_INVALID,
                    f"filename_pattern references unknown placeholder: {exc}",
                    exc,
                )
            )
            return
        except Exception as exc:
            self._record_error(
                SnapOcrError(ErrorCode.CONFIG_INVALID, f"Invalid filename_pattern: {exc}", exc)
            )
            return

        stem = stem_raw.strip() or f"{cfg.base_filename}_{timestamp_token}"

        img_path = os.path.join(cfg.save_dir_images, f"{stem}.png")
        txt_path = os.path.join(cfg.save_dir_text, f"{stem}.txt")

        self._clear_previous_outputs_if_needed()

        # Save image atomically
        try:
            # Always save as PNG for consistency (config.image_format included for extensibility)
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format=cfg.image_format)
            atomic_write_bytes(img_path, buf.getvalue())
        except PermissionError as e:
            self._record_error(
                SnapOcrError(ErrorCode.SAVE_PERMISSION, f"Permission denied writing image: {img_path}", e)
            )
            return
        except Exception as e:
            self._record_error(
                SnapOcrError(ErrorCode.OTHER, f"Failed to save image: {e}", e)
            )
            return

        # OCR
        try:
            text = perform_ocr(img, cfg.ocr_lang, cfg.tesseract_cmd)
        except SnapOcrError as se:
            self._record_error(se)
            return
        except Exception as e:
            self._record_error(
                SnapOcrError(ErrorCode.OCR_FAILED, build_ocr_failed_message(e), e)
            )
            return

        # Save text atomically
        try:
            atomic_write_text(txt_path, text, encoding="utf-8")
        except PermissionError as e:
            self._record_error(
                SnapOcrError(ErrorCode.SAVE_PERMISSION, f"Permission denied writing text: {txt_path}", e)
            )
            return
        except Exception as e:
            self._record_error(
                SnapOcrError(ErrorCode.OTHER, f"Failed to save text: {e}", e)
            )
            return

        # Success
        logger.info("Saved: %s and %s", img_path, txt_path)
        if self.config.notify_on_success:
            self._notify("Snap OCR", f"Saved screenshot + OCR:\n{img_path}\n{txt_path}")

        self.last_saved_paths = (img_path, txt_path)

        return img_path, txt_path

    def _record_error(self, err: SnapOcrError) -> None:
        # Human-readable, actionable messages
        msg = self._format_error_message(err)
        self.last_error_message = msg
        self.logger.error(msg)
        self._notify("Snap OCR Error", msg)

    def _clear_previous_outputs_if_needed(self) -> None:
        if not self.overwrite_mode:
            return
        last = self.last_saved_paths
        if not last:
            return
        for path in last:
            if not path:
                continue
            try:
                if os.path.exists(path):
                    os.remove(path)
                    self.logger.debug("Removed previous output: %s", path)
            except Exception as exc:
                self.logger.warning("Failed to remove previous output %s: %s", path, exc)
        self.last_saved_paths = None

    def _notify(self, title: str, message: str) -> None:
        # All OS notifications are disabled to keep the tool distraction-free.
        return

    def _format_error_message(self, err: SnapOcrError) -> str:
        if err.code == ErrorCode.MISSING_TESSERACT:
            return build_tesseract_missing_message(self.config.tesseract_cmd)
        if err.code == ErrorCode.SCREENSHOT_PERMISSION:
            return self._mac_screenshot_help()
        if err.code == ErrorCode.SAVE_PERMISSION:
            return f"{err}.\nFix: Choose a writable directory in config or adjust permissions; run once as admin if needed."
        if err.code == ErrorCode.HOTKEY_REGISTER:
            return f"Hotkey registration issue. If another app uses {self.config.hotkey}, change 'hotkey' in config.yaml and Reload Config."
        if err.code == ErrorCode.CONFIG_INVALID:
            return f"{err}. Fix: validate YAML formatting and keys."
        if err.code == ErrorCode.OCR_FAILED:
            return build_ocr_failed_message(err.cause or err)
        if err.code == ErrorCode.CAPTURE_FAILED:
            return str(err)
        return f"Unexpected error: {err}"

    def _on_hotkey_error(self, exc: Exception) -> None:
        self._record_error(SnapOcrError(ErrorCode.HOTKEY_REGISTER, f"Hotkey error: {exc}", exc))

    def _mac_screenshot_help(self) -> str:
        return (
            "Screen capture returned black or failed. On macOS, grant permission:\n"
            "System Settings → Privacy & Security → Screen Recording → enable for Terminal/Python.\n"
            "Also check: Accessibility and Input Monitoring (for hotkeys). Then quit and relaunch."
        )
