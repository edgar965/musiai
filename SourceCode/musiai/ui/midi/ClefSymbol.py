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

        _ensure_font()

        nh = SC.NoteHeight
        staff_h = SC.StaffHeight
        offset = self.width - self.min_width
        dx = x + offset

        painter.setPen(QPen(QColor(0, 0, 0)))

        if self.clef == TREBLE:
            if self.small:
                size = max(12, int(staff_h * 0.7))
                y = ytop + nh
            else:
                size = max(18, int(staff_h * 1.0))
                y = ytop + int(nh * 3.2)
            font = QFont("Bravura", size)
            painter.setFont(font)
            painter.drawText(dx, y, self.TREBLE_GLYPH)
        else:
            if self.small:
                size = max(10, int(staff_h * 0.5))
            else:
                size = max(14, int(staff_h * 0.7))
            y = ytop + int(nh * 1.5)
            font = QFont("Bravura", size)
            painter.setFont(font)
            painter.drawText(dx, y, self.BASS_GLYPH)
