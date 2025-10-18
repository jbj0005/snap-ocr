from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

from pynput import keyboard

if sys.platform == "darwin":
    try:
        from pynput._util import AbstractListener
        import pynput._util.darwin as _darwin_util
    except Exception:
        _darwin_util = None
    else:
        if _darwin_util and not getattr(_darwin_util, "_snap_ocr_thread_handle_patch", False):

            @AbstractListener._emitter
            def _patched_handler(self, proxy, event_type, event, refcon):
                type(self)._handle(self, proxy, event_type, event, refcon)
                if self._intercept is not None:
                    return self._intercept(event_type, event)
                if self.suppress:
                    return None

            _darwin_util.ListenerMixin._handler = _patched_handler
            _darwin_util._snap_ocr_thread_handle_patch = True


class HotkeyManager:
    def __init__(self, hotkey_str: str, on_activate: Callable[[], None], on_error: Callable[[Exception], None]) -> None:
        self.hotkey_str = hotkey_str
        self.on_activate = on_activate
        self.on_error = on_error
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            self._start_locked()

    def _start_locked(self) -> None:
        try:
            self._listener = keyboard.GlobalHotKeys({self.hotkey_str: self.on_activate})
            self._listener.start()
        except Exception as e:
            self.on_error(e)

    def stop(self) -> None:
        with self._lock:
            if self._listener:
                self._listener.stop()
                self._listener = None

    def update_hotkey(self, new_hotkey: str) -> None:
        with self._lock:
            if self.hotkey_str == new_hotkey and self._listener is not None:
                return
            # Restart listener with new hotkey
            if self._listener:
                self._listener.stop()
                self._listener = None
            self.hotkey_str = new_hotkey
            self._start_locked()

