"""NoteItem - Farbiger Punkt als QGraphicsEllipseItem."""

import logging
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import Qt
from musiai.model.Note import Note
from musiai.notation.ColorScheme import ColorScheme
from musiai.util.Constants import NOTE_RADIUS

logger = logging.getLogger("musiai.notation.NoteItem")


class NoteItem(QGraphicsEllipseItem):
    """Visuelle Darstellung einer Note als farbiger Punkt."""

    def __init__(self, note: Note, x: float, y: float):
        r = NOTE_RADIUS
        super().__init__(-r, -r + 1, r * 2, (r - 1) * 2)
        self.note = note
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._selected = False
        self.update_from_note()

    def update_from_note(self) -> None:
        """Farbe und Darstellung aus Note-Daten aktualisieren."""
        color = ColorScheme.velocity_to_color(self.note.expression.velocity)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.PenStyle.NoPen))

        if self._selected:
            self.setPen(QPen(QColor(255, 255, 255), 2))

    def set_selected_visual(self, selected: bool) -> None:
        """Auswahl-Ring anzeigen/verstecken."""
        self._selected = selected
        if selected:
            self.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            self.setPen(QPen(Qt.PenStyle.NoPen))

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)
