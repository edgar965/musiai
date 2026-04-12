"""EditController - Auswahl, Bearbeitung, Copy/Paste, Mehrfachauswahl."""

import logging
import json
from musiai.model.Note import Note
from musiai.model.Measure import Measure
from musiai.model.TimeSignature import TimeSignature
from musiai.notation.NotationScene import NotationScene
from musiai.notation.NoteItem import NoteItem
from musiai.util.SignalBus import SignalBus

logger = logging.getLogger("musiai.controller.EditController")


class EditController:
    """Verwaltet Auswahl (Einzel/Mehrfach), Bearbeitung, Copy/Paste."""

    def __init__(self, notation_scene: NotationScene, signal_bus: SignalBus):
        self.scene = notation_scene
        self.signal_bus = signal_bus
        self._selected_notes: list[Note] = []
        self._selected_measure: Measure | None = None
        self._clipboard_notes: list[dict] = []
        self._clipboard_measures: list[dict] = []

    @property
    def selected_note(self) -> Note | None:
        return self._selected_notes[0] if self._selected_notes else None

    @property
    def selected_notes(self) -> list[Note]:
        return list(self._selected_notes)

    @property
    def selected_measure(self) -> Measure | None:
        return self._selected_measure

    # ---- Selection ----

    def select_note(self, note_item: NoteItem, ctrl: bool = False,
                    shift: bool = False) -> None:
        """Note auswählen. Ctrl=toggle, Shift=range, sonst Einzelauswahl."""
        if ctrl:
            self._toggle_note(note_item.note)
        elif shift and self._selected_notes:
            self._range_select(note_item.note)
        else:
            self._deselect_all_visual()
            self._selected_notes = [note_item.note]
            self._selected_measure = None
            note_item.set_selected_visual(True)

        self.signal_bus.note_selected.emit(
            self._selected_notes[0] if self._selected_notes else None
        )
        logger.debug(f"Auswahl: {len(self._selected_notes)} Noten")

    def select_measure(self, measure: Measure) -> None:
        """Takt auswählen (alle Noten darin)."""
        self._deselect_all_visual()
        self._selected_measure = measure
        self._selected_notes = list(measure.notes)
        self._reselect_all_visual()
        logger.debug(f"Takt {measure.number} ausgewählt ({len(measure.notes)} Noten)")

    def deselect(self) -> None:
        self._deselect_all_visual()
        self._selected_notes.clear()
        self._selected_measure = None
        self.signal_bus.notes_deselected.emit()

    def _toggle_note(self, note: Note) -> None:
        """Ctrl+Click: Note zur Auswahl hinzufügen/entfernen."""
        if note in self._selected_notes:
            self._selected_notes.remove(note)
            item = self._find_item(note)
            if item:
                item.set_selected_visual(False)
        else:
            self._selected_notes.append(note)
            item = self._find_item(note)
            if item:
                item.set_selected_visual(True)
        self._selected_measure = None

    def _range_select(self, end_note: Note) -> None:
        """Shift+Click: Alle Noten zwischen erster Auswahl und Klick."""
        all_items = self.scene.get_all_note_items()
        all_notes = [item.note for item in all_items]

        start = self._selected_notes[0]
        try:
            idx_start = all_notes.index(start)
            idx_end = all_notes.index(end_note)
        except ValueError:
            return

        lo, hi = min(idx_start, idx_end), max(idx_start, idx_end)
        self._deselect_all_visual()
        self._selected_notes = all_notes[lo:hi + 1]
        self._reselect_all_visual()
        self._selected_measure = None

    # ---- Delete ----

    def delete_selected(self) -> None:
        """Ausgewählte Noten oder Takt löschen."""
        if not self._selected_notes:
            return

        for note in list(self._selected_notes):
            for renderer in self.scene.measure_renderers:
                if note in renderer.measure.notes:
                    renderer.measure.remove_note(note)
                    break
            self.signal_bus.note_deleted.emit(note)

        count = len(self._selected_notes)
        self._selected_notes.clear()
        self._selected_measure = None
        self.scene.refresh()
        logger.info(f"{count} Noten gelöscht")

    # ---- Edit ----

    def change_velocity(self, velocity: int) -> None:
        vel = max(0, min(127, velocity))
        for note in self._selected_notes:
            note.expression.velocity = vel
            item = self._find_item(note)
            if item:
                item.update_from_note()
        if self._selected_notes:
            self.signal_bus.note_changed.emit(self._selected_notes[0])

    def change_cent_offset(self, cents: float, glide_type: str = "zigzag") -> None:
        cents = max(-50, min(50, cents))
        for note in self._selected_notes:
            note.expression.cent_offset = cents
            note.expression.glide_type = glide_type if abs(cents) > 0.5 else "none"
        if self._selected_notes:
            self.signal_bus.note_changed.emit(self._selected_notes[0])
            self.scene.refresh()
            self._reselect_all_visual()

    def change_duration_deviation(self, deviation: float) -> None:
        dev = max(0.8, min(1.2, deviation))
        for note in self._selected_notes:
            note.expression.duration_deviation = dev
        if self._selected_notes:
            self.signal_bus.note_changed.emit(self._selected_notes[0])
            self.scene.refresh()
            self._reselect_all_visual()

    # ---- Copy / Paste ----

    def copy(self) -> None:
        """Ausgewählte Noten oder Takt in die Zwischenablage kopieren."""
        if self._selected_measure:
            self._clipboard_measures = [self._selected_measure.to_dict()]
            self._clipboard_notes.clear()
            logger.info(f"Takt {self._selected_measure.number} kopiert")
        elif self._selected_notes:
            self._clipboard_notes = [n.to_dict() for n in self._selected_notes]
            self._clipboard_measures.clear()
            logger.info(f"{len(self._selected_notes)} Noten kopiert")

    def paste(self, target_measure: Measure | None = None) -> None:
        """Aus Zwischenablage einfügen."""
        if self._clipboard_measures:
            self._paste_measures()
        elif self._clipboard_notes:
            self._paste_notes(target_measure)

    def _paste_notes(self, target_measure: Measure | None) -> None:
        """Noten einfügen in den aktuellen oder angegebenen Takt."""
        if not self._clipboard_notes:
            return

        # Zieltakt bestimmen
        if target_measure is None and self._selected_measure:
            target_measure = self._selected_measure
        if target_measure is None and self.scene.measure_renderers:
            # Ersten Takt nehmen als Fallback
            target_measure = self.scene.measure_renderers[0].measure

        if target_measure is None:
            return

        for note_dict in self._clipboard_notes:
            new_note = Note.from_dict(note_dict)
            target_measure.add_note(new_note)

        self.scene.refresh()
        logger.info(f"{len(self._clipboard_notes)} Noten eingefügt in Takt {target_measure.number}")

    def _paste_measures(self) -> None:
        """Takte einfügen nach dem ausgewählten Takt."""
        if not self._clipboard_measures or not self.scene.piece:
            return

        piece = self.scene.piece
        if not piece.parts:
            return

        part = piece.parts[0]
        insert_idx = len(part.measures)

        if self._selected_measure:
            for i, m in enumerate(part.measures):
                if m is self._selected_measure:
                    insert_idx = i + 1
                    break

        for measure_dict in self._clipboard_measures:
            new_measure = Measure.from_dict(measure_dict)
            new_measure.number = insert_idx + 1
            part.measures.insert(insert_idx, new_measure)
            insert_idx += 1

        # Taktnummern neu durchnummerieren
        for i, m in enumerate(part.measures):
            m.number = i + 1

        self.scene.refresh()
        logger.info(f"{len(self._clipboard_measures)} Takte eingefügt")

    @property
    def has_clipboard(self) -> bool:
        return bool(self._clipboard_notes or self._clipboard_measures)

    # ---- Helpers ----

    def _find_item(self, note: Note) -> NoteItem | None:
        for item in self.scene.get_all_note_items():
            if item.note is note:
                return item
        return None

    def _deselect_all_visual(self) -> None:
        for note in self._selected_notes:
            item = self._find_item(note)
            if item:
                item.set_selected_visual(False)

    def _reselect_all_visual(self) -> None:
        for note in self._selected_notes:
            item = self._find_item(note)
            if item:
                item.set_selected_visual(True)

    def _on_note_selected_from_bus(self, note: Note) -> None:
        pass  # Handled internally
