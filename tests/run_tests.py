"""Test-Runner: Führt alle Tests aus und zeigt Ergebnis."""

import sys
import os
import unittest

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Logging
from musiai.util.LoggingConfig import setup_logging
import logging
logger = setup_logging(logging.WARNING)  # Nur Fehler in Tests

# QApplication muss vor Tests existieren
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)


def run_all():
    """Entdeckt und führt alle Tests im tests/ Verzeichnis aus."""
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(__file__),
        pattern="test_*.py",
        top_level_dir=os.path.join(os.path.dirname(__file__), ".."),
    )

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    result = run_all()
    sys.exit(0 if result.wasSuccessful() else 1)
