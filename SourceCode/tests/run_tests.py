"""Test-Runner: Führt Tests aus mit 3 Geschwindigkeits-Stufen.

Kategorien:
  standard/  — Schnelle Tests (<3s), laufen immer
  longer/    — Mittlere Tests (3-10s), mit --longer oder --all
  longrunner/ — Langsame Tests (>10s), nur mit --all
"""

import sys
import os
import unittest

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Externe Bibliotheks-Warnungen unterdrücken (PortMidi, FluidSynth)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
if sys.platform == "win32":
    _stderr_fd = os.dup(2)
    _devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull, 2)

# Logging
from musiai.util.LoggingConfig import setup_logging
import logging
logger = setup_logging(logging.ERROR)
logging.getLogger("musiai.audio").setLevel(logging.CRITICAL)
logging.getLogger("musiai.midi").setLevel(logging.CRITICAL)

# QApplication muss vor Tests existieren
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

# stderr wiederherstellen
if sys.platform == "win32":
    os.dup2(_stderr_fd, 2)
    os.close(_devnull)
    os.close(_stderr_fd)

EXCLUDE_DIRS = {"longrunner", "longer"}


def _discover_filtered(loader, test_dir, top_dir, exclude: set):
    """Tests entdecken, bestimmte Ordner ausschließen."""
    suite = unittest.TestSuite()
    for entry in sorted(os.listdir(test_dir)):
        sub = os.path.join(test_dir, entry)
        if entry in exclude or entry.startswith("__"):
            continue
        if os.path.isdir(sub):
            suite.addTests(loader.discover(
                sub, pattern="test_*.py", top_level_dir=top_dir))
        elif entry.startswith("test_") and entry.endswith(".py"):
            suite.addTests(loader.discover(
                test_dir, pattern=entry, top_level_dir=top_dir))
    return suite


def run_all(include_longer: bool = False, include_longrunner: bool = False):
    """Tests ausführen.

    Standard:       nur standard/ (schnell)
    --longer:       standard/ + longer/ (mittel)
    --all:          standard/ + longer/ + longrunner/ (alles)
    """
    loader = unittest.TestLoader()
    test_dir = os.path.dirname(__file__)
    top_dir = os.path.join(test_dir, "..")

    if include_longrunner:
        # Alles
        suite = loader.discover(test_dir, pattern="test_*.py",
                                top_level_dir=top_dir)
    elif include_longer:
        # Standard + longer
        exclude = {"longrunner"}
        suite = _discover_filtered(loader, test_dir, top_dir, exclude)
    else:
        # Nur standard
        suite = _discover_filtered(loader, test_dir, top_dir, EXCLUDE_DIRS)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    args = set(sys.argv[1:])
    result = run_all(
        include_longer="--longer" in args or "--all" in args,
        include_longrunner="--all" in args,
    )
    sys.exit(0 if result.wasSuccessful() else 1)
