"""Test-Runner: Führt alle Tests aus und zeigt Ergebnis."""

import sys
import os
import unittest
import ctypes

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Externe Bibliotheks-Warnungen unterdrücken (PortMidi, FluidSynth)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
if sys.platform == "win32":
    # stderr von C-Bibliotheken unterdrücken
    _stderr_fd = os.dup(2)
    _devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull, 2)

# Logging - alle Bibliotheks-Warnungen unterdrücken
from musiai.util.LoggingConfig import setup_logging
import logging
logger = setup_logging(logging.ERROR)  # Nur echte Fehler in Tests
logging.getLogger("musiai.audio").setLevel(logging.CRITICAL)
logging.getLogger("musiai.midi").setLevel(logging.CRITICAL)

# QApplication muss vor Tests existieren
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

# stderr wiederherstellen (Python-Output sichtbar, C-Init-Meldungen weg)
if sys.platform == "win32":
    os.dup2(_stderr_fd, 2)
    os.close(_devnull)
    os.close(_stderr_fd)


def _discover_standard(loader, test_dir, top_dir):
    """Entdeckt Tests in allen Unterordnern außer longrunner/."""
    suite = unittest.TestSuite()
    for entry in sorted(os.listdir(test_dir)):
        sub = os.path.join(test_dir, entry)
        if entry == "longrunner" or entry.startswith("__"):
            continue
        if os.path.isdir(sub):
            suite.addTests(loader.discover(
                sub, pattern="test_*.py", top_level_dir=top_dir))
        elif entry.startswith("test_") and entry.endswith(".py"):
            suite.addTests(loader.discover(
                test_dir, pattern=entry, top_level_dir=top_dir))
    return suite


def run_all(include_longrunner: bool = False):
    """Entdeckt und führt Tests aus.

    Args:
        include_longrunner: Wenn True, werden auch langsame Tests
            aus tests/longrunner/ einbezogen.
    """
    loader = unittest.TestLoader()
    test_dir = os.path.dirname(__file__)
    top_dir = os.path.join(test_dir, "..")

    if include_longrunner:
        suite = loader.discover(
            start_dir=test_dir,
            pattern="test_*.py",
            top_level_dir=top_dir,
        )
    else:
        suite = _discover_standard(loader, test_dir, top_dir)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    include_all = "--all" in sys.argv
    result = run_all(include_longrunner=include_all)
    sys.exit(0 if result.wasSuccessful() else 1)
