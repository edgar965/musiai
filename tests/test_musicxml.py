"""Tests für den MusicXML Parser (musiai/musicXML/)."""

import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

EXAMPLE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "media", "music",
                 "beispiel_micro_expression.musicxml")
)


class TestPitchParser(unittest.TestCase):
    """Tests für PitchParser - Mikrotöne."""

    def _parse(self, step, octave, alter=None):
        import xml.etree.ElementTree as ET
        from musiai.musicXML.PitchParser import PitchParser
        pitch = ET.Element("pitch")
        ET.SubElement(pitch, "step").text = step
        ET.SubElement(pitch, "octave").text = str(octave)
        if alter is not None:
            ET.SubElement(pitch, "alter").text = str(alter)
        return PitchParser.parse(pitch)

    def test_c4_no_alter(self):
        r = self._parse("C", 4)
        self.assertEqual(r.midi_note, 60)
        self.assertAlmostEqual(r.cent_offset, 0.0)

    def test_a4_no_alter(self):
        r = self._parse("A", 4)
        self.assertEqual(r.midi_note, 69)

    def test_c_sharp(self):
        """<alter>1</alter> → C# (1 Halbton)."""
        r = self._parse("C", 4, 1)
        self.assertEqual(r.midi_note, 61)
        self.assertAlmostEqual(r.cent_offset, 0.0)

    def test_microtone_4_cent(self):
        """<alter>0.04</alter> → 4 Cent hoch."""
        r = self._parse("E", 4, 0.04)
        self.assertEqual(r.midi_note, 64)
        self.assertAlmostEqual(r.cent_offset, 4.0)

    def test_microtone_quarter_sharp(self):
        """<alter>0.5</alter> → 50 Cent (Viertelton)."""
        r = self._parse("G", 4, 0.5)
        self.assertEqual(r.midi_note, 67)
        self.assertAlmostEqual(r.cent_offset, 50.0)

    def test_microtone_negative(self):
        """<alter>-0.10</alter> → -10 Cent."""
        r = self._parse("G", 4, -0.10)
        self.assertEqual(r.midi_note, 67)
        self.assertAlmostEqual(r.cent_offset, -10.0)

    def test_sharp_plus_microtone(self):
        """<alter>1.15</alter> → C# + 15 Cent."""
        r = self._parse("C", 4, 1.15)
        self.assertEqual(r.midi_note, 61)
        self.assertAlmostEqual(r.cent_offset, 15.0)

    def test_flat(self):
        """<alter>-1</alter> → Bb."""
        r = self._parse("B", 4, -1)
        self.assertEqual(r.midi_note, 70)  # Bb4
        self.assertAlmostEqual(r.cent_offset, 0.0)

    def test_missing_step_returns_none(self):
        import xml.etree.ElementTree as ET
        from musiai.musicXML.PitchParser import PitchParser
        pitch = ET.Element("pitch")
        ET.SubElement(pitch, "octave").text = "4"
        self.assertIsNone(PitchParser.parse(pitch))


class TestNoteParser(unittest.TestCase):
    """Tests für NoteParser."""

    def _make_note_xml(self, step="C", octave=4, alter=None,
                       duration=480, velocity=None, rest=False):
        import xml.etree.ElementTree as ET
        note = ET.Element("note")
        if rest:
            ET.SubElement(note, "rest")
            ET.SubElement(note, "duration").text = str(duration)
            return note
        pitch = ET.SubElement(note, "pitch")
        ET.SubElement(pitch, "step").text = step
        ET.SubElement(pitch, "octave").text = str(octave)
        if alter is not None:
            ET.SubElement(pitch, "alter").text = str(alter)
        ET.SubElement(note, "duration").text = str(duration)
        if velocity is not None:
            sound = ET.SubElement(note, "sound", dynamics=str(velocity))
        return note

    def test_parse_simple_note(self):
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml("C", 4, duration=480)
        note = NoteParser.parse(xml, "", 480, 80, 0.0)
        self.assertIsNotNone(note)
        self.assertEqual(note.pitch, 60)
        self.assertAlmostEqual(note.duration_beats, 1.0)

    def test_parse_note_with_velocity(self):
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml("E", 4, velocity=110)
        note = NoteParser.parse(xml, "", 480, 80, 0.0)
        self.assertEqual(note.expression.velocity, 110)

    def test_parse_note_with_microtone(self):
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml("E", 4, alter=0.04)
        note = NoteParser.parse(xml, "", 480, 80, 0.0)
        self.assertEqual(note.pitch, 64)
        self.assertAlmostEqual(note.expression.cent_offset, 4.0)
        self.assertEqual(note.expression.glide_type, "zigzag")

    def test_parse_rest_returns_none(self):
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml(rest=True)
        self.assertIsNone(NoteParser.parse(xml, "", 480, 80, 0.0))

    def test_velocity_clamped(self):
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml(velocity=200)
        note = NoteParser.parse(xml, "", 480, 80, 0.0)
        self.assertEqual(note.expression.velocity, 127)

    def test_glissando_sets_curve(self):
        import xml.etree.ElementTree as ET
        from musiai.musicXML.NoteParser import NoteParser
        xml = self._make_note_xml("C", 4, alter=0.2)
        notations = ET.SubElement(xml, "notations")
        ET.SubElement(notations, "glissando", type="start")
        note = NoteParser.parse(xml, "", 480, 80, 0.0)
        self.assertEqual(note.expression.glide_type, "curve")


class TestMusicXmlImporter(unittest.TestCase):
    """Tests für den kompletten MusicXML Import."""

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_import_example_file(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        self.assertEqual(piece.title, "Micro-Expression Demo")
        self.assertEqual(len(piece.parts), 1)
        self.assertEqual(len(piece.parts[0].measures), 2)

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_microtones_preserved(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        notes = piece.parts[0].measures[0].notes
        # E4 +4ct
        e4 = [n for n in notes if n.pitch == 64][0]
        self.assertAlmostEqual(e4.expression.cent_offset, 4.0)
        # G4 -10ct
        g4 = [n for n in notes if n.pitch == 67][0]
        self.assertAlmostEqual(g4.expression.cent_offset, -10.0)
        # C5 +15ct
        c5 = [n for n in notes if n.pitch == 72][0]
        self.assertAlmostEqual(c5.expression.cent_offset, 15.0)

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_velocity_preserved(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        notes = piece.parts[0].measures[0].notes
        e4 = [n for n in notes if n.pitch == 64][0]
        self.assertEqual(e4.expression.velocity, 90)

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_duration_deviation_preserved(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        notes = piece.parts[0].measures[0].notes
        # Takt 2 hat Standard-Noten (keine Abweichung)
        notes2 = piece.parts[0].measures[1].notes
        for n in notes2:
            self.assertAlmostEqual(n.expression.duration_deviation, 1.0)

    def test_import_nonexistent_raises(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        with self.assertRaises(FileNotFoundError):
            MusicXmlImporter().import_file("nonexistent.musicxml")

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_time_signature(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        ts = piece.parts[0].measures[0].time_signature
        self.assertEqual(ts.numerator, 4)
        self.assertEqual(ts.denominator, 4)

    @unittest.skipUnless(os.path.exists(EXAMPLE_FILE), "Beispieldatei fehlt")
    def test_tempo(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = MusicXmlImporter().import_file(EXAMPLE_FILE)
        self.assertAlmostEqual(piece.initial_tempo, 100.0)


class TestMusicXmlExporter(unittest.TestCase):
    """Tests für den MusicXML Export."""

    def _make_piece(self):
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        piece = Piece("ExportTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(80, 0, 1.0)))
        m.add_note(Note(64, 1, 1, Expression(110, 15.0, 1.0, "zigzag")))
        m.add_note(Note(67, 2, 1, Expression(50, -20.0, 1.0, "curve")))
        part.add_measure(m)
        piece.add_part(part)
        return piece

    def test_export_creates_file(self):
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_export.musicxml")
        MusicXmlExporter().export_file(piece, path)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 100)
        os.unlink(path)

    def test_export_contains_alter(self):
        """Export sollte <alter> für Mikrotöne enthalten."""
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_alter.musicxml")
        MusicXmlExporter().export_file(piece, path)
        content = Path(path).read_text(encoding="utf-8")
        self.assertIn("<alter>", content)
        os.unlink(path)

    def test_export_contains_dynamics(self):
        """Export sollte <sound dynamics="X"/> enthalten."""
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_dyn.musicxml")
        MusicXmlExporter().export_file(piece, path)
        content = Path(path).read_text(encoding="utf-8")
        self.assertIn('dynamics="110"', content)
        os.unlink(path)

    def test_roundtrip_preserves_microtones(self):
        """Export → Import Roundtrip bewahrt Mikrotöne."""
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_rt.musicxml")
        MusicXmlExporter().export_file(piece, path)
        piece2 = MusicXmlImporter().import_file(path)
        notes = piece2.parts[0].measures[0].notes
        e4 = [n for n in notes if n.pitch == 64][0]
        self.assertAlmostEqual(e4.expression.cent_offset, 15.0, delta=1.0)
        os.unlink(path)

    def test_roundtrip_preserves_velocity(self):
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_rv.musicxml")
        MusicXmlExporter().export_file(piece, path)
        piece2 = MusicXmlImporter().import_file(path)
        notes = piece2.parts[0].measures[0].notes
        e4 = [n for n in notes if n.pitch == 64][0]
        self.assertEqual(e4.expression.velocity, 110)
        os.unlink(path)

    def test_roundtrip_preserves_glissando(self):
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        piece = self._make_piece()
        path = os.path.join(tempfile.gettempdir(), "test_xml_gl.musicxml")
        MusicXmlExporter().export_file(piece, path)
        piece2 = MusicXmlImporter().import_file(path)
        notes = piece2.parts[0].measures[0].notes
        g4 = [n for n in notes if n.pitch == 67][0]
        self.assertEqual(g4.expression.glide_type, "curve")
        os.unlink(path)


class TestMusicXmlConstants(unittest.TestCase):
    """Tests für MusicXML Konstanten."""

    def test_step_to_semitone(self):
        from musiai.musicXML.MusicXmlConstants import STEP_TO_SEMITONE
        self.assertEqual(STEP_TO_SEMITONE["C"], 0)
        self.assertEqual(STEP_TO_SEMITONE["A"], 9)
        self.assertEqual(len(STEP_TO_SEMITONE), 7)

    def test_dynamics_to_velocity(self):
        from musiai.musicXML.MusicXmlConstants import DYNAMICS_TO_VELOCITY
        self.assertEqual(DYNAMICS_TO_VELOCITY["pp"], 33)
        self.assertEqual(DYNAMICS_TO_VELOCITY["ff"], 112)
        self.assertLess(DYNAMICS_TO_VELOCITY["p"], DYNAMICS_TO_VELOCITY["f"])


if __name__ == "__main__":
    unittest.main()
