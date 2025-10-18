from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from .paths import get_logs_dir


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("snap_ocr")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    logs_dir = get_logs_dir()
    file_path = os.path.join(logs_dir, "app.log")
    fh = RotatingFileHandler(file_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)

        # Optional console handler (debugging); not required for production
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        ch.setLevel(logging.WARNING)
        logger.addHandler(ch)

    logger.debug("Logging configured at %s", level)
    return logger

