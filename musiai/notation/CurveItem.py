"""CurveItem - Gleitender Bogen für Glissando-artige Cent-Verschiebung."""

import logging
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtCore import Qt
from musiai.notation.ColorScheme import ColorScheme

logger = logging.getLogger("musiai.notation.CurveItem")


class CurveItem(QGraphicsPathItem):
    """Bogen auf der Notenlinie: zeigt gleitende Cent-Verschiebung.

    Bogen nach oben = positive Cents (höher)
    Bogen nach unten = negative Cents (tiefer)
    Höhe proportional zum Cent-Wert.
    """

    def __init__(self, cents: float, x: float, y: float, width: float = 30):
        super().__init__()
        self.cents = cents
        self.curve_width = width
        self.setPos(x, y)
        self.setZValue(5)
        self._build_path()

    def _build_path(self) -> None:
        height = self.cents * 0.6
        w = self.curve_width

        path = QPainterPath()
        path.moveTo(-w / 2, 0)
        path.quadTo(0, -height, w / 2, 0)

        self.setPath(path)
        pen = QPen(ColorScheme.cent_marker_color(), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def update_cents(self, cents: float) -> None:
        """Cent-Wert aktualisieren und Pfad neu berechnen."""
        self.cents = cents
        self._build_path()
