"""MeasureRenderer - Zeichnet einen einzelnen Takt mit Expression-Visuals."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsRectItem
from PySide6.QtGui import QPen, QColor, QFont, QBrush
from PySide6.QtCore import Qt
from musiai.model.Measure import Measure
from musiai.notation.NoteItem import NoteItem
from musiai.notation.ZigzagItem import ZigzagItem
from musiai.notation.CurveItem import CurveItem
from musiai.notation.DurationItem import DurationItem
from musiai.notation.StaffRenderer import StaffRenderer
from musiai.notation.ClefItem import ClefItem
from musiai.notation.TimeSignatureItem import TimeSignatureItem
from musiai.util.Constants import (
    PIXELS_PER_BEAT, STAFF_LINE_SPACING, COLOR_MEASURE_LINE, MIDI_MIDDLE_C,
)

logger = logging.getLogger("musiai.notation.MeasureRenderer")

CLEF_WIDTH = 24
TS_WIDTH = 24
HEADER_GAP = 8


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
        return CLEF_WIDTH + TS_WIDTH + HEADER_GAP * 2

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
        bar = scene.addLine(
            self.x_offset, self.center_y - staff_half,
            self.x_offset, self.center_y + staff_half,
            QPen(QColor(*COLOR_MEASURE_LINE), 1.5),
        )
        bar.setZValue(1)
        self._items.append(bar)

        # Header
        if self.show_clef:
            self._draw_header(scene, staff_half)

        # Taktnummer
        self._draw_measure_number(scene, staff_half)

        # Noten
        self._draw_notes(scene)

    def _draw_header(self, scene: QGraphicsScene, staff_half: float) -> None:
        """Schlüssel + Taktart + Tempo/Dynamik."""
        # Violinschlüssel
        clef_x = self.x_offset + HEADER_GAP
        clef = ClefItem(clef_x, self.center_y, staff_half)
        scene.addItem(clef)
        self._items.append(clef)

        # Taktart
        ts_x = self.x_offset + HEADER_GAP + CLEF_WIDTH + HEADER_GAP
        ts_item = TimeSignatureItem(
            self.measure.time_signature, ts_x, self.center_y, staff_half
        )
        scene.addItem(ts_item)
        self._items.append(ts_item)

        # Trennstrich nach Header
        sep_x = self.x_offset + self.header_width
        sep = scene.addLine(
            sep_x, self.center_y - staff_half,
            sep_x, self.center_y + staff_half,
            QPen(QColor(180, 180, 200), 0.5),
        )
        sep.setZValue(1)
        self._items.append(sep)

        # Tempo (über dem System)
        if self.tempo_bpm > 0:
            from musiai.notation.TempoMarking import TempoMarking
            text = TempoMarking.format_tempo(self.tempo_bpm)
            tempo = scene.addText(text)
            tempo.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            tempo.setDefaultTextColor(QColor(30, 110, 30))
            tempo.setPos(self.x_offset + self.header_width + 4,
                        self.center_y - staff_half - 36)
            tempo.setZValue(2)
            self._items.append(tempo)

        # Dynamik (unter dem System)
        if self.velocity > 0:
            from musiai.notation.TempoMarking import DynamicMarking
            text = DynamicMarking.format_dynamic(self.velocity)
            dyn = scene.addText(text)
            dyn.setFont(QFont("Times New Roman", 10, QFont.Weight.Bold))
            dyn.setDefaultTextColor(QColor(180, 30, 30))
            dyn.setPos(self.x_offset + self.header_width + 4,
                      self.center_y + staff_half + 4)
            dyn.setZValue(2)
            self._items.append(dyn)

    def _draw_measure_number(self, scene: QGraphicsScene, staff_half: float) -> None:
        x = self.x_offset + self.header_width + 2
        num = scene.addText(str(self.measure.number))
        num.setFont(QFont("Arial", 7))
        num.setDefaultTextColor(QColor(160, 160, 180))
        num.setPos(x, self.center_y - staff_half - 14)
        num.setZValue(1)
        self._items.append(num)

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
