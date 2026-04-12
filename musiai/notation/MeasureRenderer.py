"""MeasureRenderer - Zeichnet einen einzelnen Takt mit Expression-Visuals."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QPen, QColor, QFont, QPainterPath
from PySide6.QtCore import Qt
from musiai.model.Measure import Measure
from musiai.notation.NoteItem import NoteItem
from musiai.notation.ZigzagItem import ZigzagItem
from musiai.notation.CurveItem import CurveItem
from musiai.notation.DurationItem import DurationItem
from musiai.notation.StaffRenderer import StaffRenderer
from musiai.util.Constants import (
    PIXELS_PER_BEAT, STAFF_LINE_SPACING, COLOR_MEASURE_LINE, MIDI_MIDDLE_C,
)

logger = logging.getLogger("musiai.notation.MeasureRenderer")

CLEF_WIDTH = 28
TS_WIDTH = 22
HEADER_PADDING = 8


class MeasureRenderer:
    """Rendert einen einzelnen Takt mit allen Expression-Visuals."""

    def __init__(self, measure: Measure, x_offset: float, center_y: float,
                 show_clef: bool = False, tempo_bpm: float = 0, velocity: int = 0):
        self.measure = measure
        self.x_offset = x_offset
        self.center_y = center_y
        self.show_clef = show_clef
        self.tempo_bpm = tempo_bpm
        self.velocity = velocity
        self.note_items: list[NoteItem] = []
        self._items: list[QGraphicsItem] = []

    @property
    def header_width(self) -> float:
        if not self.show_clef:
            return 0
        return CLEF_WIDTH + TS_WIDTH + HEADER_PADDING

    @property
    def width(self) -> float:
        return self.measure.duration_beats * PIXELS_PER_BEAT + self.header_width

    def render(self, scene: QGraphicsScene) -> None:
        staff_half = 2 * STAFF_LINE_SPACING

        # Notenlinien
        lines = StaffRenderer.draw_staff_lines(
            scene, self.x_offset, self.width, self.center_y
        )
        self._items.extend(lines)

        # Taktstrich links
        pen = QPen(QColor(*COLOR_MEASURE_LINE), 1.5)
        bar = scene.addLine(
            self.x_offset, self.center_y - staff_half,
            self.x_offset, self.center_y + staff_half, pen,
        )
        bar.setZValue(1)
        self._items.append(bar)

        # Header (Schlüssel + Taktart + Tempo/Dynamik)
        if self.show_clef:
            self._draw_clef(scene, staff_half)
            self._draw_time_signature(scene, staff_half)
            self._draw_tempo_marking(scene, staff_half)
            self._draw_dynamic_marking(scene, staff_half)

        # Taktnummer (klein, über dem Takt)
        self._draw_measure_number(scene, staff_half)

        # Noten
        self._draw_notes(scene)

    def _draw_clef(self, scene: QGraphicsScene, staff_half: float) -> None:
        """Violinschlüssel - sauber positioniert."""
        clef = scene.addText("𝄞")
        clef.setFont(QFont("Segoe UI Symbol", 24))
        clef.setDefaultTextColor(QColor(40, 40, 60))
        # Vertikal zentriert auf den Notenlinien
        clef.setPos(self.x_offset + 2, self.center_y - 26)
        clef.setZValue(2)
        self._items.append(clef)

    def _draw_time_signature(self, scene: QGraphicsScene, staff_half: float) -> None:
        """Taktart rechts vom Schlüssel, Zähler und Nenner gestapelt."""
        ts = self.measure.time_signature
        ts_font = QFont("Arial", 13, QFont.Weight.Bold)
        ts_x = self.x_offset + CLEF_WIDTH + 2

        # Zähler (auf der 2. Notenlinie von oben)
        num = scene.addText(str(ts.numerator))
        num.setFont(ts_font)
        num.setDefaultTextColor(QColor(40, 40, 60))
        num.setPos(ts_x, self.center_y - staff_half - 2)
        num.setZValue(2)
        self._items.append(num)

        # Nenner (auf der 4. Notenlinie von oben)
        den = scene.addText(str(ts.denominator))
        den.setFont(ts_font)
        den.setDefaultTextColor(QColor(40, 40, 60))
        den.setPos(ts_x, self.center_y + 2)
        den.setZValue(2)
        self._items.append(den)

    def _draw_tempo_marking(self, scene: QGraphicsScene, staff_half: float) -> None:
        """Tempo über dem System: ♩= 120 (Allegro)."""
        if self.tempo_bpm <= 0:
            return
        from musiai.notation.TempoMarking import TempoMarking
        text = TempoMarking.format_tempo(self.tempo_bpm)

        tempo_item = scene.addText(text)
        tempo_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        tempo_item.setDefaultTextColor(QColor(30, 100, 30))
        tempo_item.setPos(self.x_offset + 2, self.center_y - staff_half - 38)
        tempo_item.setZValue(2)
        self._items.append(tempo_item)

    def _draw_dynamic_marking(self, scene: QGraphicsScene, staff_half: float) -> None:
        """Dynamik unter dem System: f (forte)."""
        if self.velocity <= 0:
            return
        from musiai.notation.TempoMarking import DynamicMarking
        text = DynamicMarking.format_dynamic(self.velocity)

        dyn_item = scene.addText(text)
        dyn_item.setFont(QFont("Times New Roman", 10, QFont.Weight.Bold))
        dyn_item.setDefaultTextColor(QColor(180, 40, 40))
        dyn_item.setPos(self.x_offset + 2, self.center_y + staff_half + 4)
        dyn_item.setZValue(2)
        self._items.append(dyn_item)

    def _draw_measure_number(self, scene: QGraphicsScene, staff_half: float) -> None:
        num_text = scene.addText(str(self.measure.number))
        num_text.setFont(QFont("Arial", 7))
        num_text.setDefaultTextColor(QColor(150, 150, 170))
        x = self.x_offset + self.header_width + 2
        num_text.setPos(x, self.center_y - staff_half - 16)
        num_text.setZValue(1)
        self._items.append(num_text)

    def _draw_notes(self, scene: QGraphicsScene) -> None:
        for note in self.measure.notes:
            nx = (self.x_offset + self.header_width +
                  note.start_beat * PIXELS_PER_BEAT + PIXELS_PER_BEAT / 2)
            ny = self.pitch_to_y(note.pitch)
            expr = note.expression

            if abs(expr.duration_deviation - 1.0) >= 0.01:
                dur_item = DurationItem(expr.duration_deviation, nx, ny)
                scene.addItem(dur_item)
                self._items.append(dur_item)

            if abs(expr.cent_offset) > 0.5:
                if expr.glide_type == "curve":
                    item = CurveItem(expr.cent_offset, nx - 15, ny)
                else:
                    item = ZigzagItem(expr.cent_offset, nx - 15, ny)
                scene.addItem(item)
                self._items.append(item)

            note_item = NoteItem(note, nx, ny)
            scene.addItem(note_item)
            self.note_items.append(note_item)

    def pitch_to_y(self, midi_pitch: int) -> float:
        return self.center_y - (midi_pitch - MIDI_MIDDLE_C) * (STAFF_LINE_SPACING / 2)

    def clear(self, scene: QGraphicsScene) -> None:
        for item in self.note_items:
            scene.removeItem(item)
        for item in self._items:
            scene.removeItem(item)
        self.note_items.clear()
        self._items.clear()
