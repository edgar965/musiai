"""ClefItem - Zeichnet einen sauberen Violinschlüssel als QPainterPath."""

import logging
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PySide6.QtGui import QPainterPath, QPen, QColor, QBrush
from PySide6.QtCore import Qt

logger = logging.getLogger("musiai.notation.ClefItem")


class ClefItem(QGraphicsPathItem):
    """Violinschlüssel als saubere Vektorgrafik.

    Gezeichnet als stilisierte Kurve statt Unicode-Hack.
    Klickbar: zeigt Schlüssel-Eigenschaften im Properties Panel.
    """

    def __init__(self, x: float, center_y: float, staff_half: float):
        super().__init__()
        self.setPos(x, center_y)
        self.setZValue(3)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._staff_half = staff_half
        self._build_path()

    def _build_path(self) -> None:
        """Stilisierter Violinschlüssel als Bezier-Kurven."""
        h = self._staff_half
        path = QPainterPath()

        # Untere Spirale
        path.moveTo(8, h + 6)
        path.cubicTo(2, h + 2, 2, h - 4, 8, h - 8)

        # Aufstieg durch die Linien
        path.cubicTo(14, h - 14, 14, -h + 8, 10, -h - 2)

        # Oberer Bogen
        path.cubicTo(6, -h - 10, 0, -h - 8, 2, -h + 2)

        # Abstieg Mitte
        path.cubicTo(4, -h + 10, 10, -4, 10, 4)

        # Untere Schleife
        path.cubicTo(10, 12, 4, h - 2, 4, h + 2)
        path.cubicTo(4, h + 6, 6, h + 8, 8, h + 6)

        self.setPath(path)
        pen = QPen(QColor(30, 30, 60), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        # Punkt unten
        self._dot_path = QPainterPath()
        self._dot_path.addEllipse(6, h + 2, 4, 4)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 60)))
        painter.drawPath(self._dot_path)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)
