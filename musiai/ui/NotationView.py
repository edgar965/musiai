"""NotationView - QGraphicsView für die Notation-Scene."""

import logging
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, Signal
from musiai.notation.NotationScene import NotationScene
from musiai.notation.NoteItem import NoteItem

logger = logging.getLogger("musiai.ui.NotationView")


class NotationView(QGraphicsView):
    """Scrollbare, zoombare Ansicht der Notation."""

    note_clicked = Signal(object)            # NoteItem
    clef_clicked = Signal()                  # Schlüssel angeklickt
    time_signature_clicked = Signal(object)  # TimeSignatureItem
    measure_clicked = Signal(object)         # MeasureRenderer (via Takt-Bereich)

    def __init__(self, scene: NotationScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom_level = 1.0

    def zoom_in(self) -> None:
        if self._zoom_level < 3.0:
            self._zoom_level *= 1.2
            self.setTransform(self.transform().scale(1.2, 1.2))

    def zoom_out(self) -> None:
        if self._zoom_level > 0.3:
            self._zoom_level /= 1.2
            self.setTransform(self.transform().scale(1 / 1.2, 1 / 1.2))

    def scroll_to_beat(self, beat: float) -> None:
        from musiai.util.Constants import PIXELS_PER_BEAT
        x = beat * PIXELS_PER_BEAT + 40
        self.centerOn(x, self.sceneRect().height() / 2)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Klick erkennen: Note, Schlüssel, Taktart oder Takt-Bereich."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            scene = self.scene()

            if not isinstance(scene, NotationScene):
                super().mousePressEvent(event)
                return

            # Was wurde angeklickt?
            for item in scene.items(scene_pos):
                if isinstance(item, NoteItem):
                    self.note_clicked.emit(item)
                    return

        super().mousePressEvent(event)
