"""NoteItem - Farbiger Notenkopf mit Hals als QGraphicsItem."""

import logging
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import Qt
from musiai.model.Note import Note
from musiai.notation.ColorScheme import ColorScheme
from musiai.util.Constants import NOTE_RADIUS

logger = logging.getLogger("musiai.notation.NoteItem")

STEM_LENGTH = 24


class NoteItem(QGraphicsEllipseItem):
    """Visuelle Darstellung einer Note: farbiger Kopf + Hals."""

    def __init__(self, note: Note, x: float, y: float, center_y: float = 0):
        r = NOTE_RADIUS
        # Ovaler Notenkopf: breiter als hoch (wie echte Noten)
        super().__init__(-r, -r * 0.7, r * 2, r * 1.4)
        self.note = note
        self._center_y = center_y
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
        """Notenhals-Richtung nach Standard-Regel:

        Noten UNTER der 3. Notenlinie (center_y): Hals nach OBEN
        Noten AUF oder ÜBER der 3. Notenlinie: Hals nach UNTEN
        Basiert auf der tatsächlichen Y-Position, nicht auf MIDI-Pitch.
        """
        # y > center_y means visually below middle line → stem up
        if self.y() > self._center_y:
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
        # Hals immer schwarz (wie in echter Notation)
        self._stem.setPen(QPen(QColor(30, 30, 50), 1.2))

        if self._selected:
            self.setPen(QPen(QColor(255, 255, 255), 2))

    def set_selected_visual(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.setPen(QPen(QColor(0, 120, 255), 2.5))
        else:
            self.setPen(QPen(Qt.PenStyle.NoPen))

    def stem_end_pos(self) -> tuple[float, float] | None:
        """Absolute Position des Stem-Endes (für Beaming)."""
        if not self._stem:
            return None
        line = self._stem.line()
        return (self.x() + line.x2(), self.y() + line.y2())

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if not self._selected:
            self.setPen(QPen(QColor(100, 180, 255, 150), 1.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        if not self._selected:
            self.setPen(QPen(Qt.PenStyle.NoPen))
        super().hoverLeaveEvent(event)
