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
        """Stem endpoint: 3.5 staff spaces = 7 white notes, extra for flags."""
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
        use_bravura = (config.get('use_bravura', False)
                       if isinstance(config, dict) else False)
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)

        self._draw_vertical_line(painter, pen, x, ytop, top_staff,
                                 ls, nh, nw, use_bravura)

        if self.duration in (ND.QUARTER, ND.DOTTED_QUARTER,
                             ND.HALF, ND.DOTTED_HALF):
            return
        if self.receiver:
            return

        if self.pair is not None:
            self._draw_horiz_bar_stem(painter, pen, x, ytop, top_staff,
                                      ls, nh, nw, use_bravura)
        else:
            if use_bravura:
                self._draw_bravura_flag(painter, x, ytop, top_staff,
                                        ls, nh, nw)
            else:
                self._draw_curvy_stem(painter, pen, x, ytop, top_staff,
                                      ls, nh, nw)

    # ------------------------------------------------------------------
    # Stem x-position helper
    # ------------------------------------------------------------------
    def _stem_x(self, x, ls, nw, use_smufl, sc=0.0):
        """Calculate stem x-position for this stem's direction."""
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            if self.direction == UP:
                se = SMuFLMetadata.stem_up_se()
                return int(x + ls // 4 + se[0] * sc)
            else:
                nw_pt = SMuFLMetadata.stem_down_nw()
                return int(x + ls // 4 + nw_pt[0] * sc)
        else:
            if self.side == LEFT_SIDE:
                return x + ls // 4 + 1
            else:
                return x + ls // 4 + nw

    @staticmethod
    def _stem_x_offset(direction, ls, nw, use_smufl, sc=0.0):
        """Stem x offset relative to chord note-x (no absolute x)."""
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            if direction == UP:
                se = SMuFLMetadata.stem_up_se()
                return int(ls // 4 + se[0] * sc)
            else:
                nw_pt = SMuFLMetadata.stem_down_nw()
                return int(ls // 4 + nw_pt[0] * sc)
        else:
            if direction == UP:
                return ls // 4 + nw
            else:
                return ls // 4 + 1

    def _draw_vertical_line(self, painter, pen, x, ytop, top_staff,
                            ls, nh, nw, use_bravura=False):
        # Use SAME x-calculation as beams for consistency
        if use_bravura:
            glyph_w = int(ls * 1.34)
            if self.direction == UP:
                xstart = x + ls // 4 + glyph_w
            else:
                xstart = x + ls // 4
        elif self.side == LEFT_SIDE:
            xstart = x + ls // 4 + 1
        else:
            xstart = x + ls // 4 + nw

        if self.direction == UP:
            if use_smufl:
                se = SMuFLMetadata.stem_up_se()
                y1 = (ytop + top_staff.dist(self.bottom) * nh // 2
                       + nh // 2 - int(se[1] * sc))
            else:
                y1 = ytop + top_staff.dist(self.bottom) * nh // 2 + nh // 4
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            painter.drawLine(xstart, int(y1), xstart, int(ystem))
        elif self.direction == DOWN:
            if use_smufl:
                nw_pt = SMuFLMetadata.stem_down_nw()
                y1 = (ytop + top_staff.dist(self.top) * nh // 2
                       + nh // 2 - int(nw_pt[1] * sc))
            else:
                y1 = ytop + top_staff.dist(self.top) * nh // 2 + nh
                if self.side == LEFT_SIDE:
                    y1 -= nh // 4
                else:
                    y1 -= nh // 2
            ystem = (ytop + top_staff.dist(self.end) * nh // 2 + nh)
            painter.drawLine(xstart, int(y1), xstart, int(ystem))

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
        """Draw flag glyph using Bravura SMuFL font with metadata."""
        from PySide6.QtGui import QFont, QPen, QColor
        from musiai.ui.midi import BravuraGlyphs as BG

        flaggable = {ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET,
                     ND.SIXTEENTH, ND.THIRTYSECOND}
        if self.duration not in flaggable:
            return

        use_smufl = self._has_smufl_metadata()
        sc = 0.0
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)

        xstart = self._stem_x(x, ls, nw, use_smufl, sc)

        size = max(14, int(ls * 3.5))
        font = QFont(BG.FONT_NAME, size)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))

        if self.direction == UP:
            ystem = ytop + top_staff.dist(self.end) * nh // 2
            if use_smufl:
                flag_name = self._flag_glyph_name_up()
                anchor = SMuFLMetadata.flag_stem_up_nw(flag_name)
                y_off = nh // 2 - int(anchor[1] * sc)
            else:
                y_off = nh // 2
            glyph = {ND.EIGHTH: BG.FLAG_8TH_UP,
                     ND.DOTTED_EIGHTH: BG.FLAG_8TH_UP,
                     ND.TRIPLET: BG.FLAG_8TH_UP,
                     ND.SIXTEENTH: BG.FLAG_16TH_UP,
                     ND.THIRTYSECOND: BG.FLAG_32ND_UP}.get(self.duration)
            if glyph:
                painter.drawText(xstart, ystem + y_off, glyph)
        elif self.direction == DOWN:
            ystem = ytop + top_staff.dist(self.end) * nh // 2 + nh
            if use_smufl:
                flag_name = self._flag_glyph_name_down()
                anchor = SMuFLMetadata.get_anchor(flag_name, 'stemDownSW')
                y_off = -int(anchor[1] * sc)
            else:
                y_off = 0
            glyph = {ND.EIGHTH: BG.FLAG_8TH_DOWN,
                     ND.DOTTED_EIGHTH: BG.FLAG_8TH_DOWN,
                     ND.TRIPLET: BG.FLAG_8TH_DOWN,
                     ND.SIXTEENTH: BG.FLAG_16TH_DOWN,
                     ND.THIRTYSECOND: BG.FLAG_32ND_DOWN}.get(self.duration)
            if glyph:
                painter.drawText(xstart, ystem + y_off, glyph)

    def _flag_glyph_name_up(self) -> str:
        """Return SMuFL glyph name for up-stem flag."""
        if self.duration in (ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET):
            return 'flag8thUp'
        elif self.duration == ND.SIXTEENTH:
            return 'flag16thUp'
        elif self.duration == ND.THIRTYSECOND:
            return 'flag32ndUp'
        return 'flag8thUp'

    def _flag_glyph_name_down(self) -> str:
        """Return SMuFL glyph name for down-stem flag."""
        if self.duration in (ND.EIGHTH, ND.DOTTED_EIGHTH, ND.TRIPLET):
            return 'flag8thDown'
        elif self.duration == ND.SIXTEENTH:
            return 'flag16thDown'
        elif self.duration == ND.THIRTYSECOND:
            return 'flag32ndDown'
        return 'flag8thDown'

    def _draw_horiz_bar_stem(self, painter, pen, x, ytop, top_staff,
                             ls, nh, nw, use_bravura=False):
        """Draw horizontal beam to paired stem."""
        from PySide6.QtCore import Qt

        use_smufl = use_bravura and self._has_smufl_metadata()
        sc = 0.0
        if use_smufl:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)
            beam_thick = SMuFLMetadata.get_engraving_default(
                'beamThickness', 0.5)
            beam_px = max(2, int(beam_thick * sc))
        else:
            beam_px = nh // 2

        pen.setWidth(beam_px)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)

        # Beam x-positions: must match vertical stem positions exactly
        if use_bravura:
            glyph_w = int(ls * 1.34)
            if self.direction == UP:
                xstart = x + ls // 4 + glyph_w
                xstart2 = ls // 4 + glyph_w
            else:
                xstart = x + ls // 4
                xstart2 = ls // 4
        else:
            xstart = self._stem_x(x, ls, nw, use_smufl, sc)
            xstart2 = self._stem_x_offset(
                self.pair.direction, ls, nw, use_smufl, sc)

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
