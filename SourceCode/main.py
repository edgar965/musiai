"""MusiAI - Entry Point."""

import sys
import logging
from musiai.util.LoggingConfig import setup_logging

logger = setup_logging()


def _exception_hook(exc_type, exc_value, exc_tb):
    """Alle uncaught Exceptions ins Log schreiben."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_tb))


sys.excepthook = _exception_hook


def main():
    logger.info("MusiAI startet...")

    # Apply log level from settings
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("MusiAI")
    app.setOrganizationName("MusiAI")

    from PySide6.QtCore import QSettings
    from musiai.util.LoggingConfig import apply_log_level
    settings = QSettings("MusiAI", "MusiAI")
    level = int(settings.value("logging/level", 4))
    apply_log_level(level)
    logger.info(f"Log-Level aus Settings: {level}")

    from musiai.controller.AppController import AppController
    controller = AppController()

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
