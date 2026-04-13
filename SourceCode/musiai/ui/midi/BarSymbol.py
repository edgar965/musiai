"""BarSymbol - Taktstrich (portiert von BarSymbol.java)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol


class BarSymbol(MusicSymbol):
    """Vertikaler Taktstrich."""

    def __init__(self, start_time: int):
        super().__init__(start_time)
        self._width = self.min_width

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        return 2 * SC.LineSpace

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nw = SC.NoteWidth
        ls = SC.LineSpace
        lw = SC.LineWidth
        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)
        bx = x + nw // 2
        yend = ytop + ls * 4 + lw * 4
        painter.drawLine(bx, ytop, bx, yend)
