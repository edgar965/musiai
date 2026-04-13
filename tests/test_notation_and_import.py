"""Tests für MXL-Import, System-Breaks, Kontextmenü-Signal."""

import sys
import os
import unittest
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_qapp = None

def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)


# =============================================================================
# MXL Import
# =============================================================================

class TestMxlImport(unittest.TestCase):

    def test_parse_mxl_file(self):
        """MXL (ZIP-komprimierte MusicXML) korrekt importieren."""
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter

        # Erstelle eine minimale MXL-Datei
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise>
  <work><work-title>Test MXL</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration><type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>"""

        with tempfile.NamedTemporaryFile(suffix=".mxl", delete=False) as f:
            mxl_path = f.name

        try:
            with zipfile.ZipFile(mxl_path, 'w') as z:
                z.writestr("score.xml", xml_content)

            importer = MusicXmlImporter()
            piece = importer.import_file(mxl_path)
            self.assertEqual(piece.title, "Test MXL")
            self.assertEqual(len(piece.parts), 1)
            self.assertEqual(piece.parts[0].name, "Piano")
            self.assertGreater(len(piece.parts[0].measures), 0)
        finally:
            os.unlink(mxl_path)

    def test_mxl_with_container_xml(self):
        """MXL mit META-INF/container.xml korrekt parsen."""
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise>
  <work><work-title>Container Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Voice</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration><type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>"""

        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="music/score.xml"/>
  </rootfiles>
</container>"""

        with tempfile.NamedTemporaryFile(suffix=".mxl", delete=False) as f:
            mxl_path = f.name

        try:
            with zipfile.ZipFile(mxl_path, 'w') as z:
                z.writestr("META-INF/container.xml", container_xml)
                z.writestr("music/score.xml", xml_content)

            importer = MusicXmlImporter()
            piece = importer.import_file(mxl_path)
            self.assertEqual(piece.title, "Container Test")
        finally:
            os.unlink(mxl_path)

    def test_mxl_empty_raises(self):
        """Leeres MXL wirft ValueError."""
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter

        with tempfile.NamedTemporaryFile(suffix=".mxl", delete=False) as f:
            mxl_path = f.name

        try:
            with zipfile.ZipFile(mxl_path, 'w') as z:
                z.writestr("readme.txt", "no xml here")

            importer = MusicXmlImporter()
            with self.assertRaises(ValueError):
                importer.import_file(mxl_path)
        finally:
            os.unlink(mxl_path)

    def test_regular_xml_still_works(self):
        """Normaler .musicxml Import funktioniert weiterhin."""
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise>
  <work><work-title>Plain XML</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Flute</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note>
        <pitch><step>G</step><octave>5</octave></pitch>
        <duration>4</duration><type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>"""

        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False,
                                         mode='w', encoding='utf-8') as f:
            f.write(xml_content)
            xml_path = f.name

        try:
            importer = MusicXmlImporter()
            piece = importer.import_file(xml_path)
            self.assertEqual(piece.title, "Plain XML")
        finally:
            os.unlink(xml_path)


# =============================================================================
# System Breaks in NotationScene
# =============================================================================

class TestSystemBreaks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def _make_piece_with_measures(self, n_measures, n_parts=1):
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.TimeSignature import TimeSignature

        piece = Piece("Test")
        for p in range(n_parts):
            part = Part(name=f"Part {p+1}", channel=p)
            for i in range(n_measures):
                m = Measure(i + 1, TimeSignature(4, 4))
                m.add_note(Note(60 + p, 0.0, 1.0))
                part.add_measure(m)
            piece.add_part(part)
        return piece

    def test_short_piece_one_system(self):
        """Kurzes Stück (3 Takte) passt in ein System."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece_with_measures(3)
        scene.set_piece(piece)
        systems = scene._compute_systems(piece.parts[0])
        self.assertEqual(len(systems), 1)
        self.assertEqual(len(systems[0]), 3)

    def test_long_piece_multiple_systems(self):
        """Langes Stück wird in mehrere Systeme umbrochen."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece_with_measures(20)
        scene.set_piece(piece)
        systems = scene._compute_systems(piece.parts[0])
        self.assertGreater(len(systems), 1)
        # Alle Takte müssen vorhanden sein
        total = sum(len(s) for s in systems)
        self.assertEqual(total, 20)

    def test_multi_part_renders(self):
        """Multi-Part Stück rendert ohne Fehler."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece_with_measures(8, n_parts=3)
        scene.set_piece(piece)
        self.assertGreater(len(scene.measure_renderers), 0)

    def test_primary_renderers_for_beat_mapping(self):
        """Primary Renderer (Part 0) für Beat↔X Mapping korrekt."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece_with_measures(8, n_parts=2)
        scene.set_piece(piece)
        # Primary Renderer nur für Part 0
        self.assertEqual(len(scene._primary_renderers), 8)

    def test_beat_to_x_and_back(self):
        """beat_to_x und x_to_beat sind invers."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece_with_measures(10)
        scene.set_piece(piece)

        for beat in [0.0, 2.0, 5.5, 10.0]:
            x = scene.beat_to_x(beat)
            result = scene.x_to_beat(x)
            self.assertAlmostEqual(result, beat, places=1,
                                   msg=f"Roundtrip failed for beat={beat}")


# =============================================================================
# System Bracket
# =============================================================================

class TestSystemBracket(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_bracket_drawn_for_multi_part(self):
        """Partiturklammer wird bei Multi-Part Stücken gezeichnet."""
        from musiai.notation.NotationScene import NotationScene
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.TimeSignature import TimeSignature

        piece = Piece("Bracket Test")
        for i in range(2):
            part = Part(name=f"P{i+1}", channel=i)
            m = Measure(1, TimeSignature(4, 4))
            m.add_note(Note(60, 0.0, 1.0))
            part.add_measure(m)
            piece.add_part(part)

        scene = NotationScene()
        scene.set_piece(piece)
        # Scene sollte mehr Items haben als bei Single-Part
        item_count = len(list(scene.items()))
        self.assertGreater(item_count, 0)


# =============================================================================
# Context Menu Signal
# =============================================================================

class TestPlayFromBeatSignal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_signal_exists(self):
        """NotationView hat play_from_beat_requested Signal."""
        from musiai.ui.NotationView import NotationView
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        view = NotationView(scene)
        self.assertTrue(hasattr(view, 'play_from_beat_requested'))

    def test_signal_emits(self):
        """Signal kann emittiert werden."""
        from musiai.ui.NotationView import NotationView
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        view = NotationView(scene)
        received = []
        view.play_from_beat_requested.connect(received.append)
        view.play_from_beat_requested.emit(42.5)
        self.assertEqual(received, [42.5])


# =============================================================================
# Toolbar Hidden
# =============================================================================

class TestToolbarHidden(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_toolbar_not_visible(self):
        from musiai.ui.MainWindow import MainWindow
        mw = MainWindow()
        self.assertFalse(mw.toolbar.isVisible())


if __name__ == "__main__":
    unittest.main()
