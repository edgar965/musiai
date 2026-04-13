"""ClefSymbol - Violin- und Bassschluessel via Bravura SMuFL Font."""

from musiai.ui.midi.MusicSymbol import MusicSymbol

TREBLE = 0
BASS = 1

_font_loaded = False


def _ensure_font():
    """Bravura Font einmalig laden."""
    global _font_loaded
    if _font_loaded:
        return
    import os
    from PySide6.QtGui import QFontDatabase
    font_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..",
        "media", "fonts", "Bravura.otf")
    font_path = os.path.abspath(font_path)
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)
    _font_loaded = True


class ClefSymbol(MusicSymbol):
    """Zeichnet Notenschluessel mit Bravura SMuFL Font."""

    # SMuFL Codepoints
    TREBLE_GLYPH = "\uE050"
    BASS_GLYPH = "\uE062"

    def __init__(self, clef: int, start_time: int = 0, small: bool = False):
        super().__init__(start_time)
        self.clef = clef
        self.small = small
        self._width = self.min_width

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        return SC.NoteWidth * 2 if self.small else SC.NoteWidth * 3

    @property
    def above_staff(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        if self.clef == TREBLE and not self.small:
            return SC.NoteHeight * 2
        return 0

    @property
    def below_staff(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        if self.clef == TREBLE and not self.small:
            return SC.NoteHeight * 2
        elif self.clef == TREBLE and self.small:
            return SC.NoteHeight
        return 0

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QFont, QColor, QPen
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata

        _ensure_font()

        nh = SC.NoteHeight
        ls = SC.LineSpace
        lw = SC.LineWidth
        offset = self.width - self.min_width
        dx = x + offset

        painter.setPen(QPen(QColor(0, 0, 0)))

        # Font size: the notehead font size gives 1 staff space per sc pixels.
        # Clef uses the same font size as noteheads for consistent scaling.
        fs = SMuFLMetadata.notehead_font_size(ls)
        sc = SMuFLMetadata.font_scale(fs)

        if self.clef == TREBLE:
            if self.small:
                size = max(10, int(ls * 2.8))
            else:
                size = fs  # Same size as noteheads
            font = QFont("Bravura", size)
            painter.setFont(font)
            # gClef origin is at the G line (2nd line from bottom = line 4
            # counting from top in 0-based, or 3rd line in 0-based).
            # Staff line positions: ytop + line*(lw+ls) for line 0..4
            # Line 3 (G4, 2nd from bottom) = ytop + 3*(lw+ls) - lw
            # The glyph baseline sits at the G line.
            y_g_line = ytop - lw + 3 * (lw + ls)
            painter.drawText(dx, y_g_line, self.TREBLE_GLYPH)
        else:
            if self.small:
                size = max(8, int(ls * 2.8))
            else:
                size = fs
            font = QFont("Bravura", size)
            painter.setFont(font)
            # fClef origin is at the F line (4th line = line 1 from top).
            # Line 1 = ytop + 1*(lw+ls) - lw
            y_f_line = ytop - lw + 1 * (lw + ls)
            painter.drawText(dx, y_f_line, self.BASS_GLYPH)
