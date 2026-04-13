"""RecordingController - Nimmt Expression-Daten live während des Abspielens auf."""

import logging
from musiai.model.Piece import Piece
from musiai.model.Note import Note
from musiai.midi.MidiKeyboard import MidiKeyboard
from musiai.midi.MidiMapping import MidiMapping
from musiai.audio.Transport import Transport
from musiai.util.SignalBus import SignalBus

logger = logging.getLogger("musiai.controller.RecordingController")


class RecordingController:
    """Nimmt Expression-Werte vom MIDI-Keyboard auf und wendet sie auf Noten an."""

    def __init__(
        self,
        midi_keyboard: MidiKeyboard,
        midi_mapping: MidiMapping,
        transport: Transport,
        signal_bus: SignalBus,
    ):
        self.keyboard = midi_keyboard
        self.mapping = midi_mapping
        self.transport = transport
        self.signal_bus = signal_bus
        self.piece: Piece | None = None
        self._is_recording = False
        self._all_notes: list[tuple[float, Note]] = []

        self._connect_signals()

    def _connect_signals(self) -> None:
        self.keyboard.control_change.connect(self._on_cc)
        self.keyboard.pitch_bend.connect(self._on_pitch_bend)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_piece(self, piece: Piece) -> None:
        self.piece = piece
        self._prepare_note_list()

    def _prepare_note_list(self) -> None:
        """Alle Noten mit absoluten Beat-Positionen sammeln."""
        self._all_notes.clear()
        if not self.piece:
            return
        for part in self.piece.parts:
            abs_beat = 0.0
            for measure in part.measures:
                for note in measure.notes:
                    self._all_notes.append((abs_beat + note.start_beat, note))
                abs_beat += measure.duration_beats
        self._all_notes.sort(key=lambda x: x[0])

    def start_recording(self) -> None:
        self._is_recording = True
        self.signal_bus.recording_started.emit()
        logger.info("Expression-Recording gestartet")

    def stop_recording(self) -> None:
        self._is_recording = False
        self.signal_bus.recording_stopped.emit()
        logger.info("Expression-Recording gestoppt")

    def toggle_recording(self) -> None:
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _get_current_note(self) -> Note | None:
        """Findet die Note an der aktuellen Playback-Position."""
        current_beat = self.transport.current_beat
        best_note = None
        best_dist = float("inf")

        for abs_beat, note in self._all_notes:
            end_beat = abs_beat + note.duration_beats
            if abs_beat <= current_beat <= end_beat:
                dist = abs(current_beat - abs_beat)
                if dist < best_dist:
                    best_dist = dist
                    best_note = note
        return best_note

    def _on_cc(self, cc_number: int, value: int) -> None:
        if not self._is_recording or self.transport.state != "playing":
            return

        result = self.mapping.map_cc(cc_number, value)
        if not result:
            return

        note = self._get_current_note()
        if not note:
            return

        param, val = result
        if param == "velocity":
            note.expression.velocity = int(val)
            logger.debug(f"Recording: {note.name} Velocity → {int(val)}")
        elif param == "duration":
            note.expression.duration_deviation = val
            logger.debug(f"Recording: {note.name} Duration → {val:.2f}")

        self.signal_bus.note_changed.emit(note)

    def _on_pitch_bend(self, value: int) -> None:
        if not self._is_recording or self.transport.state != "playing":
            return

        note = self._get_current_note()
        if not note:
            return

        cents = self.mapping.map_pitch_bend(value)
        note.expression.cent_offset = cents
        note.expression.glide_type = "zigzag" if abs(cents) > 0.5 else "none"
        logger.debug(f"Recording: {note.name} Cents → {cents:.1f}")
        self.signal_bus.note_changed.emit(note)
