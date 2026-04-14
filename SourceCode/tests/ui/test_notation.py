"""Tests für Notation-Rendering (notation/)."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)


class TestColorScheme(unittest.TestCase):
    def setUp(self):
        from PySide6.QtCore import QSettings
        s = QSettings("MusiAI", "MusiAI")
        # Ensure default colors for tests
        self._orig_std = s.value("musicxml/vel_color_std")
        self._orig_soft = s.value("musicxml/vel_color_soft")
        self._orig_loud = s.value("musicxml/vel_color_loud")
        s.setValue("musicxml/vel_color_std", "#FF0000")
        s.setValue("musicxml/vel_color_soft", "#FFFF00")
        s.setValue("musicxml/vel_color_loud", "#0000FF")
        from musiai.notation.ColorScheme import ColorScheme
        ColorScheme.reload_colors()

    def tearDown(self):
        from PySide6.QtCore import QSettings
        s = QSettings("MusiAI", "MusiAI")
        if self._orig_std:
            s.setValue("musicxml/vel_color_std", self._orig_std)
        if self._orig_soft:
            s.setValue("musicxml/vel_color_soft", self._orig_soft)
        if self._orig_loud:
            s.setValue("musicxml/vel_color_loud", self._orig_loud)
        from musiai.notation.ColorScheme import ColorScheme
        ColorScheme.reload_colors()

    def test_velocity_yellow_at_zero(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.velocity_to_color(0)
        self.assertEqual(c.red(), 255)
        self.assertEqual(c.green(), 255)
        self.assertEqual(c.blue(), 0)

    def test_velocity_red_at_default(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.velocity_to_color(80)
        self.assertEqual(c.red(), 255)
        self.assertEqual(c.green(), 0)

    def test_velocity_blue_at_max(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.velocity_to_color(127)
        self.assertEqual(c.blue(), 255)
        self.assertEqual(c.red(), 0)

    def test_velocity_gradient_monotonic(self):
        """Blue channel should increase from 80 to 127."""
        from musiai.notation.ColorScheme import ColorScheme
        prev_blue = 0
        for v in range(80, 128):
            c = ColorScheme.velocity_to_color(v)
            self.assertGreaterEqual(c.blue(), prev_blue)
            prev_blue = c.blue()

    def test_duration_short_is_red(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.duration_to_color(0.8)
        self.assertGreater(c.red(), 200)

    def test_duration_long_is_blue(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.duration_to_color(1.2)
        self.assertGreater(c.blue(), 200)

    def test_duration_standard_is_gray(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.duration_to_color(1.0)
        self.assertEqual(c.red(), 100)


class TestNotationScene(unittest.TestCase):
    def setUp(self):
        from PySide6.QtCore import QSettings
        s = QSettings("MusiAI", "MusiAI")
        self._orig_bravura = s.value("ui/musicxml_bravura", "true")
        s.setValue("ui/musicxml_bravura", "false")

    def tearDown(self):
        from PySide6.QtCore import QSettings
        QSettings("MusiAI", "MusiAI").setValue(
            "ui/musicxml_bravura", self._orig_bravura)

    def _make_piece(self, num_measures=2, notes_per_measure=3):
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression

        piece = Piece("Test")
        part = Part("Piano")
        for i in range(num_measures):
            m = Measure(i + 1)
            for j in range(notes_per_measure):
                expr = Expression(velocity=40 + j * 30, cent_offset=j * 5.0,
                                  glide_type="zigzag" if j == 1 else "none")
                m.add_note(Note(60 + j * 4, j, 1.0, expr))
            part.add_measure(m)
        piece.add_part(part)
        return piece

    def test_render_creates_items(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece(2, 3)
        scene.set_piece(piece)
        items = scene.get_all_note_items()
        self.assertEqual(len(items), 6)
        self.assertEqual(len(scene.measure_renderers), 2)

    def test_refresh_clears_and_redraws(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece(1, 2)
        scene.set_piece(piece)
        self.assertEqual(len(scene.get_all_note_items()), 2)
        scene.refresh()
        self.assertEqual(len(scene.get_all_note_items()), 2)

    def test_playhead(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(self._make_piece())
        scene.update_playhead(2.0)
        self.assertTrue(scene.playhead.isVisible())
        scene.hide_playhead()
        self.assertFalse(scene.playhead.isVisible())


class TestNotationSceneBravura(unittest.TestCase):
    """Same tests as TestNotationScene but with Bravura/MidiSheet pipeline."""

    def setUp(self):
        from PySide6.QtCore import QSettings
        s = QSettings("MusiAI", "MusiAI")
        self._orig_bravura = s.value("ui/musicxml_bravura", "true")
        s.setValue("ui/musicxml_bravura", "true")

    def tearDown(self):
        from PySide6.QtCore import QSettings
        QSettings("MusiAI", "MusiAI").setValue(
            "ui/musicxml_bravura", self._orig_bravura)

    def _make_piece(self, num_measures=2, notes_per_measure=3):
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression

        piece = Piece("Test")
        part = Part("Piano")
        for i in range(num_measures):
            m = Measure(i + 1)
            for j in range(notes_per_measure):
                expr = Expression(velocity=40 + j * 30, cent_offset=j * 5.0,
                                  glide_type="zigzag" if j == 1 else "none")
                m.add_note(Note(60 + j * 4, j, 1.0, expr))
            part.add_measure(m)
        piece.add_part(part)
        return piece

    def test_render_creates_pixmaps(self):
        """Bravura mode renders pixmaps instead of NoteItems."""
        from musiai.notation.NotationScene import NotationScene
        from PySide6.QtWidgets import QGraphicsPixmapItem
        scene = NotationScene()
        piece = self._make_piece(2, 3)
        scene.set_piece(piece)
        pixmaps = [i for i in scene.items()
                   if isinstance(i, QGraphicsPixmapItem)]
        self.assertGreater(len(pixmaps), 0)

    def test_refresh_no_crash(self):
        """Bravura refresh does not crash."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = self._make_piece(1, 2)
        scene.set_piece(piece)
        scene.refresh()
        # Should have items after refresh
        self.assertGreater(len(list(scene.items())), 0)

    def test_playhead(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(self._make_piece())
        scene.update_playhead(2.0)
        self.assertTrue(scene.playhead.isVisible())
        scene.hide_playhead()
        self.assertFalse(scene.playhead.isVisible())

    def test_staff_layout_populated(self):
        """Bravura mode populates _staff_layout for playhead."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(self._make_piece(4, 3))
        self.assertGreater(len(scene._staff_layout), 0)


class TestNoteItem(unittest.TestCase):
    def test_color_updates_on_velocity_change(self):
        from musiai.notation.NoteItem import NoteItem
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        n = Note(60, 0, 1, Expression(velocity=40))
        item = NoteItem(n, 100, 100)
        color_before = item.brush().color()
        n.expression.velocity = 120
        item.update_from_note()
        color_after = item.brush().color()
        self.assertNotEqual(color_before.rgb(), color_after.rgb())

    def test_selection_visual(self):
        from musiai.notation.NoteItem import NoteItem
        from musiai.model.Note import Note
        n = Note(60, 0, 1)
        item = NoteItem(n, 100, 100)
        item.set_selected_visual(True)
        self.assertGreater(item.pen().width(), 0)
        item.set_selected_visual(False)


class TestZigzagItem(unittest.TestCase):
    def test_update_cents(self):
        from musiai.notation.ZigzagItem import ZigzagItem
        z = ZigzagItem(20.0, 50, 50)
        self.assertEqual(z.cents, 20.0)
        z.update_cents(-30.0)
        self.assertEqual(z.cents, -30.0)


class TestCurveItem(unittest.TestCase):
    def test_update_cents(self):
        from musiai.notation.CurveItem import CurveItem
        c = CurveItem(15.0, 50, 50)
        c.update_cents(-10.0)
        self.assertEqual(c.cents, -10.0)


class TestDurationItem(unittest.TestCase):
    def test_visible_when_deviation(self):
        from musiai.notation.DurationItem import DurationItem
        d = DurationItem(1.15, 50, 50)
        self.assertTrue(d.isVisible())

    def test_text_when_standard(self):
        from musiai.notation.DurationItem import DurationItem
        d = DurationItem(1.0, 50, 50)
        self.assertEqual(d.text(), "\u00d71.00")


if __name__ == "__main__":
    unittest.main()
