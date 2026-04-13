"""Stem - Notenhals mit Balken (portiert von Stem.cs)."""

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
        self.side = RIGHT_SIDE if (direction == UP or overlap) else LEFT_SIDE
        self.end = self._calculate_end()
        self.pair: 'Stem | None' = None
        self.width_to_pair = 0
        self.receiver = False

    @property
    def is_beam(self) -> bool:
        return self.receiver or self.pair is not None

    def _calculate_end(self) -> WhiteNote:
        """Stem endpoint: +/-6 white notes, extra for 16th/32nd."""
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

    def change_direction(self, new_dir: int):
        """Change stem direction (called by beam creation)."""
        self.direction = new_dir
        if new_dir == UP or self.overlap:
            self.side = RIGHT_SIDE
        else:
            self.side = LEFT_SIDE
        self.end = self._calculate_end()

    def set_pair(self, other: 'Stem', width: int):
        self.pair = other
        self.width_to_pair = width

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, painter, x: int, ytop: int, config: dict,
             top_staff: WhiteNote) -> None:
        """Draw the stem (vertical line + flags or beams)."""
        from PySide6.QtGui import QPen, QColor
        if self.duration == ND.WHOLE:
            return

        ls = config.get('line_space', 12)
        nh = ls + 1  # NoteHeight = LineSpace + LineWidth
        nw = 3 * ls // 2
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        self._draw_vertical_line(painter, pen, x, ytop, top_staff, ls, nh, nw)

        if self.duration in (ND.QUARTER, ND.DOTTED_QUARTER,
                             ND.HALF, ND.DOTTED_HALF):
            return
        if self.receiver:
            return

        if self.pair is not None:
            self._draw_horiz_bar_stem(painter, pen, x, ytop, top_staff,
                                      ls, nh, nw)
        else:
            self._draw_curvy_stem(painter, pen, x, ytop, top_staff,
                                  ls, nh, nw)

    def _draw_vertical_line(self, painter, pen, x, ytop, top_staff,
                            ls, nh, nw):
        if self.side == LEFT_SIDE:
            xstart = x + ls // 4 + 1
        else:
            xstart = x + ls // 4 + nw

        if self.direction == UP:
            y1 = ytop + top_staff.dist(self.bottom) * nh // 2 + nh // 4
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            painter.drawLine(xstart, y1, xstart, ystem)
        elif self.direction == DOWN:
            y1 = ytop + top_staff.dist(self.top) * nh // 2 + nh
            if self.side == LEFT_SIDE:
                y1 -= nh // 4
            else:
                y1 -= nh // 2
            ystem = (ytop + top_staff.dist(self.end) * nh // 2 + nh)
            painter.drawLine(xstart, y1, xstart, ystem)

    def _draw_curvy_stem(self, painter, pen, x, ytop, top_staff,
                         ls, nh, nw):
        """Draw curvy flag for single (unbeamed) 8th/16th/32nd notes."""
        from PySide6.QtGui import QPen, QPainterPath
        pen.setWidth(2)
        painter.setPen(pen)

        if self.side == LEFT_SIDE:
            xstart = x + ls // 4 + 1
        else:
            xstart = x + ls // 4 + nw

        flaggable = {ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET,
                     ND.SIXTEENTH, ND.THIRTYSECOND}

        if self.direction == UP:
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            if self.duration in flaggable:
                self._bezier_up(painter, xstart, ystem, ls, nh)
            ystem += nh
            if self.duration in (ND.SIXTEENTH, ND.THIRTYSECOND):
                self._bezier_up(painter, xstart, ystem, ls, nh)
            ystem += nh
            if self.duration == ND.THIRTYSECOND:
                self._bezier_up(painter, xstart, ystem, ls, nh)
        elif self.direction == DOWN:
            ystem = (ytop + top_staff.dist(self.end) * nh // 2 + nh)
            if self.duration in flaggable:
                self._bezier_down(painter, xstart, ystem, ls, nh)
            ystem -= nh
            if self.duration in (ND.SIXTEENTH, ND.THIRTYSECOND):
                self._bezier_down(painter, xstart, ystem, ls, nh)
            ystem -= nh
            if self.duration == ND.THIRTYSECOND:
                self._bezier_down(painter, xstart, ystem, ls, nh)

        pen.setWidth(1)
        painter.setPen(pen)

    @staticmethod
    def _bezier_up(painter, xs, ys, ls, nh):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(xs, ys)
        path.cubicTo(xs, ys + 3 * ls // 2,
                     xs + ls * 2, ys + nh * 2,
                     xs + ls // 2, ys + nh * 3)
        painter.drawPath(path)

    @staticmethod
    def _bezier_down(painter, xs, ys, ls, nh):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(xs, ys)
        path.cubicTo(xs, ys - ls,
                     xs + ls * 2, ys - nh * 2,
                     xs + ls, ys - nh * 2 - ls // 2)
        painter.drawPath(path)

    def _draw_horiz_bar_stem(self, painter, pen, x, ytop, top_staff,
                             ls, nh, nw):
        """Draw horizontal beam to paired stem.

        In Java, drawing is relative to the chord's translated origin.
        Here, x is the absolute position of this chord's note area.
        width_to_pair is the pixel distance between the two chord positions.
        xstart2 is the stem x offset within the paired chord.
        xend = x + width_to_pair + xstart2 to get the absolute position.
        """
        from PySide6.QtCore import Qt
        pen.setWidth(nh // 2)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)

        if self.side == LEFT_SIDE:
            xstart = x + ls // 4 + 1
        else:
            xstart = x + ls // 4 + nw

        if self.pair.side == LEFT_SIDE:
            xstart2 = ls // 4 + 1
        else:
            xstart2 = ls // 4 + nw

        beamable = {ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET,
                    ND.SIXTEENTH, ND.THIRTYSECOND}

        if self.direction == UP:
            xend = x + self.width_to_pair + xstart2
            ystart = ytop + top_staff.dist(self.end) * nh // 2
            yend = ytop + top_staff.dist(self.pair.end) * nh // 2

            if self.duration in beamable:
                painter.drawLine(xstart, ystart, xend, yend)
            ystart += nh
            yend += nh

            # Dotted eighth partial beam
            if self.duration == ND.DOTTED_EIGHTH:
                px = xend - nh
                slope = (yend - ystart) * 1.0 / max(xend - xstart, 1)
                py = int(slope * (px - xend) + yend)
                painter.drawLine(px, py, xend, yend)

            if self.duration in (ND.SIXTEENTH, ND.THIRTYSECOND):
                painter.drawLine(xstart, ystart, xend, yend)
            ystart += nh
            yend += nh
            if self.duration == ND.THIRTYSECOND:
                painter.drawLine(xstart, ystart, xend, yend)
        else:
            xend = x + self.width_to_pair + xstart2
            ystart = ytop + top_staff.dist(self.end) * nh // 2 + nh
            yend = ytop + top_staff.dist(self.pair.end) * nh // 2 + nh

            if self.duration in beamable:
                painter.drawLine(xstart, ystart, xend, yend)
            ystart -= nh
            yend -= nh

            if self.duration == ND.DOTTED_EIGHTH:
                px = xend - nh
                slope = (yend - ystart) * 1.0 / max(xend - xstart, 1)
                py = int(slope * (px - xend) + yend)
                painter.drawLine(px, py, xend, yend)

            if self.duration in (ND.SIXTEENTH, ND.THIRTYSECOND):
                painter.drawLine(xstart, ystart, xend, yend)
            ystart -= nh
            yend -= nh
            if self.duration == ND.THIRTYSECOND:
                painter.drawLine(xstart, ystart, xend, yend)

        pen.setWidth(1)
        painter.setPen(pen)

    def __repr__(self):
        return (f"Stem(dur={self.duration} dir={self.direction} "
                f"top={self.top} bot={self.bottom} end={self.end} "
                f"overlap={self.overlap} side={self.side} "
                f"w2p={self.width_to_pair} recv={self.receiver})")
