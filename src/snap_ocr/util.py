from __future__ import annotations

import os
import time


def build_timestamped_name() -> str:
    # YYYYMMDD_HHMMSS
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def atomic_write_bytes(path: str, data: bytes) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding=encoding, newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

