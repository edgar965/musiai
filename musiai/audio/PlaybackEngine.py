"""PlaybackEngine - Orchestriert Playback: Transport + FluidSynth + Noten."""

import logging
from musiai.model.Piece import Piece
from musiai.model.Note import Note
from musiai.audio.Transport import Transport
from musiai.audio.FluidSynthPlayer import FluidSynthPlayer
from musiai.util.PitchUtils import cents_to_pitch_bend
from musiai.util.SignalBus import SignalBus

logger = logging.getLogger("musiai.audio.PlaybackEngine")


class PlaybackEngine:
    """Spielt ein Piece ab: liest Noten, sendet an FluidSynth."""

    def __init__(self, signal_bus: SignalBus):
        self.signal_bus = signal_bus
        self.transport = Transport()
        self.player = FluidSynthPlayer()
        self.piece: Piece | None = None

        # Tracking welche Noten gerade spielen
        self._active_notes: dict[int, Note] = {}  # MIDI-Note → Note
        self._last_beat = 0.0
        self._all_notes: list[tuple[float, Note, int]] = []  # (abs_beat, note, channel)

        self.transport.position_changed.connect(self._on_beat)
        self.transport.state_changed.connect(self._on_state_changed)

    def set_piece(self, piece: Piece) -> None:
        """Piece setzen und für Playback vorbereiten."""
        self.piece = piece
        self.transport.tempo_bpm = piece.initial_tempo
        self._prepare_note_list()
        logger.info(f"Playback vorbereitet: {len(self._all_notes)} Noten")

    def _prepare_note_list(self) -> None:
        """Alle Noten mit absoluten Beat-Positionen sammeln."""
        self._all_notes.clear()
        if not self.piece:
            return

        for part in self.piece.parts:
            abs_beat = 0.0
            for measure in part.measures:
                for note in measure.notes:
                    abs_start = abs_beat + note.start_beat
                    self._all_notes.append((abs_start, note, part.channel))
                abs_beat += measure.duration_beats

            self.transport.set_end_beat(abs_beat)

        self._all_notes.sort(key=lambda x: x[0])

    def play(self) -> None:
        self.transport.play()
        self.signal_bus.playback_started.emit()

    def pause(self) -> None:
        self.transport.pause()
        self.player.all_notes_off()

    def stop(self) -> None:
        self.transport.stop()
        self.player.all_notes_off()
        self._active_notes.clear()
        self.signal_bus.playback_stopped.emit()

    def _on_beat(self, current_beat: float) -> None:
        """Bei jedem Timer-Tick: Noten starten/stoppen."""
        self.signal_bus.playback_position.emit(current_beat)

        # Note-Ons
        for abs_beat, note, channel in self._all_notes:
            if self._last_beat <= abs_beat < current_beat:
                self._play_note(note, channel)

        # Note-Offs (aktive Noten prüfen)
        finished = []
        for midi_note, note_data in self._active_notes.items():
            abs_beat, note, channel = note_data
            if current_beat >= abs_beat + note.duration_beats * note.expression.duration_deviation:
                self.player.note_off(channel, midi_note)
                finished.append(midi_note)

        for midi_note in finished:
            del self._active_notes[midi_note]

        self._last_beat = current_beat

    def _play_note(self, note: Note, channel: int) -> None:
        """Eine Note mit Expression abspielen."""
        # Pitch Bend für Cent-Offset
        if abs(note.expression.cent_offset) > 0.5:
            bend = cents_to_pitch_bend(note.expression.cent_offset)
            self.player.set_pitch_bend(channel, bend)
        else:
            self.player.set_pitch_bend(channel, 8192)  # Reset

        # Note On
        vel = note.expression.velocity
        self.player.note_on(channel, note.pitch, vel)

        # Für Note-Off tracking
        abs_beat = self.transport.current_beat
        self._active_notes[note.pitch] = (abs_beat, note, channel)

    def _on_state_changed(self, state: str) -> None:
        if state == "stopped":
            self._last_beat = 0.0

    def load_soundfont(self, path: str) -> bool:
        return self.player.load_soundfont(path)

    def shutdown(self) -> None:
        self.stop()
        self.player.shutdown()
