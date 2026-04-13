"""Integration Tests - Projekt save/load roundtrip mit Expression."""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)


class TestProjectRoundtrip(unittest.TestCase):
    """Kompletter Save/Load Roundtrip mit allen Expression-Features."""

    def test_full_roundtrip(self):
        from musiai.model.Project import Project
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        from musiai.model.TimeSignature import TimeSignature
        from musiai.model.Tempo import Tempo

        # Erstellen
        proj = Project()
        piece = Piece("Roundtrip-Test")
        piece.tempos = [Tempo(96.0, 0.0), Tempo(72.0, 12.0)]

        part = Part("Klavier", channel=0)
        m = Measure(1, TimeSignature(5, 4))
        m.add_note(Note(60, 0, 1, Expression(30, 0, 1.0, "none")))
        m.add_note(Note(64, 1, 1, Expression(120, 25.0, 1.1, "zigzag")))
        m.add_note(Note(67, 2, 1.5, Expression(80, -15.0, 0.9, "curve")))
        m.add_note(Note(72, 3.5, 1.5, Expression(100, 0, 1.0, "none")))
        part.add_measure(m)
        piece.add_part(part)
        proj.add_piece(piece)

        # Speichern
        path = os.path.join(tempfile.gettempdir(), "roundtrip.musiai")
        proj.save(path)

        # Laden
        proj2 = Project()
        proj2.load(path)

        # Vergleichen
        p = proj2.current_piece
        self.assertEqual(p.title, "Roundtrip-Test")
        self.assertEqual(len(p.tempos), 2)
        self.assertAlmostEqual(p.tempos[1].bpm, 72.0)

        part2 = p.parts[0]
        self.assertEqual(part2.name, "Klavier")
        self.assertEqual(part2.channel, 0)

        m2 = part2.measures[0]
        self.assertEqual(m2.time_signature.numerator, 5)
        self.assertEqual(len(m2.notes), 4)

        n1 = m2.notes[1]  # E4 mit zigzag
        self.assertEqual(n1.pitch, 64)
        self.assertEqual(n1.expression.velocity, 120)
        self.assertAlmostEqual(n1.expression.cent_offset, 25.0)
        self.assertAlmostEqual(n1.expression.duration_deviation, 1.1)
        self.assertEqual(n1.expression.glide_type, "zigzag")

        n2 = m2.notes[2]  # G4 mit curve
        self.assertEqual(n2.expression.glide_type, "curve")
        self.assertAlmostEqual(n2.expression.cent_offset, -15.0)

        os.unlink(path)


class TestEditAndSave(unittest.TestCase):
    """Edit → Save → Load → Verify edits persisted."""

    def test_edit_persists_after_save(self):
        from musiai.controller.AppController import AppController
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        import tempfile

        ctrl = AppController()
        piece = Piece("EditPersist")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(80)))
        part.add_measure(m)
        piece.add_part(part)
        ctrl.project.add_piece(piece)
        ctrl.signal_bus.piece_loaded.emit(piece)

        # Edit
        items = ctrl._active_scene().get_all_note_items()
        ctrl._active_edit_controller().select_note(items[0])
        ctrl._active_edit_controller().change_velocity(115)
        ctrl._active_edit_controller().change_cent_offset(20.0, "curve")

        # Save
        path = os.path.join(tempfile.gettempdir(), "edit_persist.musiai")
        ctrl.project.save(path)

        # Load in fresh project
        from musiai.model.Project import Project
        proj2 = Project()
        proj2.load(path)
        n = proj2.current_piece.parts[0].measures[0].notes[0]
        self.assertEqual(n.expression.velocity, 115)
        self.assertAlmostEqual(n.expression.cent_offset, 20.0)
        self.assertEqual(n.expression.glide_type, "curve")

        ctrl.shutdown()
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
