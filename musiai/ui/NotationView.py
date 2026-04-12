"""NotationView - QGraphicsView für die Notation-Scene."""

import logging
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, Signal
from musiai.notation.NotationScene import NotationScene

logger = logging.getLogger("musiai.ui.NotationView")


class NotationView(QGraphicsView):
    """Scrollbare, zoombare Ansicht der Notation."""

    note_clicked = Signal(object)  # NoteItem

    def __init__(self, scene: NotationScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom_level = 1.0
        logger.debug("NotationView erstellt")

    def zoom_in(self) -> None:
        if self._zoom_level < 3.0:
            self._zoom_level *= 1.2
            self.setTransform(self.transform().scale(1.2, 1.2))
            logger.debug(f"Zoom in: {self._zoom_level:.1f}x")

    def zoom_out(self) -> None:
        if self._zoom_level > 0.3:
            self._zoom_level /= 1.2
            self.setTransform(self.transform().scale(1 / 1.2, 1 / 1.2))
            logger.debug(f"Zoom out: {self._zoom_level:.1f}x")

    def scroll_to_beat(self, beat: float) -> None:
        """Scrollt die Ansicht zu einer bestimmten Beat-Position."""
        from musiai.util.Constants import PIXELS_PER_BEAT
        x = beat * PIXELS_PER_BEAT + 40
        self.centerOn(x, self.sceneRect().height() / 2)

    def wheelEvent(self, event):
        """Mausrad → Zoom."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Klick auf Note erkennen."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            scene = self.scene()
            if isinstance(scene, NotationScene):
                note_item = scene.get_note_item_at(scene_pos)
                if note_item:
                    self.note_clicked.emit(note_item)
                    return
        super().mousePressEvent(event)
