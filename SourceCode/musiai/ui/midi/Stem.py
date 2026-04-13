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
        """Stem endpoint: 3.5 staff spaces = 7 white notes, extra for flags.

        Verovio uses 3.5 * staff_space as default stem length.
        1 staff space = 2 white notes, so 3.5 * 2 = 7 white notes.
        """
        if self.direction == UP:
            w = self.top.add(7)
            if self.duration == ND.SIXTEENTH:
                w = w.add(2)
            elif self.duration == ND.THIRTYSECOND:
                w = w.add(4)
            return w
        else:
            w = self.bottom.add(-7)
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
            use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False
            if use_bravura:
                self._draw_bravura_flag(painter, x, ytop, top_staff,
                                        ls, nh, nw)
            else:
                self._draw_curvy_stem(painter, pen, x, ytop, top_staff,
                                      ls, nh, nw)

    def _draw_vertical_line(self, painter, pen, x, ytop, top_staff,
                            ls, nh, nw):
        use_smufl = self._has_smufl_metadata()

        # Stem thickness from SMuFL engraving defaults
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            stem_thickness = SMuFLMetadata.get_engraving_default(
                'stemThickness', 0.12)
            stem_w = max(1, int(stem_thickness * ls + 0.5))
            pen.setWidth(stem_w)
            painter.setPen(pen)

        # Stem x: use actual Bravura glyph width for precise attachment
        use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False
        if use_bravura and use_smufl:
            # Empirical: Bravura notehead at font_size=ls*3.5 has width ≈ 1.34*ls
            glyph_w = int(ls * 1.34)
            if self.direction == UP:
                # Stem attaches at RIGHT edge of notehead
                xstart = x + ls // 4 + glyph_w
            else:
                # Stem attaches at LEFT edge of notehead
                xstart = x + ls // 4
        else:
            if self.side == LEFT_SIDE:
                xstart = x + ls // 4 + 1
            else:
                xstart = x + ls // 4 + nw

        # Snap stem x to pixel grid for crisp rendering
        xstart = int(xstart)

        if self.direction == UP:
            if use_smufl:
                se = SMuFLMetadata.stem_up_se()
                # SMuFL y-axis: positive = up; Qt: positive = down
                # stemUpSE.y is negative (below notehead center)
                y1 = (ytop + top_staff.dist(self.bottom) * nh // 2
                       + nh // 2 - int(se[1] * ls))
            else:
                y1 = ytop + top_staff.dist(self.bottom) * nh // 2 + nh // 4
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            painter.drawLine(xstart, int(y1), xstart, int(ystem))
        elif self.direction == DOWN:
            if use_smufl:
                nw_pt = SMuFLMetadata.stem_down_nw()
                # stemDownNW.y is positive (above notehead center)
                y1 = (ytop + top_staff.dist(self.top) * nh // 2
                       + nh // 2 - int(nw_pt[1] * ls))
            else:
                y1 = ytop + top_staff.dist(self.top) * nh // 2 + nh
                if self.side == LEFT_SIDE:
                    y1 -= nh // 4
                else:
                    y1 -= nh // 2
            ystem = (ytop + top_staff.dist(self.end) * nh // 2 + nh)
            painter.drawLine(xstart, int(y1), xstart, int(ystem))

        # Reset pen width
        if use_smufl:
            pen.setWidth(1)
            painter.setPen(pen)

    @staticmethod
    def _has_smufl_metadata() -> bool:
        """Check if SMuFL metadata is available."""
        try:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            SMuFLMetadata.load()
            return bool(SMuFLMetadata._data)
        except Exception:
            return False

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

    def _draw_bravura_flag(self, painter, x, ytop, top_staff,
                           ls, nh, nw):
        """Draw flag glyph using Bravura SMuFL font with metadata positioning."""
        from PySide6.QtGui import QFont, QPen, QColor
        from musiai.ui.midi import BravuraGlyphs as BG

        flaggable = {ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET,
                     ND.SIXTEENTH, ND.THIRTYSECOND}
        if self.duration not in flaggable:
            return

        use_smufl = self._has_smufl_metadata()
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            if self.direction == UP:
                se = SMuFLMetadata.stem_up_se()
                xstart = x + ls // 4 + int(se[0] * ls)
            else:
                nw_pt = SMuFLMetadata.stem_down_nw()
                xstart = x + ls // 4 + int(nw_pt[0] * ls)
        else:
            if self.side == LEFT_SIDE:
                xstart = x + ls // 4 + 1
            else:
                xstart = x + ls // 4 + nw

        size = max(14, int(ls * 3.5))
        font = QFont(BG.FONT_NAME, size)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))

        if self.direction == UP:
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            if use_smufl:
                # Use flag's stemUpNW anchor for vertical offset
                flag_name = self._flag_glyph_name_up()
                anchor = SMuFLMetadata.flag_stem_up_nw(flag_name)
                y_off = nh // 2 - int(anchor[1] * ls)
            else:
                y_off = nh // 2
            if self.duration in (ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET):
                painter.drawText(xstart, ystem + y_off, BG.FLAG_8TH_UP)
            elif self.duration == ND.SIXTEENTH:
                painter.drawText(xstart, ystem + y_off, BG.FLAG_16TH_UP)
            elif self.duration == ND.THIRTYSECOND:
                painter.drawText(xstart, ystem + y_off, BG.FLAG_32ND_UP)
        elif self.direction == DOWN:
            ystem = ytop + top_staff.dist(self.end) * nh // 2 + nh
            if self.duration in (ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET):
                painter.drawText(xstart, ystem, BG.FLAG_8TH_DOWN)
            elif self.duration == ND.SIXTEENTH:
                painter.drawText(xstart, ystem, BG.FLAG_16TH_DOWN)
            elif self.duration == ND.THIRTYSECOND:
                painter.drawText(xstart, ystem, BG.FLAG_32ND_DOWN)

    def _flag_glyph_name_up(self) -> str:
        """Return SMuFL glyph name for up-stem flag based on duration."""
        if self.duration in (ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET):
            return 'flag8thUp'
        elif self.duration == ND.SIXTEENTH:
            return 'flag16thUp'
        elif self.duration == ND.THIRTYSECOND:
            return 'flag32ndUp'
        return 'flag8thUp'

    def _draw_horiz_bar_stem(self, painter, pen, x, ytop, top_staff,
                             ls, nh, nw):
        """Draw horizontal beam to paired stem.

        In Java, drawing is relative to the chord's translated origin.
        Here, x is the absolute position of this chord's note area.
        width_to_pair is the pixel distance between the two chord positions.
        xstart2 is the stem x offset within the paired chord.
        xend = x + width_to_pair + xstart2 for absolute position.
        """
        from PySide6.QtCore import Qt
        pen.setWidth(nh // 2)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)

        use_bravura_beam = config.get('use_bravura', False) if isinstance(config, dict) else False
        if use_bravura_beam:
            glyph_w = int(ls * 1.34)  # empirical Bravura notehead width
            if self.direction == UP:
                xstart = x + ls // 4 + glyph_w
                xstart2 = ls // 4 + glyph_w
            else:
                xstart = x + ls // 4
                xstart2 = ls // 4
        else:
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
