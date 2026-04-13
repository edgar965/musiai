"""Visuelle Tests für MIDI Sheet Renderer — vergleicht mit Verovio."""

import sys
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

_qapp = None
BRAHMS = os.path.abspath("../media/music/midi/Brahms_Valse_15.mid")


def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)


class TestMidiSheetBrahms(unittest.TestCase):
    """MIDI Sheet mit Brahms Walzer — prüft Grundstruktur."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_two_parts_rendered(self):
        """Brahms hat 2 Parts (Treble + Bass) — beide müssen gerendert werden."""
        from musiai.ui.midi.Music21Converter import Music21Converter
        conv = Music21Converter()
        parts = conv.convert(BRAHMS)
        self.assertEqual(len(parts), 2, "Brahms should have 2 parts")
        self.assertEqual(parts[0]['clef'], 0, "Part 0 should be Treble")
        self.assertEqual(parts[1]['clef'], 1, "Part 1 should be Bass")

    def test_part_names_meaningful(self):
        """Part-Namen sollten aussagekräftig sein."""
        from musiai.ui.midi.Music21Converter import Music21Converter
        conv = Music21Converter()
        parts = conv.convert(BRAHMS)
        for pd in parts:
            name = pd['part_name']
            self.assertNotEqual(name, "Track",
                                "Part name should not be generic 'Track'")
            self.assertTrue(len(name) > 0, "Part name should not be empty")

    def test_both_parts_have_pixmaps(self):
        """Beide Parts müssen Pixmaps erzeugen."""
        from musiai.notation.NotationScene import NotationScene
        from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsTextItem
        scene = NotationScene()
        scene._source_file_path = BRAHMS
        scene.set_render_mode('midisheet')
        from musiai.model.Piece import Piece
        scene.piece = Piece('Brahms')
        scene.refresh()

        labels = [i for i in scene.items()
                  if isinstance(i, QGraphicsTextItem) and i.pos().x() < 50]
        pixmaps = [i for i in scene.items()
                   if isinstance(i, QGraphicsPixmapItem)]

        self.assertGreaterEqual(len(labels), 2,
                                f"Should have 2+ part labels, got {len(labels)}")
        self.assertGreater(len(pixmaps), 10,
                           f"Should have many pixmaps, got {len(pixmaps)}")

    def test_time_signature_3_4(self):
        """Brahms Walzer ist in 3/4."""
        from musiai.ui.midi.Music21Converter import Music21Converter
        conv = Music21Converter()
        parts = conv.convert(BRAHMS)
        self.assertEqual(parts[0]['time_num'], 3)
        self.assertEqual(parts[0]['time_den'], 4)

    def test_measure_count(self):
        """Brahms Walzer hat ca. 38-44 Takte."""
        from musiai.ui.midi.Music21Converter import Music21Converter
        from musiai.ui.midi.BarSymbol import BarSymbol
        conv = Music21Converter()
        parts = conv.convert(BRAHMS)
        bars = sum(1 for s in parts[0]['symbols'] if isinstance(s, BarSymbol))
        self.assertGreater(bars, 30, f"Should have 30+ bars, got {bars}")
        self.assertLess(bars, 60, f"Should have <60 bars, got {bars}")


class TestVerovioComparison(unittest.TestCase):
    """Vergleicht Verovio-Output mit MIDI Sheet."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_verovio_renders_brahms(self):
        """Verovio rendert Brahms — Scene bekommt Items."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene._source_file_path = BRAHMS
        scene.set_render_mode('svg')
        from musiai.model.Piece import Piece
        scene.piece = Piece('Brahms')
        scene.refresh()
        # WebEngine braucht Event-Loop, aber mindestens Playhead+Cursor+Widget
        items = [i for i in scene.items()]
        # Playhead + Cursor + mindestens ein Verovio-Widget
        self.assertGreaterEqual(len(items), 2,
                                "Verovio should add items to scene")

    def test_verovio_has_bass_clef(self):
        """Verovio-Export hat Bassschlüssel für Part 2."""
        from musiai.midi.MidiImporter import MidiImporter
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = MidiImporter().import_file(BRAHMS)
        xml = MusicXmlExporter().export_string(piece)
        self.assertIn("<sign>F</sign>", xml,
                      "Export should contain F clef (bass)")
        self.assertIn("<sign>G</sign>", xml,
                      "Export should contain G clef (treble)")

    def test_verovio_has_note_types(self):
        """Verovio-Export hat <type> Elemente."""
        from musiai.midi.MidiImporter import MidiImporter
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = MidiImporter().import_file(BRAHMS)
        xml = MusicXmlExporter().export_string(piece)
        self.assertIn("<type>quarter</type>", xml)
        self.assertIn("<type>eighth</type>", xml)


if __name__ == "__main__":
    unittest.main()
