"""NotationView - QGraphicsView für die Notation-Scene."""

import logging
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter, QKeySequence, QShortcut
from PySide6.QtCore import Qt, Signal
from musiai.notation.NotationScene import NotationScene
from musiai.notation.NoteItem import NoteItem

logger = logging.getLogger("musiai.ui.NotationView")


class NotationView(QGraphicsView):
    """Scrollbare, zoombare Ansicht der Notation."""

    note_clicked = Signal(object, bool, bool)  # NoteItem, ctrl, shift
    measure_clicked = Signal(object)           # Measure
    copy_requested = Signal()
    paste_requested = Signal()

    def __init__(self, scene: NotationScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom_level = 1.0
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        copy_sc = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_sc.activated.connect(self.copy_requested.emit)
        paste_sc = QShortcut(QKeySequence.StandardKey.Paste, self)
        paste_sc.activated.connect(self.paste_requested.emit)

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
        self.centerOn(beat * PIXELS_PER_BEAT + 40, self.sceneRect().height() / 2)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.pos())
        scene = self.scene()
        if not isinstance(scene, NotationScene):
            super().mousePressEvent(event)
            return

        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        # Note angeklickt?
        for item in scene.items(scene_pos):
            if isinstance(item, NoteItem):
                self.note_clicked.emit(item, ctrl, shift)
                return

        # Kein Item → Takt-Bereich prüfen
        measure = self._find_measure_at(scene_pos, scene)
        if measure:
            self.measure_clicked.emit(measure)
            return

        super().mousePressEvent(event)

    def _find_measure_at(self, scene_pos, scene: NotationScene):
        """Findet den Takt unter der Scene-Position."""
        x = scene_pos.x()
        for renderer in scene.measure_renderers:
            if renderer.x_offset <= x < renderer.x_offset + renderer.width:
                return renderer.measure
        return None
