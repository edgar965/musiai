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
        """Stem-Endpunkt berechnen: 6 weiße Noten über/unter."""
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

    def change_direction(self, new_dir: int) -> None:
        self.direction = new_dir
        self.side = RIGHT_SIDE if new_dir == UP or self.overlap else LEFT_SIDE
        self.end = self._calculate_end()

    def draw(self, painter, x: int, ytop: int, config: dict,
             top_staff: WhiteNote) -> None:
        """Notenhals zeichnen."""
        from PySide6.QtGui import QPen, QColor
        nh = config.get('note_height', 8)
        nw = config.get('note_width', 10)
        ls = config.get('line_space', 7)

        if self.duration in (ND.WHOLE, ND.DOTTED_HALF, ND.HALF):
            return  # Keine Hälse für ganze/halbe Noten

        pen = QPen(QColor(40, 40, 60), 1.2)
        painter.setPen(pen)

        # X-Position
        if self.side == LEFT_SIDE:
            stem_x = x + ls // 4 + 1
        else:
            stem_x = x + ls // 4 + nw

        # Y-Positionen
        if self.direction == UP:
            y_start = ytop + top_staff.dist(self.bottom) * nh // 2 + nh // 4
            y_end = ytop + top_staff.dist(self.end) * nh // 2
        else:
            y_start = ytop + top_staff.dist(self.top) * nh // 2 + nh
            y_end = ytop + top_staff.dist(self.end) * nh // 2 + nh

        painter.drawLine(stem_x, y_start, stem_x, y_end)

        # Balken zeichnen wenn gepaart
        if self.pair and not self.receiver:
            self._draw_beam(painter, stem_x, y_end, config, ytop, top_staff)

    def _draw_beam(self, painter, x_start: int, y_start: int,
                   config: dict, ytop: int, top_staff: WhiteNote) -> None:
        """Horizontalen Balken zum Partner zeichnen."""
        from PySide6.QtGui import QPen, QColor
        nh = config.get('note_height', 8)
        nw = config.get('note_width', 10)
        ls = config.get('line_space', 7)

        if self.pair.side == LEFT_SIDE:
            x_end_stem = ls // 4 + 1
        else:
            x_end_stem = ls // 4 + nw
        x_end = self.width_to_pair + x_end_stem

        y_end = ytop + top_staff.dist(self.pair.end) * nh // 2
        if self.direction == DOWN:
            y_end += nh

        pen = QPen(QColor(40, 40, 60), nh // 2)
        painter.setPen(pen)

        # 1. Balken (Achtel+)
        n_beams = ND.BEAM_COUNT.get(self.duration, 1)
        for b in range(n_beams):
            offset = b * nh
            if self.direction == UP:
                painter.drawLine(x_start, y_start + offset,
                                 x_end, y_end + offset)
            else:
                painter.drawLine(x_start, y_start - offset,
                                 x_end, y_end - offset)
