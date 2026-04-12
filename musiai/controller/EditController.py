"""EditController - Noten auswählen, bearbeiten, löschen, verschieben."""

import logging
from musiai.model.Note import Note
from musiai.notation.NotationScene import NotationScene
from musiai.notation.NoteItem import NoteItem
from musiai.util.SignalBus import SignalBus

logger = logging.getLogger("musiai.controller.EditController")


class EditController:
    """Verwaltet Noten-Auswahl und -Bearbeitung."""

    def __init__(self, notation_scene: NotationScene, signal_bus: SignalBus):
        self.scene = notation_scene
        self.signal_bus = signal_bus
        self._selected_note: Note | None = None  # Referenz auf Model-Note (überlebt Refresh)
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.signal_bus.note_selected.connect(self._on_note_selected_from_bus)

    @property
    def selected_note(self) -> Note | None:
        return self._selected_note

    def _find_item_for_note(self, note: Note) -> NoteItem | None:
        """NoteItem für eine Model-Note in der aktuellen Scene finden."""
        for item in self.scene.get_all_note_items():
            if item.note is note:
                return item
        return None

    def select_note(self, note_item: NoteItem) -> None:
        """Note auswählen (und vorherige Auswahl aufheben)."""
        self._deselect_visual()
        self._selected_note = note_item.note
        note_item.set_selected_visual(True)
        self.signal_bus.note_selected.emit(note_item.note)
        logger.debug(f"Note ausgewählt: {note_item.note.name}")

    def deselect(self) -> None:
        """Auswahl aufheben."""
        self._deselect_visual()
        self._selected_note = None
        self.signal_bus.notes_deselected.emit()

    def _deselect_visual(self) -> None:
        """Visuelles Deselect - nur wenn Item noch existiert."""
        if self._selected_note:
            item = self._find_item_for_note(self._selected_note)
            if item:
                item.set_selected_visual(False)

    def delete_selected(self) -> None:
        """Ausgewählte Note löschen."""
        if not self._selected_note:
            return

        note = self._selected_note
        for renderer in self.scene.measure_renderers:
            if note in renderer.measure.notes:
                renderer.measure.remove_note(note)
                break

        self.signal_bus.note_deleted.emit(note)
        self._selected_note = None
        self.scene.refresh()
        logger.info(f"Note gelöscht: {note.name}")

    def change_velocity(self, velocity: int) -> None:
        """Velocity der ausgewählten Note ändern."""
        if not self._selected_note:
            return
        self._selected_note.expression.velocity = max(0, min(127, velocity))
        item = self._find_item_for_note(self._selected_note)
        if item:
            item.update_from_note()
        self.signal_bus.note_changed.emit(self._selected_note)
        logger.debug(f"Velocity → {velocity}")

    def change_cent_offset(self, cents: float, glide_type: str = "zigzag") -> None:
        """Cent-Offset der ausgewählten Note ändern."""
        if not self._selected_note:
            return
        self._selected_note.expression.cent_offset = max(-50, min(50, cents))
        self._selected_note.expression.glide_type = glide_type if abs(cents) > 0.5 else "none"
        self.signal_bus.note_changed.emit(self._selected_note)
        self.scene.refresh()
        self._reselect_visual()
        logger.debug(f"Cent-Offset → {cents}, Typ: {glide_type}")

    def change_duration_deviation(self, deviation: float) -> None:
        """Dauer-Abweichung der ausgewählten Note ändern."""
        if not self._selected_note:
            return
        self._selected_note.expression.duration_deviation = max(0.8, min(1.2, deviation))
        self.signal_bus.note_changed.emit(self._selected_note)
        self.scene.refresh()
        self._reselect_visual()
        logger.debug(f"Dauer-Abweichung → {deviation}")

    def _reselect_visual(self) -> None:
        """Nach Refresh das neue Item wieder markieren."""
        if self._selected_note:
            item = self._find_item_for_note(self._selected_note)
            if item:
                item.set_selected_visual(True)

    def _on_note_selected_from_bus(self, note: Note) -> None:
        """Reagiert auf externe Note-Auswahl."""
        self._deselect_visual()
        self._selected_note = note
        self._reselect_visual()
