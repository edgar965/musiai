"""AccidSymbol - Vorzeichen (Sharp, Flat, Natural) portiert von AccidSymbol.cs."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.WhiteNote import WhiteNote

NONE = 0
SHARP = 1
FLAT = 2
NATURAL = 3


class AccidSymbol(MusicSymbol):
    """Zeichnet ein Vorzeichen neben einer Note."""

    def __init__(self, accid: int, whitenote: WhiteNote, clef: int):
        super().__init__(-1)
        self.accid = accid
        self.whitenote = whitenote
        self.clef = clef
        self._width = self.min_width

    @property
    def note(self) -> WhiteNote:
        return self.whitenote

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        return 3 * SC._nh // 2

    @property
    def above_staff(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        dist = WhiteNote.top(self.clef).dist(self.whitenote) * SC._nh // 2
        if self.accid in (SHARP, NATURAL):
            dist -= SC._nh
        elif self.accid == FLAT:
            dist -= 3 * SC._nh // 2
        return -dist if dist < 0 else 0

    @property
    def below_staff(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        dist = (WhiteNote.bottom(self.clef).dist(self.whitenote) * SC._nh // 2
                + SC._nh)
        if self.accid in (SHARP, NATURAL):
            dist += SC._nh
        return dist if dist > 0 else 0

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC._nh
        nw = SC._nw
        ls = SC._ls
        lw = SC._lw

        # Align to right
        offset = self.width - self.min_width
        ynote = ytop + WhiteNote.top(self.clef).dist(self.whitenote) * nh // 2

        ax = x + offset

        use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False
        if use_bravura:
            self._draw_bravura(painter, ax, ynote, nh)
        elif self.accid == SHARP:
            self._draw_sharp(painter, ax, ynote, nh, ls, lw)
        elif self.accid == FLAT:
            self._draw_flat(painter, ax, ynote, nh, ls, lw)
        elif self.accid == NATURAL:
            self._draw_natural(painter, ax, ynote, nh, ls, lw)

    def _draw_bravura(self, painter, x, ynote, nh):
        """Draw accidental using Bravura SMuFL glyph."""
        from PySide6.QtGui import QFont, QPen, QColor
        from musiai.ui.midi import BravuraGlyphs as BG

        glyph_map = {SHARP: BG.SHARP, FLAT: BG.FLAT, NATURAL: BG.NATURAL}
        glyph = glyph_map.get(self.accid)
        if glyph is None:
            return

        size = max(6, int(nh * 1.5))
        painter.setFont(QFont(BG.FONT_NAME, size))
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawText(x, ynote + nh // 2, glyph)

    def _draw_sharp(self, painter, x, ynote, nh, ls, lw):
        """Two vertical + two angled horizontal lines."""
        from PySide6.QtGui import QPen, QColor
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        ystart = ynote - nh
        yend = ynote + 2 * nh
        vx = x + nh // 2
        painter.drawLine(vx, ystart + 2, vx, yend)
        vx2 = vx + nh // 2
        painter.drawLine(vx2, ystart, vx2, yend - 2)

        # Slightly upwards horizontal lines
        xstart = x + nh // 2 - nh // 4
        xend = x + nh + nh // 4
        hy1_start = ynote + lw
        hy1_end = hy1_start - lw - ls // 4
        pen.setWidth(ls // 2)
        painter.setPen(pen)
        painter.drawLine(xstart, hy1_start, xend, hy1_end)
        painter.drawLine(xstart, hy1_start + ls, xend, hy1_end + ls)
        pen.setWidth(1)
        painter.setPen(pen)

    def _draw_flat(self, painter, x, ynote, nh, ls, lw):
        """Vertical line + bezier curve."""
        from PySide6.QtGui import QPen, QColor, QPainterPath
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        fx = x + ls // 4
        # Vertical line
        painter.drawLine(fx, ynote - nh - nh // 2, fx, ynote + nh)

        # Three bezier curves for thickness
        for extra_x, extra_y in [(0, 0),
                                 (ls // 4, -ls // 4),
                                 (ls // 2, -ls // 2)]:
            path = QPainterPath()
            path.moveTo(fx, ynote + ls // 4)
            path.cubicTo(
                fx + ls // 2, ynote - ls // 2,
                fx + ls + extra_x, ynote + ls // 3 + extra_y,
                fx, ynote + ls + lw + 1
            )
            painter.drawPath(path)

    def _draw_natural(self, painter, x, ynote, nh, ls, lw):
        """Two vertical + two horizontal lines."""
        from PySide6.QtGui import QPen, QColor
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        # Two vertical lines
        ystart = ynote - ls - lw
        yend = ynote + ls + lw
        vx = x + ls // 2
        painter.drawLine(vx, ystart, vx, yend)

        vx2 = vx + ls - ls // 4
        ystart2 = ynote - ls // 4
        yend2 = ynote + 2 * ls + lw - ls // 4
        painter.drawLine(vx2, ystart2, vx2, yend2)

        # Slightly upwards horizontal lines
        xstart = x + ls // 2
        xend = xstart + ls - ls // 4
        hy_start = ynote + lw
        hy_end = hy_start - lw - ls // 4
        pen.setWidth(ls // 2)
        painter.setPen(pen)
        painter.drawLine(xstart, hy_start, xend, hy_end)
        painter.drawLine(xstart, hy_start + ls, xend, hy_end + ls)
        pen.setWidth(1)
        painter.setPen(pen)

    def __repr__(self):
        names = {NONE: "None", SHARP: "Sharp", FLAT: "Flat", NATURAL: "Natural"}
        return f"AccidSymbol({names.get(self.accid, '?')}, {self.whitenote})"
