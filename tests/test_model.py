"""Tests für das Datenmodell (model/)."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestExpression(unittest.TestCase):
    def test_defaults(self):
        from musiai.model.Expression import Expression
        e = Expression()
        self.assertEqual(e.velocity, 80)
        self.assertEqual(e.cent_offset, 0.0)
        self.assertEqual(e.duration_deviation, 1.0)
        self.assertEqual(e.glide_type, "none")

    def test_custom_values(self):
        from musiai.model.Expression import Expression
        e = Expression(velocity=120, cent_offset=-15.0, duration_deviation=1.1, glide_type="curve")
        self.assertEqual(e.velocity, 120)
        self.assertEqual(e.cent_offset, -15.0)
        self.assertEqual(e.glide_type, "curve")

    def test_serialize_roundtrip(self):
        from musiai.model.Expression import Expression
        e = Expression(velocity=100, cent_offset=4.5, duration_deviation=0.95, glide_type="zigzag")
        d = e.to_dict()
        e2 = Expression.from_dict(d)
        self.assertEqual(e2.velocity, e.velocity)
        self.assertAlmostEqual(e2.cent_offset, e.cent_offset)
        self.assertAlmostEqual(e2.duration_deviation, e.duration_deviation)
        self.assertEqual(e2.glide_type, e.glide_type)


class TestTimeSignature(unittest.TestCase):
    def test_4_4(self):
        from musiai.model.TimeSignature import TimeSignature
        self.assertEqual(TimeSignature(4, 4).beats_per_measure(), 4.0)

    def test_3_4(self):
        from musiai.model.TimeSignature import TimeSignature
        self.assertEqual(TimeSignature(3, 4).beats_per_measure(), 3.0)

    def test_6_8(self):
        from musiai.model.TimeSignature import TimeSignature
        self.assertEqual(TimeSignature(6, 8).beats_per_measure(), 3.0)

    def test_5_4(self):
        from musiai.model.TimeSignature import TimeSignature
        self.assertEqual(TimeSignature(5, 4).beats_per_measure(), 5.0)

    def test_repr(self):
        from musiai.model.TimeSignature import TimeSignature
        self.assertEqual(str(TimeSignature(3, 4)), "3/4")


class TestTempo(unittest.TestCase):
    def test_seconds_per_beat(self):
        from musiai.model.Tempo import Tempo
        self.assertAlmostEqual(Tempo(120).seconds_per_beat(), 0.5)
        self.assertAlmostEqual(Tempo(60).seconds_per_beat(), 1.0)
        self.assertAlmostEqual(Tempo(180).seconds_per_beat(), 1 / 3)

    def test_serialize(self):
        from musiai.model.Tempo import Tempo
        t = Tempo(96.0, 8.0)
        t2 = Tempo.from_dict(t.to_dict())
        self.assertEqual(t2.bpm, 96.0)
        self.assertEqual(t2.beat_position, 8.0)


class TestNote(unittest.TestCase):
    def test_name(self):
        from musiai.model.Note import Note
        self.assertEqual(Note(pitch=60).name, "C4")
        self.assertEqual(Note(pitch=69).name, "A4")
        self.assertEqual(Note(pitch=72).name, "C5")

    def test_end_beat(self):
        from musiai.model.Note import Note
        n = Note(pitch=60, start_beat=1.5, duration_beats=2.0)
        self.assertAlmostEqual(n.end_beat, 3.5)

    def test_frequency_with_cents(self):
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        n_normal = Note(pitch=69)
        n_sharp = Note(pitch=69, expression=Expression(cent_offset=10))
        self.assertGreater(n_sharp.frequency, n_normal.frequency)

    def test_serialize(self):
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        n = Note(60, 0.5, 1.5, Expression(110, -5.0, 1.05, "zigzag"))
        n2 = Note.from_dict(n.to_dict())
        self.assertEqual(n2.pitch, 60)
        self.assertAlmostEqual(n2.start_beat, 0.5)
        self.assertEqual(n2.expression.velocity, 110)


class TestMeasure(unittest.TestCase):
    def test_add_notes_sorted(self):
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        m = Measure(1)
        m.add_note(Note(64, 2.0, 1.0))
        m.add_note(Note(60, 0.0, 1.0))
        m.add_note(Note(62, 1.0, 1.0))
        self.assertEqual([n.pitch for n in m.notes], [60, 62, 64])

    def test_get_note_at(self):
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        m = Measure(1)
        m.add_note(Note(60, 0.0, 1.0))
        m.add_note(Note(64, 2.0, 1.0))
        self.assertIsNotNone(m.get_note_at(2.0))
        self.assertIsNone(m.get_note_at(3.0))

    def test_remove_note(self):
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        m = Measure(1)
        n = Note(60, 0.0, 1.0)
        m.add_note(n)
        m.remove_note(n)
        self.assertEqual(len(m.notes), 0)

    def test_duration_seconds(self):
        from musiai.model.Measure import Measure
        from musiai.model.TimeSignature import TimeSignature
        m = Measure(1, time_signature=TimeSignature(3, 4))
        self.assertAlmostEqual(m.duration_seconds(120.0), 1.5)


class TestPiece(unittest.TestCase):
    def test_tempo_at_beat(self):
        from musiai.model.Piece import Piece
        from musiai.model.Tempo import Tempo
        p = Piece("Test")
        p.tempos = [Tempo(120, 0), Tempo(80, 8)]
        self.assertEqual(p.tempo_at_beat(4), 120)
        self.assertEqual(p.tempo_at_beat(10), 80)

    def test_total_measures(self):
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        p = Piece("Test")
        part = Part("Piano")
        part.add_measure(Measure(1))
        part.add_measure(Measure(2))
        p.add_part(part)
        self.assertEqual(p.total_measures, 2)


class TestProject(unittest.TestCase):
    def test_save_load(self):
        from musiai.model.Project import Project
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        import tempfile, os

        proj = Project()
        piece = Piece("SaveTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(90, 5.0, 1.05, "zigzag")))
        part.add_measure(m)
        piece.add_part(part)
        proj.add_piece(piece)

        path = os.path.join(tempfile.gettempdir(), "test_project.musiai")
        proj.save(path)
        proj2 = Project()
        proj2.load(path)
        n = proj2.current_piece.parts[0].measures[0].notes[0]
        self.assertEqual(n.expression.velocity, 90)
        self.assertAlmostEqual(n.expression.cent_offset, 5.0)
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
