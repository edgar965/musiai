"""DurationItem - Zeigt Tempo-Abweichung als Text über der Note."""

import logging
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from PySide6.QtGui import QFont, QBrush, QColor

logger = logging.getLogger("musiai.notation.DurationItem")


class DurationItem(QGraphicsSimpleTextItem):
    """Text über der Note: zeigt Tempo-Abweichung.

    z.B. ×1.20 für 20% schneller (accel.)
         ×0.80 für 20% langsamer (rit.)
    """

    def __init__(self, deviation: float, x: float, y: float):
        super().__init__(f"\u00d7{deviation:.2f}")
        self.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.setPos(x - 12, y - 18)
        self.setZValue(15)
        self._update_color(deviation)

    def _update_color(self, deviation: float) -> None:
        if deviation < 1.0:
            # Langsamer → Orange (rit.)
            self.setBrush(QBrush(QColor(200, 100, 0)))
        else:
            # Schneller → Blau (accel.)
            self.setBrush(QBrush(QColor(0, 80, 200)))
