"""ZigzagItem - Spitze Zacke für sofortige Cent-Verschiebung."""

import logging
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtCore import Qt
from musiai.notation.ColorScheme import ColorScheme

logger = logging.getLogger("musiai.notation.ZigzagItem")


class ZigzagItem(QGraphicsPathItem):
    """Spitze Zacke auf der Notenlinie: zeigt sofortige Cent-Verschiebung.

    Zacke nach oben = positive Cents (höher)
    Zacke nach unten = negative Cents (tiefer)
    Höhe proportional zum Cent-Wert.
    """

    def __init__(self, cents: float, x: float, y: float):
        super().__init__()
        self.cents = cents
        self.setPos(x, y)
        self.setZValue(5)
        self._build_path()

    def _build_path(self) -> None:
        height = self.cents * 0.6  # Skalierung: 50 Cent ≈ 30px
        width = 16

        path = QPainterPath()
        path.moveTo(-width / 2, 0)
        path.lineTo(0, -height)
        path.lineTo(width / 2, 0)

        self.setPath(path)
        pen = QPen(ColorScheme.cent_marker_color(), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def update_cents(self, cents: float) -> None:
        """Cent-Wert aktualisieren und Pfad neu berechnen."""
        self.cents = cents
        self._build_path()
