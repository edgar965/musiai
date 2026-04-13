"""BarSymbol - Taktstrich."""

from musiai.ui.midi.MusicSymbol import MusicSymbol


class BarSymbol(MusicSymbol):
    """Vertikaler Taktstrich."""

    def __init__(self, start_time: int):
        super().__init__(start_time)

    @property
    def min_width(self) -> int:
        return 10  # 2 * LineSpace

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor
        nh = config.get('note_height', 8)
        ls = config.get('line_space', 7)
        pen = QPen(QColor(60, 60, 80), 1)
        painter.setPen(pen)
        nw = config.get('note_width', 10)
        bx = x + nw // 2
        painter.drawLine(bx, ytop, bx, ytop + 4 * ls + 4)
