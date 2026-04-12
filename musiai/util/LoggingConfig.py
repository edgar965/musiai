"""Logging-Konfiguration für MusiAI."""

import logging
import sys
from pathlib import Path

LOG_DIR = Path("A:/MusiAI/logs")
LOG_FILE = LOG_DIR / "musiai.log"


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Konfiguriert Logging für Console + Datei."""
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger("musiai")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    # Datei-Handler (alles loggen)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    # Console-Handler (nur INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(levelname)-8s] %(name)-20s | %(message)s"
    )
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
