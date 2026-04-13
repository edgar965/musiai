"""MusiAI - Entry Point."""

import sys
import os
import signal
import threading
import atexit
from musiai.util.LoggingConfig import setup_logging

logger = setup_logging()

# Sofort-Exit bei Signalen
signal.signal(signal.SIGINT, lambda *_: os._exit(0))
signal.signal(signal.SIGTERM, lambda *_: os._exit(0))

# atexit: Prozess killen wenn Python Cleanup beginnt
atexit.register(lambda: os._exit(0))


def _watchdog():
    """Hintergrund-Thread: beendet Prozess wenn Hauptthread stirbt."""
    main_thread = threading.main_thread()
    main_thread.join()  # Wartet bis Hauptthread beendet
    os._exit(0)


def main():
    logger.info("MusiAI startet...")

    # Watchdog starten (daemon=True reicht nicht bei pygame-Threads)
    wd = threading.Thread(target=_watchdog, daemon=True)
    wd.start()

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("MusiAI")
    app.setOrganizationName("MusiAI")

    from musiai.controller.AppController import AppController
    controller = AppController()

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()

    app.exec()
    os._exit(0)


if __name__ == "__main__":
    main()
