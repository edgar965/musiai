"""PlaybackEngine - Orchestriert Playback mit wählbarem Audio-Backend."""

import logging
from musiai.model.Piece import Piece
from musiai.model.Note import Note
from musiai.audio.Transport import Transport
from musiai.audio.FluidSynthPlayer import FluidSynthPlayer
from musiai.util.PitchUtils import cents_to_pitch_bend
from musiai.util.SignalBus import SignalBus

logger = logging.getLogger("musiai.audio.PlaybackEngine")


class PlaybackEngine:
    """Spielt ein Piece ab mit wählbarem Backend.

    Backends:
      - "windows_gm": Windows GS Wavetable Synth (pygame.midi)
      - "soundfont":   FluidSynth mit .sf2 SoundFonts
      - "midi_port":   Externer MIDI-Port (z.B. HALion via loopMIDI)
    """

    def __init__(self, signal_bus: SignalBus):
        self.signal_bus = signal_bus
        self.transport = Transport()
        self.piece: Piece | None = None
        self._backend_name = "windows_gm"

        # Standard-Backend: Windows GS Wavetable
        self.player = FluidSynthPlayer()
        self._sf_player = None   # SoundFontPlayer (lazy)
        self._port_player = None  # MidiPortPlayer (lazy)

        # Audio-Player für mp3/wav Spuren
        from musiai.audio.AudioPlayer import AudioPlayer
        self.audio_player = AudioPlayer()

        # Tracking
        self._active_notes: dict[int, tuple] = {}
        self._last_beat = 0.0
        self._all_notes: list[tuple[float, Note, int, object]] = []

        self.transport.position_changed.connect(self._on_beat)
        self.transport.state_changed.connect(self._on_state_changed)

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def switch_backend(self, name: str) -> bool:
        """Backend wechseln. Gibt True zurück bei Erfolg."""
        self.stop()

        if name == "windows_gm":
            self.player = FluidSynthPlayer()
            self._backend_name = name
            logger.info("Backend: Windows GS Wavetable Synth")
            return True

        if name == "soundfont":
            if not self._sf_player:
                from musiai.audio.SoundFontPlayer import SoundFontPlayer
                self._sf_player = SoundFontPlayer()
            if self._sf_player.is_available:
                self.player = self._sf_player
                self._backend_name = name
                logger.info("Backend: FluidSynth SoundFont")
                return True
            logger.warning("FluidSynth nicht verfügbar")
            return False

        if name == "midi_port":
            if not self._port_player:
                from musiai.audio.MidiPortPlayer import MidiPortPlayer
                self._port_player = MidiPortPlayer()
            self.player = self._port_player
            self._backend_name = name
            logger.info("Backend: Externer MIDI Port")
            return True

        logger.warning(f"Unbekanntes Backend: {name}")
        return False

    def load_soundfont(self, path: str) -> bool:
        """SoundFont laden (wechselt automatisch zum SoundFont-Backend)."""
        if not self._sf_player:
            from musiai.audio.SoundFontPlayer import SoundFontPlayer
            self._sf_player = SoundFontPlayer()
        if not self._sf_player.is_available:
            return False
        sfid = self._sf_player.load_soundfont(path)
        if sfid is not None:
            self.switch_backend("soundfont")
            # Default: alle Kanäle auf diesen SoundFont
            for ch in range(16):
                self._sf_player.set_instrument(ch, sfid, 0, 0)
            return True
        return False

    def set_soundfont_for_part(self, part_channel: int,
                               sfont_path: str, program: int) -> None:
        """SoundFont + Program für eine bestimmte Stimme setzen."""
        if not self._sf_player or not self._sf_player.is_available:
            return
        sfid = self._sf_player.load_soundfont(sfont_path)
        if sfid is not None:
            self._sf_player.set_instrument(part_channel, sfid, 0, program)

    def connect_midi_port(self, port_id: int) -> bool:
        """Mit einem externen MIDI-Port verbinden."""
        if not self._port_player:
            from musiai.audio.MidiPortPlayer import MidiPortPlayer
            self._port_player = MidiPortPlayer()
        if self._port_player.connect(port_id):
            self.switch_backend("midi_port")
            return True
        return False

    def list_midi_ports(self) -> list[tuple[int, str]]:
        from musiai.audio.MidiPortPlayer import MidiPortPlayer
        return MidiPortPlayer.list_output_ports()

    # ---- Piece / Playback ----

    def set_piece(self, piece: Piece) -> None:
        self.piece = piece
        self.transport.tempo_bpm = piece.initial_tempo
        self._prepare_note_list()
        self._prepare_audio_tracks()
        for part in piece.parts:
            self.player.set_instrument(part.channel, 0, part.instrument)
        logger.info(f"Playback vorbereitet: {len(self._all_notes)} Noten")

    def _prepare_audio_tracks(self) -> None:
        """Audio-Tracks aus Parts registrieren."""
        self.audio_player._tracks.clear()
        if not self.piece:
            return
        for i, part in enumerate(self.piece.parts):
            if part.audio_track and part.audio_track.file_path:
                self.audio_player.set_track(i, part.audio_track.file_path)
                if part.muted:
                    self.audio_player.set_muted(True)

    def _prepare_note_list(self) -> None:
        self._all_notes.clear()
        if not self.piece:
            return
        for part in self.piece.parts:
            abs_beat = 0.0
            for measure in part.measures:
                for note in measure.notes:
                    abs_start = abs_beat + note.start_beat
                    self._all_notes.append((abs_start, note, part.channel, part))
                # Taktart-Dauer statt effective (verhindert Drift durch Expression)
                abs_beat += measure.duration_beats
            self.transport.set_end_beat(abs_beat)
        self._all_notes.sort(key=lambda x: x[0])

    def play(self) -> None:
        if self.transport.state == "paused":
            self.audio_player.unpause()
        else:
            # Beat → Sekunden für Audio-Start
            beat = self.transport.current_beat
            sec = beat * 60.0 / self.transport.tempo_bpm
            self.audio_player.play(sec)
        self.transport.play()
        self.signal_bus.playback_started.emit()

    def pause(self) -> None:
        self.transport.pause()
        self.player.all_notes_off()
        self.audio_player.pause()

    def stop(self) -> None:
        self.transport.stop()
        self.player.all_notes_off()
        self.audio_player.stop()
        self._active_notes.clear()
        self.signal_bus.playback_stopped.emit()

    def _on_beat(self, current_beat: float) -> None:
        self.signal_bus.playback_position.emit(current_beat)

        for abs_beat, note, channel, part in self._all_notes:
            if self._last_beat <= abs_beat < current_beat:
                if not part.muted:
                    self._play_note(note, channel)

        finished = []
        for key, note_data in self._active_notes.items():
            abs_beat, note, channel = note_data
            eff_dur = note.duration_beats * note.expression.duration_deviation
            if current_beat >= abs_beat + eff_dur:
                self.player.note_off(channel, note.pitch)
                finished.append(key)
        for key in finished:
            del self._active_notes[key]

        self._last_beat = current_beat

    def _play_note(self, note: Note, channel: int) -> None:
        if abs(note.expression.cent_offset) > 0.5:
            bend = cents_to_pitch_bend(note.expression.cent_offset)
            self.player.set_pitch_bend(channel, bend)
        else:
            self.player.set_pitch_bend(channel, 8192)
        self.player.note_on(channel, note.pitch, note.expression.velocity)
        # Eindeutiger Key: id(note) statt pitch (mehrere gleiche Pitches möglich)
        self._active_notes[id(note)] = (
            self.transport.current_beat, note, channel
        )

    def _on_state_changed(self, state: str) -> None:
        if state == "stopped":
            self._last_beat = 0.0

    def shutdown(self) -> None:
        self.stop()
        self.player.shutdown()
        self.audio_player.shutdown()
        if self._sf_player and self._sf_player is not self.player:
            self._sf_player.shutdown()
        if self._port_player and self._port_player is not self.player:
            self._port_player.shutdown()
