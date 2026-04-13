"""ClefSymbol - Violin- und Bassschlüssel."""

from musiai.ui.midi.MusicSymbol import MusicSymbol

TREBLE = 0
BASS = 1


class ClefSymbol(MusicSymbol):
    """Zeichnet einen Notenschlüssel (Treble oder Bass)."""

    def __init__(self, clef: int, start_time: int = 0, small: bool = False):
        super().__init__(start_time)
        self.clef = clef
        self.small = small

    @property
    def min_width(self) -> int:
        return 30 if not self.small else 20

    @property
    def above_staff(self) -> int:
        if self.clef == TREBLE:
            return 20 if not self.small else 10
        return 0

    @property
    def below_staff(self) -> int:
        if self.clef == TREBLE:
            return 15 if not self.small else 8
        return 0

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QFont, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        ls = SC.LineSpace
        nh = SC.NoteHeight
        staff_h = SC.StaffHeight

        painter.setPen(QColor(30, 30, 60))
        if self.clef == TREBLE:
            # Font-Größe proportional zum Staff (C#: Bildgröße = 1.5*StaffHeight)
            size = max(16, int(staff_h * 1.2))
            painter.setFont(QFont("Segoe UI Symbol", size))
            painter.drawText(x, ytop - nh * 2, self.min_width + 10,
                             staff_h + nh * 4, 0, "𝄞")
        else:
            size = max(12, int(staff_h * 0.8))
            painter.setFont(QFont("Segoe UI Symbol", size))
            painter.drawText(x + 1, ytop - nh, self.min_width + 10,
                             staff_h + nh * 2, 0, "𝄢")
