"""NotationView - QGraphicsView für die Notation-Scene."""

import logging
from PySide6.QtWidgets import QGraphicsView, QLabel
from PySide6.QtGui import QPainter, QKeySequence, QShortcut
from PySide6.QtCore import Qt, Signal
from musiai.notation.NotationScene import NotationScene
from musiai.notation.NoteItem import NoteItem
from musiai.ui.ZoomWidget import ZoomWidget

logger = logging.getLogger("musiai.ui.NotationView")


class NotationView(QGraphicsView):
    """Scrollbare, zoombare Ansicht der Notation."""

    note_clicked = Signal(object, bool, bool)  # NoteItem, ctrl, shift
    measure_clicked = Signal(object)           # Measure
    clef_clicked = Signal(object)              # Measure (containing clef)
    time_sig_clicked = Signal(object)          # Measure (containing time sig)
    tempo_clicked = Signal()                   # Tempo-Anzeige angeklickt
    part_label_clicked = Signal(int)           # Part-Index
    part_mute_clicked = Signal(int)            # Part-Index
    part_detect_requested = Signal(int)        # Part-Index (Rechtsklick)
    part_delete_requested = Signal(int)        # Part-Index (Rechtsklick)
    copy_requested = Signal()
    paste_requested = Signal()
    deselect_requested = Signal()

    # Edit Mode
    edit_mode_changed = Signal(bool)           # True=entered, False=exited
    cursor_moved = Signal(float)               # new global beat position

    def __init__(self, scene: NotationScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._zoom_level = 1.0
        self._edit_mode = False
        self._cursor_beat = 0.0

        # Edit Mode Label (oben links im View)
        self._edit_label = QLabel("EDIT MODE  (Esc = beenden)", self)
        self._edit_label.setStyleSheet(
            "background: #0070e0; color: white; font-weight: bold; "
            "font-size: 12px; padding: 4px 12px; border-radius: 4px;"
        )
        self._edit_label.move(10, 10)
        self._edit_label.setVisible(False)

        # Zoom widget bottom-right
        self._zoom_widget = ZoomWidget(self)
        self._zoom_widget.zoom_changed.connect(self._set_zoom_absolute)

    @property
    def edit_mode(self) -> bool:
        return self._edit_mode

    @property
    def cursor_beat(self) -> float:
        return self._cursor_beat

    def set_cursor_beat(self, beat: float) -> None:
        self._cursor_beat = max(0.0, beat)

    # ---- Zoom ----

    def zoom_in(self) -> None:
        if self._zoom_level < 4.0:
            self._zoom_level *= 1.2
            self.setTransform(self.transform().scale(1.2, 1.2))
            self._zoom_widget.set_zoom_percent(int(self._zoom_level * 100))

    def zoom_out(self) -> None:
        if self._zoom_level > 0.25:
            self._zoom_level /= 1.2
            self.setTransform(self.transform().scale(1 / 1.2, 1 / 1.2))
            self._zoom_widget.set_zoom_percent(int(self._zoom_level * 100))

    def _set_zoom_absolute(self, factor: float) -> None:
        from PySide6.QtGui import QTransform
        self._zoom_level = factor
        self.setTransform(QTransform.fromScale(factor, factor))

    def scroll_to_beat(self, beat: float) -> None:
        from musiai.util.Constants import PIXELS_PER_BEAT
        self.centerOn(beat * PIXELS_PER_BEAT + 40, self.sceneRect().height() / 2)

    # ---- Events ----

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self._zoom_widget
        w.move(self.width() - w.width() - 12, self.height() - w.height() - 8)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_E and not self._edit_mode:
            self._enter_edit_mode()
            return

        if key == Qt.Key.Key_Escape:
            if self._edit_mode:
                self._exit_edit_mode()
            else:
                self.deselect_requested.emit()
            return

        if self._edit_mode:
            if key == Qt.Key.Key_Right:
                self._cursor_beat = max(0.0, self._cursor_beat + 1.0)
                self.cursor_moved.emit(self._cursor_beat)
                return
            if key == Qt.Key.Key_Left:
                self._cursor_beat = max(0.0, self._cursor_beat - 1.0)
                self.cursor_moved.emit(self._cursor_beat)
                return
            if key == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.copy_requested.emit()
                return
            if key == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.paste_requested.emit()
                return

        # Non-edit-mode: Ctrl+C/V do nothing (no copy/paste outside edit mode)
        if key == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return  # blocked
        if key == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return  # blocked

        super().keyPressEvent(event)

    def _enter_edit_mode(self) -> None:
        self._edit_mode = True
        self._edit_label.setVisible(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFocus()
        self.edit_mode_changed.emit(True)
        self.cursor_moved.emit(self._cursor_beat)
        logger.info("Edit Mode aktiviert")

    def _exit_edit_mode(self) -> None:
        self._edit_mode = False
        self._edit_label.setVisible(False)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.edit_mode_changed.emit(False)
        logger.info("Edit Mode deaktiviert")

    def contextMenuEvent(self, event):
        """Rechtsklick-Menü für Stimm-Labels, Waveforms, Mute-Icons."""
        scene_pos = self.mapToScene(event.pos())
        scene = self.scene()
        if not isinstance(scene, NotationScene):
            super().contextMenuEvent(event)
            return
        # Part-Index finden (Label, Mute oder Waveform)
        for item in scene.items(scene_pos):
            tag = item.data(0)
            if tag in ("part_label", "part_mute", "waveform"):
                idx = item.data(1)
                from PySide6.QtWidgets import QMenu
                menu = QMenu(self)
                menu.addAction("Eigenschaften").triggered.connect(
                    lambda _, i=idx: self.part_label_clicked.emit(i)
                )
                menu.addAction("Noten erkennen...").triggered.connect(
                    lambda _, i=idx: self.part_detect_requested.emit(i)
                )
                menu.addSeparator()
                menu.addAction("Stimme löschen").triggered.connect(
                    lambda _, i=idx: self.part_delete_requested.emit(i)
                )
                menu.exec(event.globalPos())
                return
        super().contextMenuEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()  # Keyboard-Focus sicherstellen
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

        # Schlüssel, Taktart oder Tempo angeklickt?
        for item in scene.items(scene_pos):
            tag = item.data(0)
            if tag == "clef":
                self.clef_clicked.emit(item.data(1))
                return
            if tag == "time_sig":
                self.time_sig_clicked.emit(item.data(1))
                return
            if tag == "tempo":
                self.tempo_clicked.emit()
                return
            if tag == "part_label":
                self.part_label_clicked.emit(item.data(1))
                return
            if tag == "part_mute":
                self.part_mute_clicked.emit(item.data(1))
                return

        # Edit Mode: Klick setzt Cursor-Position
        if self._edit_mode:
            beat = scene.beat_at_x(scene_pos.x())
            self._cursor_beat = beat
            self.cursor_moved.emit(self._cursor_beat)
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
