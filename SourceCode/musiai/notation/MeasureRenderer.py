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
                 clef: str = TREBLE, show_chords: bool = False,
                 use_bravura: bool = False):
        self.measure = measure
        self.x_offset = x_offset
        self.center_y = center_y
        self.show_clef = show_clef
        self.tempo_bpm = tempo_bpm
        self.velocity = velocity
        self.effective_tempo = max(20, effective_tempo)
        self.clef = clef
        self.show_chords = show_chords
        self._use_bravura = use_bravura
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

        # Taktstrich immer schwarz (nicht tempo-gefärbt)
        bar_color = QColor(40, 40, 50)
        self._add_line(scene, self.x_offset, self.center_y - sh,
                       self.x_offset, self.center_y + sh, 1.0, bar_color)

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
        self._draw_rests(scene)
        self._draw_ties(scene)
        if self.show_chords:
            self._draw_chords(scene, sh)
        # Beams temporär deaktiviert bis Logik stabil
        # self._draw_beams(scene)

    def _draw_clef(self, scene: QGraphicsScene, sh: float) -> None:
        """Schlüssel zeichnen (Violin- oder Bassschlüssel)."""
        if self._use_bravura:
            from musiai.ui.midi.BravuraGlyphs import (
                ensure_font, FONT_NAME, TREBLE_CLEF, BASS_CLEF,
            )
            ensure_font()
            glyph = BASS_CLEF if self.clef == BASS else TREBLE_CLEF
            clef_item = QGraphicsSimpleTextItem(glyph)
            # Bravura clef: Größe proportional, Position auf der richtigen Linie
            clef_size = int(STAFF_LINE_SPACING * 2.2)
            clef_item.setFont(QFont(FONT_NAME, clef_size))
            clef_item.setBrush(QBrush(QColor(30, 30, 60)))
            if self.clef == BASS:
                # Bass-Clef Baseline auf der 4. Linie (F)
                clef_item.setPos(self.x_offset + 2,
                                 self.center_y - STAFF_LINE_SPACING * 0.5)
            else:
                # Treble-Clef Baseline auf der 2. Linie (G)
                clef_item.setPos(self.x_offset - 2,
                                 self.center_y + STAFF_LINE_SPACING * 1.5)
            clef_item.setZValue(3)
            clef_item.setData(0, "clef")
            clef_item.setData(1, self.measure)
            scene.addItem(clef_item)
            self._items.append(clef_item)
        else:
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
        ts_x = self.x_offset + 34
        color = QColor(30, 30, 60)

        if self._use_bravura:
            from musiai.ui.midi.BravuraGlyphs import (
                ensure_font, FONT_NAME, TIME_DIGITS,
            )
            ensure_font()
            bravura_font = QFont(FONT_NAME, int(STAFF_LINE_SPACING * 1.8))

            def _time_glyphs(value: int) -> str:
                return "".join(TIME_DIGITS[int(d)] for d in str(value))

            num = QGraphicsSimpleTextItem(_time_glyphs(ts.numerator))
            num.setFont(bravura_font)
            num.setBrush(QBrush(color))
            num_w = num.boundingRect().width()
            num.setPos(ts_x + (16 - num_w) / 2,
                       self.center_y - sh - STAFF_LINE_SPACING * 0.3)
            num.setZValue(3)
            num.setData(0, "time_sig")
            num.setData(1, self.measure)
            scene.addItem(num)
            self._items.append(num)

            den = QGraphicsSimpleTextItem(_time_glyphs(ts.denominator))
            den.setFont(bravura_font)
            den.setBrush(QBrush(color))
            den_w = den.boundingRect().width()
            den.setPos(ts_x + (16 - den_w) / 2,
                       self.center_y + STAFF_LINE_SPACING * 0.2)
            den.setZValue(3)
            den.setData(0, "time_sig")
            den.setData(1, self.measure)
            scene.addItem(den)
            self._items.append(den)
        else:
            font = QFont("Arial", 15, QFont.Weight.ExtraBold)
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

            # Dauerlinie (dezent, nur wenn Expression aktiv)
            eff_dur = note.duration_beats * expr.duration_deviation
            line_end_x = nx + eff_dur * ppb - NOTE_RADIUS * 2
            line_end_x = min(line_end_x, content_end - 8)
            line_w = max(0, line_end_x - nx)
            if line_w > NOTE_RADIUS * 2:
                dur_line = scene.addLine(
                    nx + NOTE_RADIUS, ny, nx + line_w, ny,
                    QPen(QColor(160, 160, 180, 60), 1))
                dur_line.setZValue(3)
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

            # Vorzeichen (♯/♭) für schwarze Tasten
            pc = note.pitch % 12
            if pc in (1, 3, 6, 8, 10):  # C♯, D♯, F♯, G♯, A♯
                if self._use_bravura:
                    from musiai.ui.midi.BravuraGlyphs import (
                        ensure_font, FONT_NAME, SHARP,
                    )
                    from musiai.notation.ColorScheme import ColorScheme
                    ensure_font()
                    acc_color = ColorScheme.velocity_to_color(
                        note.expression.velocity)
                    accid = QGraphicsSimpleTextItem(SHARP)
                    accid.setFont(QFont(FONT_NAME, int(STAFF_LINE_SPACING * 1.2)))
                    accid.setBrush(QBrush(acc_color))
                    accid.setPos(nx - NOTE_RADIUS - 10, ny - 6)
                else:
                    accid = QGraphicsSimpleTextItem("♯")
                    accid.setFont(QFont("Arial", 9))
                    accid.setBrush(QBrush(QColor(40, 40, 60)))
                    accid.setPos(nx - NOTE_RADIUS - 8, ny - 6)
                accid.setZValue(11)
                scene.addItem(accid)
                self._items.append(accid)

            # Punkt für punktierte Noten
            dotted_durs = {1.5, 0.75, 3.0, 0.375}
            if any(abs(note.duration_beats - d) < 0.02 for d in dotted_durs):
                if self._use_bravura:
                    from musiai.ui.midi.BravuraGlyphs import (
                        ensure_font, FONT_NAME, DOT,
                    )
                    from musiai.notation.ColorScheme import ColorScheme
                    ensure_font()
                    dot_color = ColorScheme.velocity_to_color(
                        note.expression.velocity)
                    dot = QGraphicsSimpleTextItem(DOT)
                    dot.setFont(QFont(FONT_NAME, int(STAFF_LINE_SPACING * 1.0)))
                    dot.setBrush(QBrush(dot_color))
                    dot.setPos(nx + NOTE_RADIUS + 2, ny - 4)
                else:
                    dot = QGraphicsSimpleTextItem(".")
                    dot.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                    dot.setBrush(QBrush(QColor(40, 40, 60)))
                    dot.setPos(nx + NOTE_RADIUS + 1, ny - 8)
                dot.setZValue(11)
                scene.addItem(dot)
                self._items.append(dot)

            ni = NoteItem(note, nx, ny, self.center_y,
                          use_bravura=self._use_bravura)
            scene.addItem(ni)
            self.note_items.append(ni)

    def _draw_ties(self, scene: QGraphicsScene) -> None:
        """Draw tie curves between consecutive same-pitch notes."""
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath

        for i, ni in enumerate(self.note_items):
            for j in range(i + 1, len(self.note_items)):
                nj = self.note_items[j]
                if ni.note.pitch == nj.note.pitch:
                    end_beat = ni.note.start_beat + ni.note.duration_beats
                    if abs(end_beat - nj.note.start_beat) < 0.05:
                        self._draw_tie_curve(scene, ni, nj)
                    break

    def _draw_tie_curve(self, scene: QGraphicsScene,
                        note_item_a, note_item_b) -> None:
        """Draw a bezier tie arc between two NoteItems."""
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath

        x1 = note_item_a.x() + NOTE_RADIUS
        x2 = note_item_b.x() - NOTE_RADIUS
        y = note_item_a.y()

        if y > self.center_y:
            curve_offset = STAFF_LINE_SPACING
        else:
            curve_offset = -STAFF_LINE_SPACING

        mid_x = (x1 + x2) / 2
        path = QPainterPath()
        path.moveTo(x1, y)
        path.cubicTo(mid_x, y + curve_offset,
                     mid_x, y + curve_offset, x2, y)

        item = QGraphicsPathItem(path)
        item.setPen(QPen(QColor(40, 40, 60), 1.2))
        item.setZValue(9)
        scene.addItem(item)
        self._items.append(item)

    def _draw_rests(self, scene: QGraphicsScene) -> None:
        """Draw rest symbols in gaps between notes."""
        ppb = self.pixels_per_beat
        content_start = self.x_offset + self.header_width
        ts = self.measure.time_signature
        measure_dur = ts.beats_per_measure()

        # Build sorted list of occupied intervals
        intervals = []
        for note in self.measure.notes:
            intervals.append((note.start_beat, note.end_beat))
        intervals.sort()

        # Find gaps
        gaps = []
        covered_end = 0.0
        for start, end in intervals:
            if start > covered_end + 0.05:
                gaps.append((covered_end, start))
            covered_end = max(covered_end, end)
        if covered_end + 0.05 < measure_dur:
            gaps.append((covered_end, measure_dur))

        for gap_start, gap_end in gaps:
            gap_dur = gap_end - gap_start
            if gap_dur < 0.1:
                continue
            rest_parts = self._split_rest_duration(gap_dur)
            beat = gap_start
            for dur in rest_parts:
                rx = content_start + beat * ppb + dur * ppb / 2
                self._draw_rest_symbol(scene, rx, dur)
                beat += dur

    def _split_rest_duration(self, dur: float) -> list[float]:
        """Split a rest duration into standard note values."""
        parts = []
        remaining = dur
        standard = [4.0, 2.0, 1.0, 0.5, 0.25]
        for s in standard:
            while remaining >= s - 0.02:
                parts.append(s)
                remaining -= s
        if remaining > 0.1:
            parts.append(remaining)
        return parts

    def _draw_rest_symbol(self, scene: QGraphicsScene,
                          x: float, dur_beats: float) -> None:
        """Draw a single rest glyph at position x."""
        if self._use_bravura:
            from musiai.ui.midi.BravuraGlyphs import (
                ensure_font, FONT_NAME,
                REST_WHOLE, REST_HALF, REST_QUARTER,
                REST_8TH, REST_16TH, REST_32ND,
            )
            ensure_font()
            glyph_map = {
                4.0: REST_WHOLE, 2.0: REST_HALF, 1.0: REST_QUARTER,
                0.5: REST_8TH, 0.25: REST_16TH, 0.125: REST_32ND,
            }
            glyph = None
            for threshold, g in glyph_map.items():
                if abs(dur_beats - threshold) < 0.05:
                    glyph = g
                    break
            if glyph is None:
                glyph = REST_QUARTER
            item = QGraphicsSimpleTextItem(glyph)
            rest_size = int(STAFF_LINE_SPACING * 1.8)
            item.setFont(QFont(FONT_NAME, rest_size))
            item.setBrush(QBrush(QColor(100, 100, 120)))
            bw = item.boundingRect().width()
            item.setPos(x - bw / 2, self.center_y - STAFF_LINE_SPACING * 0.8)
        else:
            text_map = {
                4.0: "\U0001D13B", 2.0: "\U0001D13C",
                1.0: "\U0001D13D", 0.5: "\U0001D13E",
                0.25: "\U0001D13F", 0.125: "\U0001D140",
            }
            text = None
            for threshold, t in text_map.items():
                if abs(dur_beats - threshold) < 0.05:
                    text = t
                    break
            if text is None:
                text = "\U0001D13D"
            item = QGraphicsSimpleTextItem(text)
            item.setFont(QFont("Segoe UI Symbol", 18))
            item.setBrush(QBrush(QColor(100, 100, 120)))
            bw = item.boundingRect().width()
            item.setPos(x - bw / 2, self.center_y - 14)
        item.setZValue(5)
        scene.addItem(item)
        self._items.append(item)

    def _draw_chords(self, scene: QGraphicsScene, sh: float) -> None:
        """Akkordnamen unter dem Notensystem zeichnen."""
        from musiai.notation.ChordDetector import ChordDetector
        from PySide6.QtCore import QSettings
        chords = ChordDetector.detect_for_measure(self.measure.notes)
        if not chords:
            return
        ppb = self.pixels_per_beat
        content_start = self.x_offset + self.header_width
        chord_y = self.center_y + sh + 16

        settings = QSettings("MusiAI", "MusiAI")
        family = settings.value("ui/chord_font_family", "Arial")
        size = int(settings.value("ui/chord_font_size", 11))
        bold = settings.value("ui/chord_font_bold", "true") == "true"
        italic = settings.value("ui/chord_font_italic", "false") == "true"
        color_hex = settings.value("ui/chord_font_color", "#0044AA")

        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        font = QFont(family, size, weight)
        font.setItalic(italic)
        color = QColor(color_hex)

        for beat, name in chords:
            cx = content_start + beat * ppb + ppb / 2
            label = QGraphicsSimpleTextItem(name)
            label.setFont(font)
            label.setBrush(QBrush(color))
            label.setPos(cx - label.boundingRect().width() / 2, chord_y)
            label.setZValue(4)
            scene.addItem(label)
            self._items.append(label)

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
