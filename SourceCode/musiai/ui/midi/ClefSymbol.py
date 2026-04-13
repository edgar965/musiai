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
        return 20 if self.small else 30

    @property
    def above_staff(self) -> int:
        if self.clef == TREBLE:
            return 16 if not self.small else 8
        return 0

    @property
    def below_staff(self) -> int:
        if self.clef == TREBLE:
            return 16 if not self.small else 8
        return 0

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QFont, QColor
        nh = config.get('note_height', 8)
        sh = config.get('staff_height', 32)

        if self.clef == TREBLE:
            font_size = 36 if not self.small else 24
            painter.setFont(QFont("Segoe UI Symbol", font_size))
            painter.setPen(QColor(30, 30, 60))
            y_offset = -nh * 2 if not self.small else -nh
            painter.drawText(x, ytop + y_offset, sh + nh, sh + nh * 2, 0, "𝄞")
        else:
            font_size = 28 if not self.small else 18
            painter.setFont(QFont("Segoe UI Symbol", font_size))
            painter.setPen(QColor(30, 30, 60))
            painter.drawText(x + 2, ytop, sh, sh, 0, "𝄢")
