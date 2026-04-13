"""Logging-Konfiguration für MusiAI."""

import logging
import sys
from pathlib import Path

LOG_DIR = Path("A:/MusiAI/logs")
LOG_FILE = LOG_DIR / "musiai.log"
EXCEPTION_LOG_FILE = LOG_DIR / "musiai_exceptions.log"

# Map settings slider (1-10) to Python logging levels
LEVEL_MAP = {
    1: logging.CRITICAL,  # 50
    2: logging.ERROR,     # 40
    3: logging.WARNING,   # 30
    4: logging.INFO,      # 20
    5: logging.DEBUG,     # 10
    6: logging.DEBUG,
    7: logging.DEBUG,
    8: logging.DEBUG,
    9: logging.DEBUG,
    10: logging.DEBUG,
}

LEVEL_NAMES = {
    1: "CRITICAL", 2: "ERROR", 3: "WARNING", 4: "INFO",
    5: "DEBUG", 6: "DEBUG+", 7: "DEBUG++", 8: "DEBUG+++",
    9: "TRACE", 10: "TRACE+",
}


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

    # Exception-Handler (nur ERROR + CRITICAL)
    exception_handler = logging.FileHandler(
        EXCEPTION_LOG_FILE, encoding="utf-8"
    )
    exception_handler.setLevel(logging.ERROR)
    exception_format = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)-30s | %(message)s\n"
        "%(pathname)s:%(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    exception_handler.setFormatter(exception_format)

    # Console-Handler (nur INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(levelname)-8s] %(name)-20s | %(message)s"
    )
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(exception_handler)
    logger.addHandler(console_handler)

    return logger


def apply_log_level(slider_value: int) -> None:
    """Apply log level from settings slider value (1-10)."""
    py_level = LEVEL_MAP.get(slider_value, logging.INFO)
    logging.getLogger("musiai").setLevel(py_level)
