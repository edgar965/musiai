"""MusiAI - Entry Point."""

import sys
from musiai.util.LoggingConfig import setup_logging

logger = setup_logging()


def main():
    logger.info("MusiAI startet...")

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("MusiAI")
    app.setOrganizationName("MusiAI")

    from musiai.controller.AppController import AppController
    controller = AppController()
    controller.start()

    exit_code = app.exec()
    controller.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
