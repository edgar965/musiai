"""Tests für MIDI I/O (midi/)."""

import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMidiMapping(unittest.TestCase):
    def test_velocity_cc(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        result = m.map_cc(1, 100)
        self.assertEqual(result, ("velocity", 100.0))

    def test_duration_cc(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        result = m.map_cc(11, 64)
        self.assertEqual(result[0], "duration")
        self.assertAlmostEqual(result[1], 1.0, delta=0.05)

    def test_unknown_cc_returns_none(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        self.assertIsNone(m.map_cc(99, 50))

    def test_pitch_bend_center(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        self.assertAlmostEqual(m.map_pitch_bend(8192), 0.0, delta=0.1)

    def test_pitch_bend_max(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        cents = m.map_pitch_bend(16383)
        self.assertGreater(cents, 40)

    def test_pitch_bend_min(self):
        from musiai.midi.MidiMapping import MidiMapping
        m = MidiMapping()
        cents = m.map_pitch_bend(0)
        self.assertLess(cents, -40)


class TestMidiExporter(unittest.TestCase):
    def test_export_creates_file(self):
        from musiai.midi.MidiExporter import MidiExporter
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression

        piece = Piece("ExportTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(100, 5.0)))
        m.add_note(Note(64, 1, 1, Expression(80, 0)))
        m.add_note(Note(67, 2, 2, Expression(60, -10.0, 0.95, "curve")))
        part.add_measure(m)
        piece.add_part(part)

        path = os.path.join(tempfile.gettempdir(), "test_export.mid")
        MidiExporter().export_file(piece, path)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 50)
        os.unlink(path)

    def test_export_with_expression(self):
        """Expression-Daten (pitch bend) sollten im Export enthalten sein."""
        from musiai.midi.MidiExporter import MidiExporter
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        import mido

        piece = Piece("BendTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(100, 25.0, 1.0, "zigzag")))
        part.add_measure(m)
        piece.add_part(part)

        path = os.path.join(tempfile.gettempdir(), "test_bend.mid")
        MidiExporter().export_file(piece, path)

        mid = mido.MidiFile(path)
        has_pitchwheel = any(
            msg.type == "pitchwheel" for track in mid.tracks for msg in track
            if hasattr(msg, "type")
        )
        self.assertTrue(has_pitchwheel, "MIDI should contain pitch bend for cent offset")
        os.unlink(path)


class TestMidiKeyboard(unittest.TestCase):
    def test_list_ports_no_crash(self):
        from musiai.midi.MidiKeyboard import MidiKeyboard
        ports = MidiKeyboard.list_ports()
        self.assertIsInstance(ports, list)


if __name__ == "__main__":
    unittest.main()
