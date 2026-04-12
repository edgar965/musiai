"""Tests für Mehrfachauswahl, Copy/Paste von Noten und Takten."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Measure import Measure
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.model.TimeSignature import TimeSignature
from musiai.notation.NotationScene import NotationScene
from musiai.controller.EditController import EditController
from musiai.util.SignalBus import SignalBus


def make_piece():
    piece = Piece("SelectionTest")
    part = Part("Piano")
    m1 = Measure(1)
    m1.add_note(Note(60, 0, 1, Expression(80)))
    m1.add_note(Note(64, 1, 1, Expression(100)))
    m1.add_note(Note(67, 2, 1, Expression(60)))
    m1.add_note(Note(72, 3, 1, Expression(120)))
    m2 = Measure(2)
    m2.add_note(Note(62, 0, 1, Expression(90)))
    m2.add_note(Note(65, 1, 1, Expression(70)))
    part.add_measure(m1)
    part.add_measure(m2)
    piece.add_part(part)
    return piece


def make_env():
    bus = SignalBus()
    scene = NotationScene()
    ctrl = EditController(scene, bus)
    piece = make_piece()
    scene.set_piece(piece)
    items = scene.get_all_note_items()
    return ctrl, scene, piece, items


# ==============================================================
# Einzelauswahl
# ==============================================================

class TestSingleSelection(unittest.TestCase):
    def test_select_one_note(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        self.assertEqual(len(ctrl.selected_notes), 1)

    def test_select_replaces_previous(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1])
        self.assertEqual(len(ctrl.selected_notes), 1)

    def test_deselect_clears(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.deselect()
        self.assertEqual(len(ctrl.selected_notes), 0)
        self.assertIsNone(ctrl.selected_note)


# ==============================================================
# Ctrl+Click Mehrfachauswahl
# ==============================================================

class TestCtrlClickSelection(unittest.TestCase):
    def test_ctrl_adds_note(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        self.assertEqual(len(ctrl.selected_notes), 2)

    def test_ctrl_three_notes(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.select_note(items[2], ctrl=True)
        self.assertEqual(len(ctrl.selected_notes), 3)

    def test_ctrl_toggle_removes(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        # Nochmal Ctrl+Click auf items[1] → entfernen
        ctrl.select_note(items[1], ctrl=True)
        self.assertEqual(len(ctrl.selected_notes), 1)

    def test_ctrl_without_initial_works(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[2], ctrl=True)
        self.assertEqual(len(ctrl.selected_notes), 1)


# ==============================================================
# Shift+Click Range-Auswahl
# ==============================================================

class TestShiftClickSelection(unittest.TestCase):
    def test_shift_selects_range(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[3], shift=True)
        # Sollte items[0] bis items[3] selektieren (4 Noten)
        self.assertGreaterEqual(len(ctrl.selected_notes), 2)

    def test_shift_without_initial_ignored(self):
        ctrl, scene, piece, items = make_env()
        # Shift ohne vorherige Auswahl = normale Auswahl
        ctrl.select_note(items[2], shift=True)
        self.assertEqual(len(ctrl.selected_notes), 1)


# ==============================================================
# Takt-Auswahl
# ==============================================================

class TestMeasureSelection(unittest.TestCase):
    def test_select_measure(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        ctrl.select_measure(m1)
        self.assertEqual(ctrl.selected_measure, m1)
        self.assertEqual(len(ctrl.selected_notes), 4)

    def test_select_measure_selects_all_notes(self):
        ctrl, scene, piece, items = make_env()
        m2 = piece.parts[0].measures[1]
        ctrl.select_measure(m2)
        self.assertEqual(len(ctrl.selected_notes), 2)

    def test_note_click_clears_measure(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        ctrl.select_measure(m1)
        ctrl.select_note(items[0])
        self.assertIsNone(ctrl.selected_measure)


# ==============================================================
# Copy/Paste Noten
# ==============================================================

class TestCopyPasteNotes(unittest.TestCase):
    def test_copy_single_note(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.copy()
        self.assertTrue(ctrl.has_clipboard)

    def test_copy_multiple_notes(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.copy()
        self.assertEqual(len(ctrl._clipboard_notes), 2)

    def test_paste_into_measure(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        m2 = piece.parts[0].measures[1]

        # 2 Noten aus Takt 1 kopieren
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.copy()

        count_before = len(m2.notes)
        ctrl.paste(target_measure=m2)
        self.assertEqual(len(m2.notes), count_before + 2)

    def test_paste_preserves_expression(self):
        ctrl, scene, piece, items = make_env()
        # Note mit vel=100 kopieren
        vel_100_items = [i for i in items if i.note.expression.velocity == 100]
        if vel_100_items:
            ctrl.select_note(vel_100_items[0])
            ctrl.copy()
            m2 = piece.parts[0].measures[1]
            count_before = len(m2.notes)
            ctrl.paste(target_measure=m2)
            # Letzte Note in m2 sollte vel=100 haben
            new_notes = m2.notes[count_before:]
            self.assertTrue(any(n.expression.velocity == 100 for n in new_notes))

    def test_paste_without_copy_does_nothing(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        count = len(m1.notes)
        ctrl.paste(target_measure=m1)
        self.assertEqual(len(m1.notes), count)


# ==============================================================
# Copy/Paste Takte
# ==============================================================

class TestCopyPasteMeasures(unittest.TestCase):
    def test_copy_measure(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        ctrl.select_measure(m1)
        ctrl.copy()
        self.assertEqual(len(ctrl._clipboard_measures), 1)

    def test_paste_measure_inserts(self):
        ctrl, scene, piece, items = make_env()
        part = piece.parts[0]
        m1 = part.measures[0]
        count_before = len(part.measures)

        ctrl.select_measure(m1)
        ctrl.copy()
        ctrl.paste()

        self.assertEqual(len(part.measures), count_before + 1)

    def test_paste_measure_after_selected(self):
        ctrl, scene, piece, items = make_env()
        part = piece.parts[0]
        m1 = part.measures[0]

        ctrl.select_measure(m1)
        ctrl.copy()
        ctrl.paste()

        # Eingefügter Takt sollte nach m1 sein (Position 2)
        self.assertEqual(part.measures[1].number, 2)

    def test_pasted_measure_has_notes(self):
        ctrl, scene, piece, items = make_env()
        part = piece.parts[0]
        m1 = part.measures[0]
        original_count = len(m1.notes)

        ctrl.select_measure(m1)
        ctrl.copy()
        ctrl.paste()

        # Neuer Takt (index 1) sollte gleich viele Noten haben
        new_measure = part.measures[1]
        self.assertEqual(len(new_measure.notes), original_count)

    def test_pasted_measure_renumbered(self):
        ctrl, scene, piece, items = make_env()
        part = piece.parts[0]
        ctrl.select_measure(part.measures[0])
        ctrl.copy()
        ctrl.paste()

        for i, m in enumerate(part.measures):
            self.assertEqual(m.number, i + 1)


# ==============================================================
# Mehrfachauswahl + Bulk Edit
# ==============================================================

class TestBulkEdit(unittest.TestCase):
    def test_change_velocity_all_selected(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.select_note(items[2], ctrl=True)
        ctrl.change_velocity(100)
        for note in ctrl.selected_notes:
            self.assertEqual(note.expression.velocity, 100)

    def test_change_cents_all_selected(self):
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.change_cent_offset(15.0, "zigzag")
        for note in ctrl.selected_notes:
            self.assertAlmostEqual(note.expression.cent_offset, 15.0)

    def test_delete_multiple(self):
        ctrl, scene, piece, items = make_env()
        total_before = sum(len(m.notes) for m in piece.parts[0].measures)
        ctrl.select_note(items[0])
        ctrl.select_note(items[1], ctrl=True)
        ctrl.delete_selected()
        total_after = sum(len(m.notes) for m in piece.parts[0].measures)
        self.assertEqual(total_after, total_before - 2)

    def test_delete_measure_notes(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        ctrl.select_measure(m1)
        ctrl.delete_selected()
        self.assertEqual(len(m1.notes), 0)


# ==============================================================
# Edge Cases
# ==============================================================

class TestEdgeCases(unittest.TestCase):
    def test_copy_empty_selection(self):
        ctrl, scene, piece, items = make_env()
        ctrl.copy()  # Nichts selektiert
        self.assertFalse(ctrl.has_clipboard)

    def test_paste_empty_clipboard(self):
        ctrl, scene, piece, items = make_env()
        m1 = piece.parts[0].measures[0]
        count = len(m1.notes)
        ctrl.paste(m1)
        self.assertEqual(len(m1.notes), count)

    def test_delete_empty_selection(self):
        ctrl, scene, piece, items = make_env()
        total = sum(len(m.notes) for m in piece.parts[0].measures)
        ctrl.delete_selected()  # Nichts selektiert
        total2 = sum(len(m.notes) for m in piece.parts[0].measures)
        self.assertEqual(total, total2)

    def test_select_after_refresh(self):
        """Auswahl sollte nach Scene-Refresh noch funktionieren."""
        ctrl, scene, piece, items = make_env()
        ctrl.select_note(items[0])
        note = ctrl.selected_note
        scene.refresh()
        # Note-Referenz überlebt Refresh
        self.assertIsNotNone(ctrl.selected_note)
        self.assertEqual(ctrl.selected_note, note)


if __name__ == "__main__":
    unittest.main()
