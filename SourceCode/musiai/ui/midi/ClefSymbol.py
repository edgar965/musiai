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
        ls = config.get('line_space', 12)
        staff_h = 4 * ls

        painter.setPen(QColor(30, 30, 60))
        if self.clef == TREBLE:
            size = 42 if not self.small else 28
            painter.setFont(QFont("Segoe UI Symbol", size))
            # Treble-Schlüssel sitzt auf der 2. Linie (G4)
            painter.drawText(x, int(ytop - ls * 1.5), 50, int(staff_h + ls * 3),
                             0, "𝄞")
        else:
            size = 30 if not self.small else 20
            painter.setFont(QFont("Segoe UI Symbol", size))
            # Bass-Schlüssel sitzt auf der 4. Linie (F3)
            painter.drawText(x + 2, int(ytop - ls * 0.3), 50, int(staff_h + ls),
                             0, "𝄢")
