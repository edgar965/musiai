"""DurationItem - Farbige Linie um Note herum für Dauer-Abweichung."""

import logging
from PySide6.QtWidgets import QGraphicsLineItem
from PySide6.QtGui import QPen
from PySide6.QtCore import Qt
from musiai.notation.ColorScheme import ColorScheme

logger = logging.getLogger("musiai.notation.DurationItem")


class DurationItem(QGraphicsLineItem):
    """Farbige Linie um die Note: zeigt Dauer-Abweichung.

    Rot-Gelb = kürzer als Standard
    Grau = Standard (unsichtbar)
    Blau = länger als Standard
    """

    HALF_WIDTH = 20  # Pixel links/rechts der Note

    def __init__(self, deviation: float, x: float, y: float):
        super().__init__(-self.HALF_WIDTH, 0, self.HALF_WIDTH, 0)
        self.deviation = deviation
        self.setPos(x, y)
        self.setZValue(4)
        self._update_color()

    def _update_color(self) -> None:
        if abs(self.deviation - 1.0) < 0.01:
            self.setVisible(False)
            return

        self.setVisible(True)
        color = ColorScheme.duration_to_color(self.deviation)
        self.setPen(QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

    def update_deviation(self, deviation: float) -> None:
        """Abweichung aktualisieren."""
        self.deviation = deviation
        self._update_color()
