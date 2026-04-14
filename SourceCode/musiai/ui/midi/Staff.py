"""Staff - Eine Zeile im Notenblatt (portiert von Staff.cs)."""

import logging
from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.ChordSymbol import ChordSymbol
from musiai.ui.midi.BarSymbol import BarSymbol
from musiai.ui.midi.ClefSymbol import ClefSymbol, TREBLE, BASS
from musiai.ui.midi.WhiteNote import WhiteNote

logger = logging.getLogger("musiai.ui.midi.Staff")


class Staff:
    """Rendert eine Zeile: Schluessel + Key Signature + Symbole + 5 Linien."""

    def __init__(self, symbols: list[MusicSymbol],
                 key_accids: list = None,
                 measure_len: int = 0,
                 track_num: int = 0, total_tracks: int = 1,
                 time_num: int = 0, time_den: int = 0):
        from musiai.ui.midi.SheetConfig import SheetConfig as SC

        self.symbols = symbols
        self.track_num = track_num
        self.total_tracks = total_tracks
        self.show_measures = True
        self.measure_length = measure_len

        # Time signature
        self.time_num = time_num
        self.time_den = time_den

        # Key signature accidentals
        self.key_accids = key_accids or []
        self.keysig_width = SC.key_signature_width(self.key_accids)

        # Add time signature width to keysig_width
        if self.time_num > 0 and self.time_den > 0:
            self.keysig_width += SC.NoteWidth * 2

        # Find clef from first ChordSymbol
        self.clef = self._find_clef(symbols)
        self.clefsym = ClefSymbol(self.clef, 0, False)

        self.ytop = 0
        self.height = 0
        self.width = SC.PageWidth
        self.start_time = 0
        self.end_time = 0

        self.calculate_height()
        self._calculate_start_end_time()
        self._full_justify()

    @staticmethod
    def _find_clef(symbols) -> int:
        for s in symbols:
            if isinstance(s, ChordSymbol):
                return s.clef
        return TREBLE

    def calculate_height(self):
        """Calculate staff height from symbol extents."""
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC.NoteHeight
        ls = SC.LineSpace
        lw = SC.LineWidth

        above = 0
        below = 0
        for s in self.symbols:
            above = max(above, s.above_staff)
            below = max(below, s.below_staff)
        above = max(above, self.clefsym.above_staff)
        below = max(below, self.clefsym.below_staff)
        if self.show_measures:
            above = max(above, nh * 3)

        self.ytop = above + nh
        self.height = nh * 5 + self.ytop + below
        if self.track_num == self.total_tracks - 1:
            self.height += nh * 3

    def _calculate_start_end_time(self):
        if not self.symbols:
            return
        self.start_time = self.symbols[0].start_time
        for s in self.symbols:
            if self.end_time < s.start_time:
                self.end_time = s.start_time
            if isinstance(s, ChordSymbol):
                if self.end_time < s.end_time:
                    self.end_time = s.end_time

    def find_x_for_pulse(self, pulse_time: int) -> int | None:
        """Return the x-offset within this staff for the given pulse time.

        Mirrors the ShadeNotes logic from MidiSheetMusic: iterate symbols,
        find where start <= pulse_time < end, return that symbol's x-pos.
        Returns None if pulse_time is outside this staff's range.
        """
        if pulse_time < self.start_time or pulse_time > self.end_time:
            return None
        # keysig_width already includes LeftMargin+5, clef width, and time sig
        xpos = self.keysig_width

        for i, sym in enumerate(self.symbols):
            if isinstance(sym, BarSymbol):
                xpos += sym.width
                continue

            start = sym.start_time
            # Determine end time: next non-bar symbol's start_time
            end = self.end_time
            j = i + 1
            while j < len(self.symbols):
                if isinstance(self.symbols[j], BarSymbol):
                    j += 1
                    continue
                end = self.symbols[j].start_time
                break

            if start <= pulse_time < end:
                return self._notehead_x(sym, xpos)
            if start > pulse_time:
                return self._notehead_x(sym, xpos)

            xpos += sym.width
        return xpos

    @staticmethod
    def _notehead_x(sym, xpos: int) -> int:
        """Return x at the notehead center, not the symbol left edge."""
        if isinstance(sym, ChordSymbol):
            # Use precomputed stem position (exact notehead x)
            st = sym.stem1 or sym.stem2
            if st and getattr(st, 'drawn_x', None) is not None:
                return st.drawn_x
            # Fallback: skip accidentals + justification padding
            offset = sym.width - sym.min_width
            accid_w = 0
            prev = None
            for ac in sym.accidsymbols:
                if prev is not None and ac.note.dist(prev.note) < 6:
                    accid_w += ac.width
                prev = ac
            if prev is not None:
                accid_w += prev.width
            return xpos + offset + accid_w
        return xpos

    def find_note_at(self, x: int, y: int):
        """Find NoteData at pixel position within this staff's pixmap.

        Returns (ChordSymbol, NoteData) or (None, None).
        Uses drawn_notes stored during draw().
        """
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC.NoteHeight
        tolerance = max(nh, 8)

        for sym in self.symbols:
            if not isinstance(sym, ChordSymbol):
                continue
            for nx, ny, nw, h, note_data in sym.drawn_notes:
                if (nx - 4 <= x <= nx + nw + 4
                        and ny - tolerance // 2 <= y <= ny + h + tolerance // 2):
                    return sym, note_data
        return None, None

    def _full_justify(self):
        """Expand symbols to fill page width."""
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        if self.width != SC.PageWidth:
            return

        nh = SC.NoteHeight
        total_width = self.keysig_width
        total_symbols = 0
        i = 0
        while i < len(self.symbols):
            start = self.symbols[i].start_time
            total_symbols += 1
            total_width += self.symbols[i].width
            i += 1
            while i < len(self.symbols) and self.symbols[i].start_time == start:
                total_width += self.symbols[i].width
                i += 1

        if total_symbols == 0:
            return
        extra = (SC.PageWidth - total_width - 1) // total_symbols
        extra = min(extra, nh * 2)
        if extra <= 0:
            return

        i = 0
        while i < len(self.symbols):
            start = self.symbols[i].start_time
            self.symbols[i].width = self.symbols[i].width + extra
            i += 1
            while i < len(self.symbols) and self.symbols[i].start_time == start:
                i += 1

    def _precompute_stem_positions(self, x_start, config):
        """Pre-calculate every stem's drawn_x before actual drawing.

        This lets beam-drawing read the pair's exact x-position
        instead of guessing via width_to_pair arithmetic.
        """
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        use_bravura = (config.get('use_bravura', False)
                       if isinstance(config, dict) else False)
        ls = SC.LineSpace
        nw = SC.NoteWidth

        x = x_start
        for sym in self.symbols:
            if isinstance(sym, ChordSymbol):
                # Mirror ChordSymbol.draw() offset logic
                offset = sym.width - sym.min_width
                accid_w = 0
                prev = None
                for ac in sym.accidsymbols:
                    if prev is not None and ac.note.dist(prev.note) < 6:
                        accid_w += ac.width
                    prev = ac
                if prev is not None:
                    accid_w += prev.width
                nx_base = x + offset + accid_w

                for st in (sym.stem1, sym.stem2):
                    if st is not None:
                        st.drawn_x = st._calc_stem_x(
                            nx_base, ls, nw, use_bravura)
            x += sym.width

# ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, painter, y_offset: int, config: dict) -> None:
        """Draw the complete staff row."""
        from PySide6.QtGui import QPen, QColor, QFont
        from musiai.ui.midi.SheetConfig import SheetConfig as SC

        nh = SC.NoteHeight
        nw = SC.NoteWidth
        ls = SC.LineSpace
        lw = SC.LineWidth

        ytop = y_offset + self.ytop

        x_current = SC.LeftMargin + 5

        # Draw clef
        self.clefsym.draw(painter, x_current, ytop, config)
        x_current += self.clefsym.width

        # Draw key signature accidentals
        for a in self.key_accids:
            a.draw(painter, x_current, ytop, config)
            x_current += a.width

        # Draw time signature
        if self.time_num > 0 and self.time_den > 0:
            x_current = self._draw_time_signature(
                painter, x_current, ytop, config)

        # Pre-calculate stem x-positions so beams know their endpoints
        self._precompute_stem_positions(x_current, config)

        # Draw symbols (notes, rests, bars)
        x_symbols_start = x_current
        for s in self.symbols:
            s.draw(painter, x_current, ytop, config)
            x_current += s.width

        # Draw tie curves between tied note pairs
        self._draw_ties(painter, ytop, x_symbols_start)

        # Draw 5 horizontal staff lines -- snap to pixel grid
        use_bravura = config.get('use_bravura', False) if isinstance(
            config, dict) else False
        if use_bravura:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            staff_line_thick = SMuFLMetadata.get_engraving_default(
                'staffLineThickness', 0.13)
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)
            sl_w = max(1, int(staff_line_thick * sc + 0.5))
        else:
            sl_w = max(1, lw)
        pen = QPen(QColor(0, 0, 0), sl_w)
        painter.setPen(pen)
        for line in range(5):
            y = int(ytop - lw + line * (lw + ls))
            painter.drawLine(SC.LeftMargin, y, self.width - 1, y)

        # Draw end lines (left and right vertical bars)
        self._draw_end_lines(painter, ytop, y_offset)

        # Draw measure numbers
        if self.show_measures and self.measure_length > 0:
            self._draw_measure_numbers(painter, ytop)

    def _draw_end_lines(self, painter, ytop, y_offset):
        from PySide6.QtGui import QPen, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
        nh = SC.NoteHeight
        lw = SC.LineWidth
        ls = SC.LineSpace

        # Barline thickness from SMuFL
        try:
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)
            bar_thick = SMuFLMetadata.get_engraving_default(
                'thinBarlineThickness', 0.16)
            bar_w = max(1, int(bar_thick * sc + 0.5))
        except Exception:
            bar_w = 1
        pen = QPen(QColor(0, 0, 0), bar_w)
        painter.setPen(pen)

        if self.track_num == 0:
            ystart = ytop - lw
        else:
            ystart = y_offset

        if self.track_num == self.total_tracks - 1:
            yend = ytop + 4 * nh
        else:
            yend = y_offset + self.height

        painter.drawLine(SC.LeftMargin, ystart, SC.LeftMargin, yend)
        painter.drawLine(self.width - 1, ystart, self.width - 1, yend)

    def _draw_time_signature(self, painter, x, ytop, config):
        """Draw time signature numerator/denominator after clef+key sig."""
        from PySide6.QtGui import QFont, QColor, QPen
        from musiai.ui.midi.SheetConfig import SheetConfig as SC

        nh = SC.NoteHeight
        ls = SC.LineSpace
        lw = SC.LineWidth
        use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False

        num_str = str(self.time_num)
        den_str = str(self.time_den)

        if use_bravura:
            from musiai.ui.midi import BravuraGlyphs as BG
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            # Time sig digits should be at notehead font size
            size = SMuFLMetadata.notehead_font_size(ls)
            font = QFont(BG.FONT_NAME, size)
            painter.setFont(font)
            painter.setPen(QPen(QColor(0, 0, 0)))

            # SMuFL time sig digits: baseline at center of the digit.
            # Numerator centered in top half (lines 0-2), baseline at line 1
            # Denominator centered in bottom half (lines 2-4), baseline at line 3
            y_num = ytop - lw + 1 * (lw + ls)
            y_den = ytop - lw + 3 * (lw + ls)

            num_glyph = ''.join(BG.TIME_DIGITS[int(d)] for d in num_str)
            den_glyph = ''.join(BG.TIME_DIGITS[int(d)] for d in den_str)

            painter.drawText(x + 2, y_num, num_glyph)
            painter.drawText(x + 2, y_den, den_glyph)
        else:
            size = max(10, int(ls * 2.5))
            font = QFont("Arial", size, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(0, 0, 0)))

            # Numerator on upper half, denominator on lower half
            y_num = ytop + nh
            y_den = ytop + nh + 2 * (lw + ls)

            painter.drawText(x + 2, y_num, num_str)
            painter.drawText(x + 2, y_den, den_str)

        return x + SC.NoteWidth * 2

    def _draw_ties(self, painter, ytop, x_symbols_start):
        """Draw tie curves between tied note pairs."""
        from PySide6.QtGui import QPen, QColor, QPainterPath
        from PySide6.QtCore import Qt
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        from musiai.ui.midi.Stem import UP

        nh = SC.NoteHeight
        ls = SC.LineSpace

        # Build x-position list for each symbol
        x_positions = []
        x = x_symbols_start
        for s in self.symbols:
            x_positions.append(x)
            x += s.width

        # Tie thickness from SMuFL engraving defaults
        from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
        try:
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc_val = SMuFLMetadata.font_scale(fs)
            mid_thick = SMuFLMetadata.get_engraving_default(
                'tieMidpointThickness', 0.22)
            tie_w = max(1.0, mid_thick * sc_val)
        except Exception:
            tie_w = 1.2
        pen = QPen(QColor(0, 0, 0), tie_w)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))

        topstaff = WhiteNote.top(self.clef)

        for i, sym in enumerate(self.symbols):
            if not isinstance(sym, ChordSymbol):
                continue
            if not getattr(sym, 'tied_to_next', False):
                continue
            # Find the next ChordSymbol
            for j in range(i + 1, len(self.symbols)):
                if isinstance(self.symbols[j], ChordSymbol):
                    next_sym = self.symbols[j]
                    # Draw a tie for the bottom note (representative)
                    note = sym.notedata[0].whitenote
                    y_note = ytop + topstaff.dist(note) * nh // 2

                    x1 = x_positions[i] + sym.width - nh // 2
                    x2 = x_positions[j] + nh // 2

                    # Curve below if stem up, above if stem down
                    # Flat arc: max 1 line space height
                    if sym.stem1 and sym.stem1.direction == UP:
                        curve_y = y_note + nh
                        ctrl_offset = ls
                    else:
                        curve_y = y_note - nh // 2
                        ctrl_offset = -ls

                    # Two control points offset by 1/3 and 2/3 for
                    # a smooth parabolic arc instead of a peak
                    third = (x2 - x1) / 3.0
                    path = QPainterPath()
                    path.moveTo(x1, curve_y)
                    path.cubicTo(x1 + third, curve_y + ctrl_offset,
                                 x2 - third, curve_y + ctrl_offset,
                                 x2, curve_y)
                    painter.drawPath(path)
                    break

    def _draw_measure_numbers(self, painter, ytop):
        from PySide6.QtGui import QFont, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC.NoteHeight
        nw = SC.NoteWidth

        x = self.keysig_width
        y = ytop - nh * 3
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(0, 0, 0))

        for s in self.symbols:
            if isinstance(s, BarSymbol):
                measure = 1 + s.start_time // self.measure_length
                painter.drawText(x + nw // 2, y, str(measure))
            x += s.width
