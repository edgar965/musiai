"""ClefSymbol - Violin- und Bassschluessel (portiert von ClefSymbol.java)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol

TREBLE = 0
BASS = 1


class ClefSymbol(MusicSymbol):
    """Zeichnet einen Notenschluessel (Treble oder Bass)."""

    def __init__(self, clef: int, start_time: int = 0, small: bool = False):
        super().__init__(start_time)
        self.clef = clef
        self.small = small
        self._width = self.min_width

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        if self.small:
            return SC.NoteWidth * 2
        else:
            return SC.NoteWidth * 3

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
        from PySide6.QtGui import QFont, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC.NoteHeight
        nw = SC.NoteWidth
        staff_h = SC.StaffHeight

        # Align to right (like Java: canvas.translate(getWidth()-getMinWidth(), 0))
        offset = self.width - self.min_width
        dx = x + offset

        painter.setPen(QColor(30, 30, 60))
        if self.clef == TREBLE:
            if self.small:
                height = staff_h + staff_h // 4
                y = ytop
            else:
                height = 3 * staff_h // 2 + nh // 2
                y = ytop - nh
            # Use Unicode treble clef, scaled to match Java bitmap height
            size = max(10, int(height * 0.75))
            painter.setFont(QFont("Segoe UI Symbol", size))
            painter.drawText(dx, y, self.min_width + 10,
                             height, 0, "\U0001D11E")
        else:
            if self.small:
                height = staff_h - 3 * nh // 2
            else:
                height = staff_h - nh
            y = ytop
            size = max(8, int(height * 0.85))
            painter.setFont(QFont("Segoe UI Symbol", size))
            painter.drawText(dx, y, self.min_width + 10,
                             height, 0, "\U0001D122")
