"""Stem - Notenhals mit Balken-Verbindungen."""

from musiai.ui.midi.WhiteNote import WhiteNote
from musiai.ui.midi import NoteDuration as ND

UP = 1
DOWN = 2
LEFT_SIDE = 1
RIGHT_SIDE = 2


class Stem:
    """Notenhals mit optionaler Balken-Verbindung zu einem Partner."""

    def __init__(self, bottom: WhiteNote, top: WhiteNote,
                 duration: int, direction: int, overlap: bool = False):
        self.top = top
        self.bottom = bottom
        self.duration = duration
        self.direction = direction
        self.overlap = overlap
        self.side = RIGHT_SIDE if direction == UP or overlap else LEFT_SIDE
        self.end = self._calculate_end()
        self.pair: 'Stem | None' = None
        self.width_to_pair = 0
        self.receiver = False

    @property
    def is_beam(self) -> bool:
        return self.receiver or self.pair is not None

    def _calculate_end(self) -> WhiteNote:
        """Stem-Endpunkt: 6 weiße Noten über/unter der äußersten Note."""
        if self.direction == UP:
            w = self.top.add(6)
            if self.duration == ND.SIXTEENTH:
                w = w.add(2)
            elif self.duration == ND.THIRTYSECOND:
                w = w.add(4)
            return w
        else:
            w = self.bottom.add(-6)
            if self.duration == ND.SIXTEENTH:
                w = w.add(-2)
            elif self.duration == ND.THIRTYSECOND:
                w = w.add(-4)
            return w

    def set_pair(self, other: 'Stem', width: int) -> None:
        self.pair = other
        self.width_to_pair = width

    def draw(self, painter, x: int, ytop: int, config: dict,
             top_staff: WhiteNote) -> None:
        """Notenhals zeichnen."""
        from PySide6.QtGui import QPen, QColor

        if self.duration in (ND.WHOLE,):
            return  # Ganze Noten haben keinen Hals

        ls = config.get('line_space', 12)
        nw = config.get('note_width', 15)
        half_space = ls / 2.0

        pen = QPen(QColor(40, 40, 60), 1.2)
        painter.setPen(pen)

        # X-Position des Stems
        if self.side == LEFT_SIDE:
            stem_x = x + 1
        else:
            stem_x = x + nw

        # Y-Positionen
        if self.direction == UP:
            y_note = ytop + top_staff.dist(self.bottom) * half_space
            y_end = ytop + top_staff.dist(self.end) * half_space
        else:
            y_note = ytop + top_staff.dist(self.top) * half_space
            y_end = ytop + top_staff.dist(self.end) * half_space

        painter.drawLine(int(stem_x), int(y_note), int(stem_x), int(y_end))

        # Balken zum Partner
        if self.pair and not self.receiver:
            self._draw_beam(painter, stem_x, y_end, config, ytop, top_staff)

    def _draw_beam(self, painter, x_start: float, y_start: float,
                   config: dict, ytop: int, top_staff: WhiteNote) -> None:
        """Horizontalen Balken zum Partner zeichnen."""
        from PySide6.QtGui import QPen, QColor
        ls = config.get('line_space', 12)
        nw = config.get('note_width', 15)
        half_space = ls / 2.0

        if self.pair.side == LEFT_SIDE:
            x_end_stem = 1
        else:
            x_end_stem = nw
        x_end = self.width_to_pair + x_end_stem

        y_end = ytop + top_staff.dist(self.pair.end) * half_space

        pen = QPen(QColor(40, 40, 60), max(2, ls // 3))
        painter.setPen(pen)

        n_beams = ND.BEAM_COUNT.get(self.duration, 1)
        beam_gap = ls * 0.8
        for b in range(n_beams):
            offset = b * beam_gap
            if self.direction == UP:
                painter.drawLine(int(x_start), int(y_start + offset),
                                 int(x_end), int(y_end + offset))
            else:
                painter.drawLine(int(x_start), int(y_start - offset),
                                 int(x_end), int(y_end - offset))
