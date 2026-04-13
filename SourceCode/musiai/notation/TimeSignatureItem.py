"""TimeSignatureItem - Taktart-Anzeige als saubere Grafik."""

import logging
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtCore import Qt
from musiai.model.TimeSignature import TimeSignature

logger = logging.getLogger("musiai.notation.TimeSignatureItem")


class TimeSignatureItem(QGraphicsItemGroup):
    """Taktart als zwei gestapelte Zahlen, zentriert auf den Notenlinien.

    Klickbar: zeigt Taktart-Eigenschaften im Properties Panel.
    """

    def __init__(self, time_sig: TimeSignature, x: float, center_y: float,
                 staff_half: float):
        super().__init__()
        self.time_sig = time_sig
        self.setPos(x, center_y)
        self.setZValue(3)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._build(staff_half)

    def _build(self, staff_half: float) -> None:
        font = QFont("Arial", 16, QFont.Weight.ExtraBold)
        color = QColor(30, 30, 60)

        # Zähler (obere Hälfte der Notenlinien)
        num = QGraphicsSimpleTextItem(str(self.time_sig.numerator))
        num.setFont(font)
        num.setBrush(QBrush(color))
        # Zentriert in der oberen Hälfte
        num_width = num.boundingRect().width()
        num.setPos(-num_width / 2, -staff_half - 2)
        self.addToGroup(num)

        # Nenner (untere Hälfte der Notenlinien)
        den = QGraphicsSimpleTextItem(str(self.time_sig.denominator))
        den.setFont(font)
        den.setBrush(QBrush(color))
        den_width = den.boundingRect().width()
        den.setPos(-den_width / 2, 2)
        self.addToGroup(den)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)
