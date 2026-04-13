"""BarSymbol - Taktstrich."""

from musiai.ui.midi.MusicSymbol import MusicSymbol


class BarSymbol(MusicSymbol):
    """Vertikaler Taktstrich."""

    def __init__(self, start_time: int):
        super().__init__(start_time)

    @property
    def min_width(self) -> int:
        return 12

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor
        ls = config.get('line_space', 12)
        pen = QPen(QColor(60, 60, 80), 1.2)
        painter.setPen(pen)
        bx = x + 4
        painter.drawLine(bx, ytop, bx, ytop + 4 * ls)
