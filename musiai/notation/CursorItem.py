"""CursorItem - Vertikaler Balken für die Edit-Cursor-Position."""

import logging
from PySide6.QtWidgets import QGraphicsLineItem
from PySide6.QtGui import QPen, QColor

logger = logging.getLogger("musiai.notation.CursorItem")


class CursorItem(QGraphicsLineItem):
    """Blauer vertikaler Balken der die Edit-Position markiert."""

    def __init__(self, height: float = 200):
        super().__init__(0, 0, 0, height)
        pen = QPen(QColor(0, 120, 255, 200), 2.5)
        self.setPen(pen)
        self.setZValue(19)
        self.setVisible(False)

    def set_y_range(self, y_top: float, y_bottom: float) -> None:
        self.setLine(0, 0, 0, y_bottom - y_top)
        self.setPos(self.pos().x(), y_top)

    def show_at(self, x: float) -> None:
        self.setPos(x, self.pos().y())
        self.setVisible(True)

    def hide(self) -> None:
        self.setVisible(False)
