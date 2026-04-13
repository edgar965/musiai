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
                 track_num: int = 0, total_tracks: int = 1):
        from musiai.ui.midi.SheetConfig import SheetConfig as SC

        self.symbols = symbols
        self.track_num = track_num
        self.total_tracks = total_tracks
        self.show_measures = True
        self.measure_length = measure_len

        # Key signature accidentals
        self.key_accids = key_accids or []
        self.keysig_width = SC.key_signature_width(self.key_accids)

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
        x_current += self.clefsym.min_width

        # Draw key signature accidentals
        for a in self.key_accids:
            a.draw(painter, x_current, ytop, config)
            x_current += a.width

        # Draw symbols (notes, rests, bars)
        for s in self.symbols:
            s.draw(painter, x_current, ytop, config)
            x_current += s.width

        # Draw 5 horizontal staff lines
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)
        y = ytop - lw
        for line in range(5):
            painter.drawLine(SC.LeftMargin, y, self.width - 1, y)
            y += lw + ls

        # Draw end lines (left and right vertical bars)
        self._draw_end_lines(painter, ytop, y_offset)

        # Draw measure numbers
        if self.show_measures and self.measure_length > 0:
            self._draw_measure_numbers(painter, ytop)

    def _draw_end_lines(self, painter, ytop, y_offset):
        from PySide6.QtGui import QPen, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC.NoteHeight
        lw = SC.LineWidth

        pen = QPen(QColor(0, 0, 0), 1)
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
