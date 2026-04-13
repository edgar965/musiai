"""MeasureRenderer - Zeichnet einen einzelnen Takt mit Expression-Visuals."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPen, QColor, QFont, QBrush
from PySide6.QtCore import Qt
from musiai.model.Measure import Measure
from musiai.notation.NoteItem import NoteItem
from musiai.notation.ZigzagItem import ZigzagItem
from musiai.notation.CurveItem import CurveItem
from musiai.notation.DurationItem import DurationItem
from musiai.notation.StaffRenderer import StaffRenderer
from musiai.notation.ClefHelper import ClefHelper, TREBLE, BASS
from musiai.notation.BeamGroup import BeamGroup
from musiai.util.Constants import (
    PIXELS_PER_BEAT, STAFF_LINE_SPACING, COLOR_MEASURE_LINE, NOTE_RADIUS,
)

logger = logging.getLogger("musiai.notation.MeasureRenderer")

HEADER_WIDTH = 58


class MeasureRenderer:
    """Rendert einen einzelnen Takt mit allen Expression-Visuals."""

    REFERENCE_TEMPO = 120.0

    def __init__(self, measure: Measure, x_offset: float, center_y: float,
                 show_clef: bool = False, tempo_bpm: float = 0,
                 velocity: int = 0, effective_tempo: float = 120.0,
                 clef: str = TREBLE):
        self.measure = measure
        self.x_offset = x_offset
        self.center_y = center_y
        self.show_clef = show_clef
        self.tempo_bpm = tempo_bpm
        self.velocity = velocity
        self.effective_tempo = max(20, effective_tempo)
        self.clef = clef
        self._ref_staff_pos = ClefHelper.ref_staff_pos(clef)
        self.note_items: list[NoteItem] = []
        self._items: list[QGraphicsItem] = []

    @property
    def header_width(self) -> float:
        return HEADER_WIDTH if self.show_clef else 0

    @property
    def tempo_scale(self) -> float:
        return self.REFERENCE_TEMPO / self.effective_tempo

    @property
    def pixels_per_beat(self) -> float:
        return PIXELS_PER_BEAT * self.tempo_scale

    @property
    def width(self) -> float:
        return self.measure.duration_beats * self.pixels_per_beat + self.header_width

    def _staff_line_color(self) -> QColor:
        scale = self.tempo_scale
        if abs(scale - 1.0) < 0.05:
            return QColor(40, 40, 50)
        if scale > 1.0:
            t = min((scale - 1.0) / 1.0, 1.0)
            return QColor(int(40 - 20 * t), int(40 + 40 * t), int(50 + 180 * t))
        else:
            t = min((1.0 - scale) / 0.5, 1.0)
            return QColor(int(40 + 160 * t), int(40 + 100 * t), int(50 - 30 * t))

    def render(self, scene: QGraphicsScene) -> None:
        sh = 2 * STAFF_LINE_SPACING
        line_color = self._staff_line_color()

        lines = StaffRenderer.draw_staff_lines(
            scene, self.x_offset, self.width, self.center_y, line_color
        )
        self._items.extend(lines)

        self._add_line(scene, self.x_offset, self.center_y - sh,
                       self.x_offset, self.center_y + sh, 1.5, line_color)

        if self.show_clef:
            self._draw_clef(scene, sh)
            self._draw_time_signature(scene, sh)
            self._draw_tempo(scene, sh)
            self._draw_dynamic(scene, sh)
            sep_x = self.x_offset + self.header_width
            self._add_line(scene, sep_x, self.center_y - sh,
                           sep_x, self.center_y + sh, 0.5,
                           QColor(190, 190, 210))

        self._draw_measure_number(scene, sh)
        self._draw_notes(scene)
        # Beams temporär deaktiviert bis Logik stabil
        # self._draw_beams(scene)

    def _draw_clef(self, scene: QGraphicsScene, sh: float) -> None:
        """Schlüssel zeichnen (Violin- oder Bassschlüssel)."""
        symbol = ClefHelper.clef_symbol(self.clef)
        clef = scene.addText(symbol)
        if self.clef == BASS:
            clef.setFont(QFont("Segoe UI Symbol", 32))
            clef.setPos(self.x_offset, self.center_y - sh - 10)
        else:
            clef.setFont(QFont("Segoe UI Symbol", 42))
            clef.setPos(self.x_offset - 2, self.center_y - sh - 24)
        clef.setDefaultTextColor(QColor(30, 30, 60))
        clef.setZValue(3)
        clef.setData(0, "clef")
        clef.setData(1, self.measure)
        self._items.append(clef)

    def _draw_time_signature(self, scene: QGraphicsScene, sh: float) -> None:
        ts = self.measure.time_signature
        font = QFont("Arial", 15, QFont.Weight.ExtraBold)
        color = QColor(30, 30, 60)
        ts_x = self.x_offset + 34

        num = QGraphicsSimpleTextItem(str(ts.numerator))
        num.setFont(font)
        num.setBrush(QBrush(color))
        num_w = num.boundingRect().width()
        num.setPos(ts_x + (16 - num_w) / 2, self.center_y - sh)
        num.setZValue(3)
        num.setData(0, "time_sig")
        num.setData(1, self.measure)
        scene.addItem(num)
        self._items.append(num)

        den = QGraphicsSimpleTextItem(str(ts.denominator))
        den.setFont(font)
        den.setBrush(QBrush(color))
        den_w = den.boundingRect().width()
        den.setPos(ts_x + (16 - den_w) / 2, self.center_y + 2)
        den.setZValue(3)
        den.setData(0, "time_sig")
        den.setData(1, self.measure)
        scene.addItem(den)
        self._items.append(den)

    def _draw_tempo(self, scene: QGraphicsScene, sh: float) -> None:
        if self.tempo_bpm <= 0:
            return
        from musiai.notation.TempoMarking import TempoMarking
        text = TempoMarking.format_tempo(self.tempo_bpm)
        item = scene.addText(text)
        item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        item.setDefaultTextColor(QColor(20, 120, 20))
        item.setPos(self.x_offset + 2, self.center_y - sh - 38)
        item.setZValue(2)
        item.setData(0, "tempo")
        item.setData(1, self.measure)
        self._items.append(item)

    def _draw_dynamic(self, scene: QGraphicsScene, sh: float) -> None:
        if self.velocity <= 0:
            return
        from musiai.notation.TempoMarking import DynamicMarking
        text = DynamicMarking.format_dynamic(self.velocity)
        item = scene.addText(text)
        item.setFont(QFont("Times New Roman", 10, QFont.Weight.Bold))
        item.setDefaultTextColor(QColor(180, 20, 20))
        item.setPos(self.x_offset + 2, self.center_y + sh + 4)
        item.setZValue(2)
        self._items.append(item)

    def _draw_measure_number(self, scene: QGraphicsScene, sh: float) -> None:
        x = self.x_offset + self.header_width + 2
        item = scene.addText(str(self.measure.number))
        item.setFont(QFont("Arial", 7))
        item.setDefaultTextColor(QColor(160, 160, 180))
        item.setPos(x, self.center_y - sh - 14)
        item.setZValue(1)
        self._items.append(item)

    def _draw_notes(self, scene: QGraphicsScene) -> None:
        ppb = self.pixels_per_beat
        content_start = self.x_offset + self.header_width
        content_end = self.x_offset + self.width

        for note in self.measure.notes:
            # Direkte Beat-Position (wie im Original)
            nx = content_start + note.start_beat * ppb + ppb / 2
            ny = self.pitch_to_y(note.pitch)
            expr = note.expression

            # Dauerlinie (geclippt auf Taktbreite)
            eff_dur = note.duration_beats * expr.duration_deviation
            line_end_x = nx + eff_dur * ppb - NOTE_RADIUS
            line_end_x = min(line_end_x, content_end - 4)
            line_w = max(4, line_end_x - nx)
            dur_line = scene.addLine(nx, ny, nx + line_w, ny,
                                     QPen(QColor(100, 100, 120, 80), 2))
            dur_line.setZValue(5)
            self._items.append(dur_line)

            if abs(expr.duration_deviation - 1.0) >= 0.01:
                d = DurationItem(expr.duration_deviation, nx, ny)
                scene.addItem(d)
                self._items.append(d)

            if abs(expr.cent_offset) > 0.5:
                if expr.glide_type == "curve":
                    c = CurveItem(expr.cent_offset, nx - 15, ny)
                    scene.addItem(c)
                    self._items.append(c)
                else:
                    z = ZigzagItem(expr.cent_offset, nx - 15, ny)
                    scene.addItem(z)
                    self._items.append(z)

            self._draw_ledger_lines(scene, note.pitch, nx, ny)

            ni = NoteItem(note, nx, ny, self.center_y)
            scene.addItem(ni)
            self.note_items.append(ni)

    def _draw_beams(self, scene: QGraphicsScene) -> None:
        """Balken für Achtel/Sechzehntelnoten zeichnen."""
        groups = BeamGroup.find_beam_groups(
            self.measure.notes, self.measure.time_signature
        )
        for group in groups:
            BeamGroup.draw_beams(scene, self.note_items, group)

    def _draw_ledger_lines(self, scene: QGraphicsScene,
                           midi_pitch: int, nx: float, ny: float) -> None:
        """Hilfslinien für Noten über/unter dem 5-Linien-System."""
        staff_pos = ClefHelper.pitch_to_staff_pos(midi_pitch)
        half_sp = STAFF_LINE_SPACING / 2
        ledger_half_w = 10
        color = QColor(80, 80, 90)
        pen = QPen(color, 1.2)

        # Linien-Positionen relativ zum Referenzpunkt
        bottom_line_pos = self._ref_staff_pos - 4
        top_line_pos = self._ref_staff_pos + 4

        if staff_pos <= bottom_line_pos - 2:
            pos = bottom_line_pos - 2
            while pos >= staff_pos:
                y = self.center_y - (pos - self._ref_staff_pos) * half_sp
                line = scene.addLine(nx - ledger_half_w, y,
                                     nx + ledger_half_w, y, pen)
                line.setZValue(6)
                self._items.append(line)
                pos -= 2

        elif staff_pos >= top_line_pos + 2:
            pos = top_line_pos + 2
            while pos <= staff_pos:
                y = self.center_y - (pos - self._ref_staff_pos) * half_sp
                line = scene.addLine(nx - ledger_half_w, y,
                                     nx + ledger_half_w, y, pen)
                line.setZValue(6)
                self._items.append(line)
                pos += 2

    def _add_line(self, scene, x1, y1, x2, y2, width=1.5, color=None):
        c = color or QColor(*COLOR_MEASURE_LINE)
        line = scene.addLine(x1, y1, x2, y2, QPen(c, width))
        line.setZValue(1)
        self._items.append(line)

    def pitch_to_y(self, midi_pitch: int) -> float:
        """MIDI-Pitch → Y-Position (nutzt clef-spezifischen Referenzpunkt)."""
        staff_pos = ClefHelper.pitch_to_staff_pos(midi_pitch)
        return self.center_y - (staff_pos - self._ref_staff_pos) * (STAFF_LINE_SPACING / 2)

    def clear(self, scene: QGraphicsScene) -> None:
        for item in self.note_items:
            scene.removeItem(item)
        for item in self._items:
            scene.removeItem(item)
        self.note_items.clear()
        self._items.clear()
