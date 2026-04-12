"""DurationItem - Zeigt Dauer-Abweichung als Zahl über der Note."""

import logging
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from PySide6.QtGui import QFont, QBrush, QColor

logger = logging.getLogger("musiai.notation.DurationItem")


class DurationItem(QGraphicsSimpleTextItem):
    """Zahl über der Note: zeigt Dauer-Abweichung (Faktor - 1).

    z.B. +0.2 für Faktor 1.2 (20% länger)
         -0.1 für Faktor 0.9 (10% kürzer)
    """

    def __init__(self, deviation: float, x: float, y: float):
        diff = deviation - 1.0
        sign = "+" if diff >= 0 else ""
        super().__init__(f"{sign}{diff:.2f}")
        self.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.setPos(x - 12, y - 18)
        self.setZValue(15)
        self._update_color(deviation)

    def _update_color(self, deviation: float) -> None:
        if deviation < 1.0:
            # Kürzer → Orange/Rot
            self.setBrush(QBrush(QColor(200, 100, 0)))
        else:
            # Länger → Blau
            self.setBrush(QBrush(QColor(0, 80, 200)))
