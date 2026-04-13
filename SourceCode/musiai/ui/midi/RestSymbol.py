"""RestSymbol - Pausenzeichen (portiert von RestSymbol.cs)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi import NoteDuration as ND


class RestSymbol(MusicSymbol):
    """Zeichnet Pausen (Ganze, Halbe, Viertel, Achtel)."""

    def __init__(self, start_time: int, duration: int):
        super().__init__(start_time)
        self.duration = duration
        self._width = self.min_width

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        return 2 * SC._nh + SC._nh // 2

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC._nh
        nw = SC._nw
        ls = SC._ls

        # Align rest to the right, then offset by NoteHeight/2
        offset = self.width - self.min_width + nh // 2
        rx = x + offset

        use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False
        if use_bravura:
            self._draw_bravura(painter, rx, ytop, nh)
            return

        if self.duration == ND.WHOLE:
            self._draw_whole(painter, rx, ytop, nh, nw)
        elif self.duration == ND.HALF:
            self._draw_half(painter, rx, ytop, nh, nw)
        elif self.duration == ND.QUARTER:
            self._draw_quarter(painter, rx, ytop, nh, nw, ls)
        elif self.duration == ND.EIGHTH:
            self._draw_eighth(painter, rx, ytop, nh, nw, ls)

    def _draw_bravura(self, painter, x, ytop, nh):
        """Draw rest using Bravura SMuFL glyph."""
        from PySide6.QtGui import QFont, QPen, QColor
        from musiai.ui.midi import BravuraGlyphs as BG

        glyph_map = {
            ND.WHOLE: BG.REST_WHOLE,
            ND.HALF: BG.REST_HALF,
            ND.QUARTER: BG.REST_QUARTER,
            ND.EIGHTH: BG.REST_8TH,
        }
        glyph = glyph_map.get(self.duration)
        if glyph is None:
            return

        size = max(14, int(ls * 3.5))
        painter.setFont(QFont(BG.FONT_NAME, size))
        painter.setPen(QPen(QColor(0, 0, 0)))
        # Position rest vertically centered on the staff
        painter.drawText(x, ytop + nh * 2, glyph)

    def _draw_whole(self, painter, x, ytop, nh, nw):
        """Rectangle below middle line."""
        from PySide6.QtGui import QColor
        y = ytop + nh
        painter.fillRect(x, y, nw, nh // 2, QColor(0, 0, 0))

    def _draw_half(self, painter, x, ytop, nh, nw):
        """Rectangle above middle line."""
        from PySide6.QtGui import QColor
        y = ytop + nh + nh // 2
        painter.fillRect(x, y, nw, nh // 2, QColor(0, 0, 0))

    def _draw_quarter(self, painter, x, ytop, nh, nw, ls):
        """Quarter rest: complex shape with diagonals."""
        from PySide6.QtGui import QPen, QColor
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        y = ytop + nh // 2
        xp = x + 2
        xend = xp + 2 * nh // 3

        # First diagonal
        painter.drawLine(xp, y, xend - 1, y + nh - 1)

        # Thick middle line
        pen.setWidth(max(1, ls // 2))
        painter.setPen(pen)
        y2 = ytop + nh + 1
        painter.drawLine(xend - 2, y2, xp, y2 + nh)

        # Third line
        pen.setWidth(1)
        painter.setPen(pen)
        y3 = ytop + nh * 2 - 1
        painter.drawLine(x, y3, xend + 2, y3 + nh)

        # Thick horizontal
        pen.setWidth(max(1, ls // 2))
        painter.setPen(pen)
        if nh == 6:
            painter.drawLine(xend, y3 + 1 + 3 * nh // 4,
                             xp // 2, y3 + 1 + 3 * nh // 4)
        else:
            painter.drawLine(xend, y3 + 3 * nh // 4,
                             xp // 2, y3 + 3 * nh // 4)

        # Bottom diagonal
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x, y3 + 2 * nh // 3 + 1,
                         xend - 1, y3 + 3 * nh // 2)

    def _draw_eighth(self, painter, x, ytop, nh, nw, ls):
        """Eighth rest: ellipse with diagonal stem."""
        from PySide6.QtGui import QPen, QColor, QBrush
        y = ytop + nh - 1
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(x, y + 1, ls - 1, ls - 1)
        painter.drawLine((ls - 2) // 2 + x, y + ls - 1,
                         3 * ls // 2 + x, y + ls // 2)
        painter.drawLine(3 * ls // 2 + x, y + ls // 2,
                         3 * ls // 4 + x, y + nh * 2)

    def __repr__(self):
        return (f"RestSymbol(start={self.start_time}, "
                f"dur={ND.name(self.duration)}, w={self.width})")
