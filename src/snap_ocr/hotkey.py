from __future__ import annotations

import threading
from typing import Callable, Optional

from pynput import keyboard


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

