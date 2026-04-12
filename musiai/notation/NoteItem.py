"""NoteItem - Farbiger Notenkopf mit Hals als QGraphicsItem."""

import logging
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import Qt
from musiai.model.Note import Note
from musiai.notation.ColorScheme import ColorScheme
from musiai.util.Constants import NOTE_RADIUS, MIDI_MIDDLE_C

logger = logging.getLogger("musiai.notation.NoteItem")

STEM_LENGTH = 30


class NoteItem(QGraphicsEllipseItem):
    """Visuelle Darstellung einer Note: farbiger Kopf + Hals."""

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

        # Notenhals
        self._stem = QGraphicsLineItem(self)
        self._stem.setZValue(9)
        self._update_stem()
        self.update_from_note()

    def _update_stem(self) -> None:
        """Hals zeichnen: nach oben wenn Note unter Mittellinie, sonst nach unten."""
        if self.note.pitch >= MIDI_MIDDLE_C:
            # Hals nach oben (rechts vom Kopf)
            self._stem.setLine(NOTE_RADIUS - 1, 0, NOTE_RADIUS - 1, -STEM_LENGTH)
        else:
            # Hals nach unten (links vom Kopf)
            self._stem.setLine(-NOTE_RADIUS + 1, 0, -NOTE_RADIUS + 1, STEM_LENGTH)

    def update_from_note(self) -> None:
        """Farbe aus Note-Daten aktualisieren."""
        color = ColorScheme.velocity_to_color(self.note.expression.velocity)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        # Hals in gleicher Farbe, etwas dunkler
        stem_color = color.darker(120)
        self._stem.setPen(QPen(stem_color, 1.5))

        if self._selected:
            self.setPen(QPen(QColor(255, 255, 255), 2))

    def set_selected_visual(self, selected: bool) -> None:
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
