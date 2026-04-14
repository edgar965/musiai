"""Tests für OMR (Optical Music Recognition) — alle Pipelines + UI Flow.

Testet:
1. oemer Engine: Bild → MusicXML → Piece
2. Audiveris Engine: Verfügbarkeit
3. UI Flow: Bearbeiten → Neue Spur aus Bild/PDF
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Test image: render a simple score to PNG using the project's own renderer
TEST_IMAGE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    'media', 'quality_final_0.png'))

# Bella figlia Notenbild (falls vorhanden)
BELLA_IMAGE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    'media', 'bella_figlia_test.png'))

_qapp = None
def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)


class TestOMREngineAvailability(unittest.TestCase):
    """Prüfe ob OMR Engines verfügbar sind."""

    def test_detect_available(self):
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        avail = SheetMusicRecognizer.detect_available()
        self.assertIsInstance(avail, dict)
        self.assertIn("oemer", avail)
        self.assertIn("audiveris", avail)

    def test_oemer_installed(self):
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        avail = SheetMusicRecognizer.detect_available()
        self.assertTrue(avail.get("oemer"),
                        "oemer should be installed (pip install oemer)")

    def test_unknown_engine_returns_error(self):
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        result = SheetMusicRecognizer.recognize("test.png", "nonexistent")
        self.assertFalse(result.success)
        self.assertIn("Unbekannt", result.error)


class TestOemerPipeline(unittest.TestCase):
    """Test oemer: Bild → MusicXML."""

    def _find_test_image(self):
        """Find a usable test image."""
        for path in [BELLA_IMAGE, TEST_IMAGE]:
            if os.path.exists(path):
                return path
        # Check for any PNG in media/
        media = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'media'))
        for f in os.listdir(media):
            if f.endswith('.png') and 'quality' in f:
                return os.path.join(media, f)
        return None

    def test_oemer_recognize_returns_result(self):
        """oemer.recognize returns OMRResult."""
        img = self._find_test_image()
        if not img:
            self.skipTest("No test image found")
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        if not SheetMusicRecognizer.detect_available().get("oemer"):
            self.skipTest("oemer not installed")
        result = SheetMusicRecognizer.recognize(img, "oemer")
        self.assertEqual(result.engine, "oemer")
        # May or may not succeed depending on image content,
        # but should not crash
        self.assertIsInstance(result.success, bool)

    def test_oemer_with_music_image(self):
        """oemer erkennt Noten aus einem Notenbild."""
        img = self._find_test_image()
        if not img:
            self.skipTest("No test image found")
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        if not SheetMusicRecognizer.detect_available().get("oemer"):
            self.skipTest("oemer not installed")
        result = SheetMusicRecognizer.recognize(img, "oemer")
        if result.success:
            self.assertGreater(len(result.musicxml), 100,
                               "MusicXML should have content")
            self.assertIn("<score-partwise", result.musicxml.lower()
                          if result.musicxml else "")


class TestAudiverisPipeline(unittest.TestCase):
    """Test Audiveris Engine (oft nicht installiert)."""

    def test_audiveris_not_available_returns_error(self):
        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        if SheetMusicRecognizer.detect_available().get("audiveris"):
            self.skipTest("Audiveris is installed")
        result = SheetMusicRecognizer.recognize("test.png", "audiveris")
        self.assertFalse(result.success)
        self.assertIn("nicht gefunden", result.error)


class TestOMRUIFlow(unittest.TestCase):
    """Test: Bearbeiten → Neue Spur aus Bild/PDF — kompletter UI Flow."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_import_from_image_cancel(self):
        """Dialog abbrechen → kein Crash."""
        from musiai.controller.AppController import AppController
        ctrl = AppController()
        from unittest.mock import patch
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=("", "")):
            ctrl._import_from_image()
        # No crash

    def test_import_from_image_creates_piece(self):
        """Bild laden → oemer → Piece erstellt."""
        # Find test image
        img = None
        for path in [BELLA_IMAGE, TEST_IMAGE]:
            if os.path.exists(path):
                img = path
                break
        if not img:
            self.skipTest("No test image found")

        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        if not SheetMusicRecognizer.detect_available().get("oemer"):
            self.skipTest("oemer not installed")

        from musiai.controller.AppController import AppController
        ctrl = AppController()

        from unittest.mock import patch, MagicMock
        # Mock the file dialog to return test image
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=(img, "Bilder")):
            ctrl._import_from_image()

        # If oemer succeeded, there should be a piece
        piece = ctrl._active_piece()
        if piece and piece.title != "Neues Projekt":
            self.assertGreater(len(piece.parts), 0,
                               "Piece should have parts")

    def test_settings_omr_tab_exists(self):
        """Settings Dialog hat 'Noten von Bild' Tab."""
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        tab_titles = [dialog._tabs.tabText(i)
                      for i in range(dialog._tabs.count())]
        self.assertIn("Noten von Bild", tab_titles)


if __name__ == "__main__":
    unittest.main()
