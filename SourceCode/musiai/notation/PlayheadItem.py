"""PlayheadItem - Vertikale Linie die die aktuelle Abspielposition zeigt."""

import logging
from PySide6.QtWidgets import QGraphicsLineItem
from PySide6.QtGui import QPen, QColor

logger = logging.getLogger("musiai.notation.PlayheadItem")


class PlayheadItem(QGraphicsLineItem):
    """Vertikale Linie die sich während des Abspielens bewegt."""

    def __init__(self, height: float = 200):
        super().__init__(0, 0, 0, height)
        pen = QPen(QColor(255, 80, 80, 180), 2)
        self.setPen(pen)
        self.setZValue(20)
        self.setVisible(False)

    def set_x_position(self, x: float) -> None:
        """Playhead horizontal positionieren."""
        self.setPos(x, self.pos().y())

    def set_y_range(self, y_top: float, y_bottom: float) -> None:
        """Vertikalen Bereich setzen."""
        self.setLine(0, 0, 0, y_bottom - y_top)
        self.setPos(self.pos().x(), y_top)

    def show_at(self, x: float) -> None:
        """Zeigen und positionieren."""
        self.set_x_position(x)
        self.setVisible(True)

    def hide(self) -> None:
        self.setVisible(False)
