"""Tests für alle Notation-Renderer (MusicXML, MIDI Sheet, SVG, Piano Roll)."""

import sys
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

_qapp = None

def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)


def _make_test_piece(n_measures=4, n_parts=1):
    """Erstellt ein Test-Piece mit Noten."""
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.TimeSignature import TimeSignature

    piece = Piece("Test Piece")
    for p in range(n_parts):
        part = Part(f"Part {p+1}", p)
        for i in range(n_measures):
            m = Measure(i + 1, TimeSignature(4, 4))
            m.add_note(Note(60 + p * 12, 0.0, 1.0))
            m.add_note(Note(64 + p * 12, 1.0, 1.0))
            m.add_note(Note(67 + p * 12, 2.0, 1.0))
            m.add_note(Note(72 + p * 12, 3.0, 0.5))
            part.add_measure(m)
        piece.add_part(part)
    return piece


# =============================================================================
# WhiteNote Tests
# =============================================================================

class TestWhiteNote(unittest.TestCase):

    def test_from_midi_c4(self):
        from musiai.ui.midi.WhiteNote import WhiteNote, C
        wn = WhiteNote.from_midi(60)
        self.assertEqual(wn.letter, C)
        self.assertEqual(wn.octave, 4)

    def test_from_midi_a4(self):
        from musiai.ui.midi.WhiteNote import WhiteNote, A
        wn = WhiteNote.from_midi(69)
        self.assertEqual(wn.letter, A)

    def test_dist(self):
        from musiai.ui.midi.WhiteNote import WhiteNote, C, E
        c4 = WhiteNote(C, 4)
        e4 = WhiteNote(E, 4)
        self.assertEqual(e4.dist(c4), 2)
        self.assertEqual(c4.dist(e4), -2)

    def test_add(self):
        from musiai.ui.midi.WhiteNote import WhiteNote, C
        c4 = WhiteNote(C, 4)
        d4 = c4.add(1)
        self.assertEqual(d4.letter, 3)  # D

    def test_to_midi_roundtrip(self):
        from musiai.ui.midi.WhiteNote import WhiteNote
        for midi in [48, 55, 60, 67, 72, 84]:
            wn = WhiteNote.from_midi(midi)
            back = wn.to_midi()
            self.assertAlmostEqual(back, midi, delta=1,
                                   msg=f"Roundtrip failed: {midi} -> {wn} -> {back}")


# =============================================================================
# NoteDuration Tests
# =============================================================================

class TestNoteDuration(unittest.TestCase):

    def test_quarter(self):
        from musiai.ui.midi import NoteDuration as ND
        self.assertEqual(ND.from_beats(1.0), ND.QUARTER)

    def test_eighth(self):
        from musiai.ui.midi import NoteDuration as ND
        self.assertEqual(ND.from_beats(0.5), ND.EIGHTH)

    def test_whole(self):
        from musiai.ui.midi import NoteDuration as ND
        self.assertEqual(ND.from_beats(4.0), ND.WHOLE)

    def test_half(self):
        from musiai.ui.midi import NoteDuration as ND
        self.assertEqual(ND.from_beats(2.0), ND.HALF)

    def test_sixteenth(self):
        from musiai.ui.midi import NoteDuration as ND
        self.assertEqual(ND.from_beats(0.25), ND.SIXTEENTH)


# =============================================================================
# Verovio SVG Renderer
# =============================================================================

class TestVerovioRenderer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_render_creates_svg_items(self):
        from musiai.notation.VerovioRenderer import VerovioRenderer
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = _make_test_piece()
        vr = VerovioRenderer()
        ok = vr.render_piece(piece, scene, 800)
        self.assertTrue(ok, "Verovio render should succeed")
        # Mindestens 1 SVG Item + Playhead + Cursor
        self.assertGreater(len(list(scene.items())), 2)

    def test_export_string_valid_xml(self):
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = _make_test_piece()
        xml = MusicXmlExporter().export_string(piece)
        self.assertTrue(xml.startswith("<?xml"))
        self.assertIn("<score-partwise", xml)
        self.assertIn("<note>", xml)


# =============================================================================
# Piano Roll Renderer
# =============================================================================

class TestPianoRollRenderer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_render_creates_items(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = _make_test_piece()
        scene.piece = piece
        scene._render_mode = "pianoroll"
        scene.refresh()
        # Mindestens Noten-Rechtecke + Grid + Playhead + Cursor
        items = list(scene.items())
        self.assertGreater(len(items), 10,
                           f"Piano Roll should create many items, got {len(items)}")

    def test_no_crash_empty_piece(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.model.Piece import Piece
        scene = NotationScene()
        scene.piece = Piece("Empty")
        scene._render_mode = "pianoroll"
        scene.refresh()  # Should not crash


# =============================================================================
# MIDI Sheet Renderer
# =============================================================================

class TestMidiSheetRenderer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_render_creates_pixmaps(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.ui.midi.MidiSheetRenderer import MidiSheetRenderer
        from PySide6.QtWidgets import QGraphicsPixmapItem
        scene = NotationScene()
        piece = _make_test_piece()
        mr = MidiSheetRenderer()
        mr.render(piece, scene, 800)
        pixmaps = [i for i in scene.items()
                   if isinstance(i, QGraphicsPixmapItem)]
        self.assertGreater(len(pixmaps), 0, "Should create at least 1 pixmap")
        # Pixmap should not be empty
        for pm_item in pixmaps:
            pm = pm_item.pixmap()
            self.assertFalse(pm.isNull(), "Pixmap should not be null")
            self.assertGreater(pm.width(), 100)
            self.assertGreater(pm.height(), 50)

    def test_chord_symbol_min_width(self):
        from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
        from musiai.ui.midi.WhiteNote import WhiteNote
        from musiai.ui.midi import NoteDuration as ND
        nd = NoteData(60, WhiteNote.from_midi(60), ND.QUARTER)
        chord = ChordSymbol([nd])
        self.assertGreater(chord.min_width, 0)

    def test_stem_direction_treble(self):
        from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
        from musiai.ui.midi.WhiteNote import WhiteNote
        from musiai.ui.midi.Stem import UP, DOWN
        from musiai.ui.midi import NoteDuration as ND
        # Low note -> stem up
        nd_low = NoteData(48, WhiteNote.from_midi(48), ND.QUARTER)
        chord_low = ChordSymbol([nd_low])
        self.assertEqual(chord_low.stem.direction, UP)
        # High note -> stem down
        nd_high = NoteData(84, WhiteNote.from_midi(84), ND.QUARTER)
        chord_high = ChordSymbol([nd_high])
        self.assertEqual(chord_high.stem.direction, DOWN)

    def test_bar_symbol(self):
        from musiai.ui.midi.BarSymbol import BarSymbol
        b = BarSymbol(480)
        self.assertEqual(b.start_time, 480)
        self.assertGreater(b.min_width, 0)

    def test_staff_height(self):
        from musiai.ui.midi.Staff import Staff
        from musiai.ui.midi.BarSymbol import BarSymbol
        staff = Staff([BarSymbol(0)], [], 480, 0, 1)
        self.assertGreater(staff.height, 40)


# =============================================================================
# NotationScene Mode Switching
# =============================================================================

class TestNotationSceneModes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_default_mode_musicxml(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        self.assertEqual(scene.render_mode, "musicxml")

    def test_set_mode_midisheet(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_render_mode("midisheet")
        self.assertEqual(scene.render_mode, "midisheet")

    def test_set_mode_svg(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_render_mode("svg")
        self.assertEqual(scene.render_mode, "svg")

    def test_set_mode_pianoroll(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_render_mode("pianoroll")
        self.assertEqual(scene.render_mode, "pianoroll")

    def test_invalid_mode_ignored(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_render_mode("invalid")
        self.assertEqual(scene.render_mode, "musicxml")

    def test_midisheet_renders_without_crash(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = _make_test_piece()
        scene.set_render_mode("midisheet")
        scene.set_piece(piece)
        self.assertGreater(len(list(scene.items())), 0)

    def test_svg_renders_without_crash(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = _make_test_piece()
        scene.set_render_mode("svg")
        scene.set_piece(piece)
        self.assertGreater(len(list(scene.items())), 0)

    def test_pianoroll_renders_without_crash(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = _make_test_piece()
        scene.set_render_mode("pianoroll")
        scene.set_piece(piece)
        self.assertGreater(len(list(scene.items())), 0)


if __name__ == "__main__":
    unittest.main()
