"""AppController - Zentraler Controller, verkabelt alle Komponenten."""

import logging
from PySide6.QtWidgets import QFileDialog
from musiai.model.Project import Project
from musiai.util.SignalBus import SignalBus
from musiai.notation.NotationScene import NotationScene
from musiai.ui.MainWindow import MainWindow
from musiai.controller.FileController import FileController
from musiai.controller.EditController import EditController
from musiai.controller.RecordingController import RecordingController
from musiai.audio.PlaybackEngine import PlaybackEngine
from musiai.midi.MidiKeyboard import MidiKeyboard
from musiai.midi.MidiMapping import MidiMapping
from musiai.midi.MidiExporter import MidiExporter
from musiai.ui.MidiDeviceDialog import MidiDeviceDialog
from musiai.ui.SoundfontDialog import SoundfontDialog

logger = logging.getLogger("musiai.controller.AppController")


class AppController:
    """Zentraler Controller - erstellt und verbindet alle Komponenten."""

    def __init__(self):
        self.project = Project()
        self.signal_bus = SignalBus()
        self.notation_scene = NotationScene()

        # MIDI
        self.midi_keyboard = MidiKeyboard()
        self.midi_mapping = MidiMapping()
        self.midi_exporter = MidiExporter()

        # Audio
        self.playback_engine = PlaybackEngine(self.signal_bus)

        # UI
        self.main_window = MainWindow()
        self.main_window.set_notation_scene(self.notation_scene)

        # Controller
        self.file_controller = FileController(
            self.project, self.signal_bus, self.main_window
        )
        self.edit_controller = EditController(
            self.notation_scene, self.signal_bus
        )
        self.recording_controller = RecordingController(
            self.midi_keyboard, self.midi_mapping,
            self.playback_engine.transport, self.signal_bus,
        )

        self._tempo_target_measure = None
        self._detection_engine = "demucs+pyin"  # Default: beste verfügbare
        self._connect_signals()
        logger.info("AppController initialisiert")

    def _connect_signals(self) -> None:
        """Alle Signals mit Slots verbinden."""
        toolbar = self.main_window.toolbar
        props = self.main_window.properties_panel

        # --- Datei ---
        toolbar.import_midi_clicked.connect(self.file_controller.import_midi)
        toolbar.import_musicxml_clicked.connect(self.file_controller.import_musicxml)
        toolbar.save_project_clicked.connect(self.file_controller.save_project)
        toolbar.load_project_clicked.connect(self.file_controller.load_project)
        toolbar.export_midi_clicked.connect(self._export_midi)
        self.main_window._save_music_action.triggered.connect(
            self.file_controller.save_music
        )
        self.main_window._save_music_as_action.triggered.connect(
            self.file_controller.save_music_as
        )

        # --- Zoom ---
        toolbar.zoom_in_clicked.connect(self.main_window.notation_view.zoom_in)
        toolbar.zoom_out_clicked.connect(self.main_window.notation_view.zoom_out)

        # --- Transport ---
        toolbar.play_clicked.connect(self._on_play)
        self.main_window._play_pause_action.triggered.connect(self._on_play_pause)
        toolbar.pause_clicked.connect(self.playback_engine.pause)
        toolbar.stop_clicked.connect(self._on_stop)

        # --- Recording ---
        toolbar.record_clicked.connect(self.recording_controller.toggle_recording)

        # --- MIDI Device ---
        toolbar.midi_device_clicked.connect(self._show_midi_dialog)

        # --- Einstellungen ---
        self.main_window._settings_action.triggered.connect(self._show_settings)

        # --- Audio Backend ---
        self.main_window._backend_gm_action.triggered.connect(
            lambda: self._switch_backend("windows_gm")
        )
        self.main_window._backend_sf_action.triggered.connect(
            self._load_global_soundfont
        )
        self.main_window._backend_port_action.triggered.connect(
            self._select_midi_port
        )

        # --- Piece geladen ---
        self.signal_bus.piece_loaded.connect(self._on_piece_loaded)

        # --- Status ---
        self.signal_bus.status_message.connect(self.main_window.status_bar.set_message)

        # --- Selection ---
        view = self.main_window.notation_view
        view.note_clicked.connect(self.edit_controller.select_note)
        view.measure_clicked.connect(self._on_measure_clicked)
        view.clef_clicked.connect(self._on_clef_clicked)
        view.time_sig_clicked.connect(self._on_ts_clicked_from_view)
        view.tempo_clicked.connect(self._on_tempo_clicked)
        view.part_label_clicked.connect(self._on_part_label_clicked)
        view.part_mute_clicked.connect(self._on_part_mute_clicked)
        view.part_detect_requested.connect(self._on_part_detect)
        view.part_delete_requested.connect(self._on_part_delete)

        # --- Stimm-Properties ---
        props.part_instrument_changed.connect(self._on_part_instrument_changed)
        props.part_muted_changed.connect(self._on_part_muted_changed)
        props.part_name_changed.connect(self._on_part_name_changed)
        props.part_soundfont_requested.connect(self._on_part_soundfont)
        props.part_delete_requested.connect(self._on_part_delete)
        props.part_detect_requested.connect(self._on_part_detect)
        view.deselect_requested.connect(self._on_deselect)
        self.signal_bus.note_selected.connect(self._on_note_selected)
        self.signal_bus.notes_deselected.connect(props.clear)

        # --- Edit Mode ---
        view.edit_mode_changed.connect(self._on_edit_mode_changed)
        view.cursor_moved.connect(self._on_cursor_moved)
        view.copy_requested.connect(self.edit_controller.copy)
        view.paste_requested.connect(self._on_paste)

        # --- Properties → Edit ---
        props.velocity_changed.connect(self.edit_controller.change_velocity)
        props.cent_offset_changed.connect(
            lambda c: self.edit_controller.change_cent_offset(
                c, props._glide_combo.currentText()
            )
        )
        props.duration_changed.connect(self.edit_controller.change_duration_deviation)
        props.glide_type_changed.connect(self._on_glide_type_changed)
        props.tempo_changed.connect(self._on_tempo_changed)

        # --- Delete ---
        self.main_window._delete_action.triggered.connect(
            self.edit_controller.delete_selected
        )

        # --- Neue Stimme ---
        self.main_window._new_voice_action.triggered.connect(self._add_new_voice)
        self.main_window._new_audio_action.triggered.connect(self._add_audio_voice)

        # --- Playback Position → Playhead ---
        self.signal_bus.playback_position.connect(
            self.notation_scene.update_playhead
        )
        self.signal_bus.playback_stopped.connect(
            self.notation_scene.hide_playhead
        )

        # --- Note changed → Refresh ---
        self.signal_bus.note_changed.connect(self._on_note_changed)
        self.signal_bus.piece_changed.connect(
            self.playback_engine._prepare_note_list
        )

        # --- MIDI Keyboard Status ---
        self.midi_keyboard.connected.connect(
            lambda p: self.main_window.status_bar.set_midi_status(True, p)
        )
        self.midi_keyboard.disconnected.connect(
            lambda: self.main_window.status_bar.set_midi_status(False)
        )

        logger.debug("Alle Signals verbunden")

    def _on_piece_loaded(self, piece) -> None:
        logger.info(f"Piece geladen: '{piece.title}'")
        self.notation_scene.set_piece(piece)
        self.playback_engine.set_piece(piece)
        self.recording_controller.set_piece(piece)
        self.main_window.setWindowTitle(f"MusiAI - {piece.title}")

    def _on_play(self) -> None:
        if not self.playback_engine.piece:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return
        self.playback_engine.play()
        self.signal_bus.status_message.emit("Wiedergabe...")

    def _on_play_pause(self) -> None:
        """Space-Taste: Play/Pause Toggle."""
        if not self.playback_engine.piece:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return
        if self.playback_engine.transport.state == "playing":
            self.playback_engine.pause()
            self.signal_bus.status_message.emit("Pause")
        else:
            self.playback_engine.play()
            self.signal_bus.status_message.emit("Wiedergabe...")

    def _on_stop(self) -> None:
        self.playback_engine.stop()
        self.signal_bus.status_message.emit("Gestoppt")

    def _export_midi(self) -> None:
        piece = self.project.current_piece
        if not piece:
            self.signal_bus.status_message.emit("Kein Stück zum Exportieren")
            return
        path, _ = QFileDialog.getSaveFileName(
            self.main_window, "MIDI exportieren", "media/music",
            "MIDI Dateien (*.mid);;Alle Dateien (*)"
        )
        if path:
            self.midi_exporter.export_file(piece, path)
            self.signal_bus.status_message.emit(f"MIDI exportiert: {path}")

    def _switch_backend(self, name: str) -> None:
        if self.playback_engine.switch_backend(name):
            mw = self.main_window
            mw._backend_gm_action.setChecked(name == "windows_gm")
            if self.playback_engine.piece:
                self.playback_engine.set_piece(self.playback_engine.piece)
            self.signal_bus.status_message.emit(f"Audio: {name}")

    def _load_global_soundfont(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "SoundFont laden", "media/soundfonts",
            "SoundFont Dateien (*.sf2);;Alle Dateien (*)"
        )
        if path and self.playback_engine.load_soundfont(path):
            self.main_window._backend_gm_action.setChecked(False)
            if self.playback_engine.piece:
                self.playback_engine.set_piece(self.playback_engine.piece)
            self.signal_bus.status_message.emit(
                f"SoundFont: {path.split('/')[-1].split(chr(92))[-1]}"
            )

    def _select_midi_port(self) -> None:
        ports = self.playback_engine.list_midi_ports()
        if not ports:
            self.signal_bus.status_message.emit("Keine MIDI-Ports gefunden")
            return
        from PySide6.QtWidgets import QInputDialog
        names = [f"{pid}: {name}" for pid, name in ports]
        choice, ok = QInputDialog.getItem(
            self.main_window, "MIDI-Port wählen",
            "Ziel-Port (z.B. loopMIDI für HALion):", names, 0, False
        )
        if ok and choice:
            port_id = int(choice.split(":")[0])
            if self.playback_engine.connect_midi_port(port_id):
                self.main_window._backend_gm_action.setChecked(False)
                self.signal_bus.status_message.emit(f"MIDI-Port: {choice}")

    def _show_settings(self) -> None:
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog(self.main_window)
        # Aktuelle Engine vorselektieren
        if dialog._engines.get(self._detection_engine):
            dialog._engines[self._detection_engine].setChecked(True)
        if dialog.exec():
            self._detection_engine = dialog.selected_engine
            logger.info(f"Erkennungs-Engine: {self._detection_engine}")

    def _show_midi_dialog(self) -> None:
        dialog = MidiDeviceDialog(self.midi_keyboard, self.main_window)
        dialog.exec()

    def _on_glide_type_changed(self, glide_type: str) -> None:
        note = self.edit_controller.selected_note
        if note:
            self.edit_controller.change_cent_offset(
                note.expression.cent_offset, glide_type
            )

    def _on_note_selected(self, note) -> None:
        """Note ausgewählt → Properties Panel anzeigen, Takt-Highlight entfernen."""
        if note:
            self._tempo_target_measure = None
            self.notation_scene.clear_measure_highlight()
            self.main_window.properties_panel.show_note(note)

    def _on_measure_clicked(self, measure) -> None:
        """Klick in Takt-Bereich → Takt selektieren, Properties zeigen."""
        self.notation_scene.highlight_measure(measure)
        self.edit_controller.select_measure(measure)
        # Tempo dieses Takts anzeigen (per-Takt oder global)
        tempo = measure.tempo.bpm if measure.tempo else (
            self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
        )
        self._tempo_target_measure = measure
        self.main_window.properties_panel.show_time_signature(
            measure.time_signature, tempo
        )
        self.signal_bus.status_message.emit(
            f"Takt {measure.number} ausgewählt ({len(measure.notes)} Noten)"
        )

    def _on_edit_mode_changed(self, active: bool) -> None:
        """Edit Mode ein/aus."""
        self.main_window.status_bar.set_edit_mode(active)
        if active:
            self.notation_scene.update_cursor(
                self.main_window.notation_view.cursor_beat
            )
            self.signal_bus.status_message.emit(
                "Edit Mode — Pfeiltasten/Mausklick: Cursor bewegen, "
                "Ctrl+C/V: Copy/Paste, Esc: beenden"
            )
        else:
            self.notation_scene.hide_cursor()
            self.signal_bus.status_message.emit("Edit Mode beendet")

    def _on_cursor_moved(self, beat: float) -> None:
        """Edit-Cursor wurde bewegt."""
        self.notation_scene.update_cursor(beat)
        # Finde Takt + lokalen Beat für Statusanzeige
        measure_num, local_beat = self._beat_to_measure_info(beat)
        self.main_window.status_bar.set_position(measure_num, local_beat)

    def _on_paste(self) -> None:
        """Paste an der Cursor-Position im Edit Mode."""
        view = self.main_window.notation_view
        if not view.edit_mode:
            return
        beat = view.cursor_beat
        target_measure, local_beat = self._find_measure_at_beat(beat)
        self.edit_controller.paste_at(target_measure, local_beat)

    def _beat_to_measure_info(self, global_beat: float) -> tuple[int, float]:
        """Globaler Beat → (Taktnummer, lokaler Beat)."""
        piece = self.notation_scene.piece
        if not piece or not piece.parts:
            return 1, global_beat
        cumulative = 0.0
        for m in piece.parts[0].measures:
            dur = m.duration_beats
            if global_beat < cumulative + dur:
                return m.number, global_beat - cumulative
            cumulative += dur
        # Hinter dem letzten Takt
        last = piece.parts[0].measures[-1]
        return last.number, global_beat - (cumulative - last.duration_beats)

    def _find_measure_at_beat(self, global_beat: float):
        """Globaler Beat → (Measure, lokaler Beat)."""
        from musiai.model.Measure import Measure
        piece = self.notation_scene.piece
        if not piece or not piece.parts:
            return None, 0.0
        cumulative = 0.0
        for m in piece.parts[0].measures:
            dur = m.duration_beats
            if global_beat < cumulative + dur:
                return m, global_beat - cumulative
            cumulative += dur
        last = piece.parts[0].measures[-1]
        return last, global_beat - (cumulative - last.duration_beats)

    def _on_tempo_changed(self, bpm: float) -> None:
        """Tempo geändert → NUR den Ziel-Takt oder globales Tempo.

        _tempo_target_measure bestimmt, was geändert wird:
          - None → globales Tempo (piece.tempos[0])
          - Measure → nur dieser Takt (measure.tempo)
        """
        piece = self.notation_scene.piece
        if not piece:
            return

        from musiai.model.Tempo import Tempo
        target = self._tempo_target_measure

        if target:
            # NUR diesen einen Takt ändern
            target.tempo = Tempo(bpm, 0)
            logger.info(f"Takt {target.number} Tempo → {bpm:.0f} BPM")
        else:
            # Globales Tempo für alle Takte
            if piece.tempos:
                piece.tempos[0].bpm = bpm
            # Auch alle per-Takt-Tempos aktualisieren
            for part in piece.parts:
                for m in part.measures:
                    if m.tempo:
                        m.tempo.bpm = bpm
            logger.info(f"Globales Tempo → {bpm:.0f} BPM")

        self.playback_engine.transport.tempo_bpm = bpm
        self.notation_scene.refresh()
        if target:
            self.notation_scene.highlight_measure(target)
        self.signal_bus.status_message.emit(
            f"Tempo: {bpm:.0f} BPM ({'Takt ' + str(target.number) if target else 'global'})"
        )

    def _on_deselect(self) -> None:
        """Escape (outside edit mode): Alles deselektieren."""
        self._tempo_target_measure = None
        self.edit_controller.deselect()
        self.notation_scene.clear_measure_highlight()
        self.main_window.properties_panel.clear()
        self.signal_bus.status_message.emit("Auswahl aufgehoben")

    def _on_note_changed(self, note) -> None:
        """Note wurde geändert → Panel updaten falls selektiert."""
        if self.edit_controller.selected_note is note:
            self.main_window.properties_panel.show_note(note)

    def _add_new_voice(self) -> None:
        """Neue Stimme (Part) zum aktuellen Piece hinzufügen."""
        piece = self.project.current_piece
        if not piece:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return

        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.TimeSignature import TimeSignature

        part_num = len(piece.parts) + 1
        new_part = Part(name=f"Stimme {part_num}", channel=min(part_num, 15))

        # Gleiche Taktanzahl wie erste Stimme, leere Takte
        if piece.parts:
            for i, existing in enumerate(piece.parts[0].measures):
                m = Measure(
                    number=existing.number,
                    time_signature=TimeSignature(
                        existing.time_signature.numerator,
                        existing.time_signature.denominator,
                    ),
                )
                new_part.add_measure(m)
        else:
            new_part.add_measure(Measure(number=1))

        piece.add_part(new_part)
        self.notation_scene.refresh()
        self.signal_bus.status_message.emit(
            f"Neue Stimme '{new_part.name}' hinzugefügt"
        )
        logger.info(f"Neue Stimme: {new_part.name} (Part {part_num})")

    def _on_tempo_clicked(self) -> None:
        """Tempo-Anzeige angeklickt → Globales Tempo editieren."""
        piece = self.notation_scene.piece
        if not piece:
            return
        self.edit_controller.deselect()
        self.notation_scene.clear_measure_highlight()
        self._tempo_target_measure = None  # Global
        tempo = piece.initial_tempo
        ts = piece.parts[0].measures[0].time_signature if piece.parts else None
        if ts:
            self.main_window.properties_panel.show_time_signature(ts, tempo)
        self.signal_bus.status_message.emit(
            f"Globales Tempo: {tempo:.0f} BPM (gilt für alle Takte)"
        )

    def _add_audio_voice(self) -> None:
        """Audio-Datei laden und als neue Stimme hinzufügen."""
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Audio laden", "media/music",
            "Audio Dateien (*.wav *.mp3 *.flac *.ogg);;Alle Dateien (*)"
        )
        if not path:
            return

        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure

        track = AudioTrack()
        if not track.load(path):
            self.signal_bus.status_message.emit("Audio laden fehlgeschlagen")
            return

        piece = self.notation_scene.piece
        if not piece:
            from musiai.model.Piece import Piece
            piece = Piece("Audio Import")
            self.project.add_piece(piece)

        # Neue Stimme mit Audio
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        part = Part(name=f"Audio: {name}", channel=len(piece.parts))
        part.audio_track = track

        # Leere Takte anlegen (Dauer = Audio-Dauer)
        tempo = piece.initial_tempo
        beats = track.duration_seconds * (tempo / 60.0)
        from musiai.model.TimeSignature import TimeSignature
        ts = TimeSignature(4, 4)
        n_measures = max(1, int(beats / ts.beats_per_measure()) + 1)
        for i in range(n_measures):
            part.add_measure(Measure(i + 1, ts))

        piece.add_part(part)
        # Playback-Engine aktualisieren (Audio-Track registrieren)
        self.playback_engine.set_piece(piece)
        self.notation_scene.refresh()
        self.signal_bus.status_message.emit(
            f"Audio-Stimme '{part.name}' geladen ({track.duration_seconds:.1f}s)"
        )

    def _on_part_delete(self, part_idx: int) -> None:
        """Stimme löschen."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        if len(piece.parts) <= 1:
            self.signal_bus.status_message.emit("Letzte Stimme kann nicht gelöscht werden")
            return
        name = piece.parts[part_idx].name
        del piece.parts[part_idx]
        self.main_window.properties_panel.clear()
        self.notation_scene.refresh()
        self.signal_bus.status_message.emit(f"Stimme '{name}' gelöscht")

    def _on_part_detect(self, part_idx: int) -> None:
        """Noten aus Audio erkennen mit gewählter Engine."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        if not part.audio_track or not part.audio_track.file_path:
            self.signal_bus.status_message.emit("Keine Audio-Daten vorhanden")
            return

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        engine = self._detection_engine
        self.signal_bus.status_message.emit(f"Erkenne Noten ({engine})...")
        QApplication.processEvents()

        try:
            if engine == "demucs+pyin":
                self._detect_demucs(part, piece)
            else:
                self._detect_pyin(part, piece)
        except Exception as e:
            logger.error(f"Erkennung fehlgeschlagen: {e}", exc_info=True)
            self.signal_bus.status_message.emit(f"Fehler: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _detect_pyin(self, part, piece) -> None:
        """Monophone Erkennung mit pyin."""
        from musiai.audio.PitchDetector import PitchDetector
        import numpy as np, librosa

        all_samples = np.concatenate([b.samples for b in part.audio_track.blocks])
        sr = part.audio_track.sr
        if len(all_samples) > sr * 30:
            all_samples = all_samples[:sr * 30]
        if sr != 22050:
            all_samples = librosa.resample(all_samples, orig_sr=sr, target_sr=22050)
            sr = 22050

        detector = PitchDetector(piece.initial_tempo)
        notes = detector.detect(all_samples, sr)
        if notes:
            self._add_detected_part(piece, f"Erkannt: {part.name}", notes)
        else:
            self.signal_bus.status_message.emit("Keine Noten erkannt")

    def _detect_demucs(self, part, piece) -> None:
        """Polyphone Erkennung: demucs trennt → pyin pro Stimme."""
        from musiai.audio.DemucsDetector import DemucsDetector

        detector = DemucsDetector(
            tempo_bpm=piece.initial_tempo, beats_per_measure=4.0
        )
        results = detector.detect(part.audio_track.file_path)

        if not results:
            self.signal_bus.status_message.emit("Keine Noten erkannt")
            return

        total = 0
        for stem_name, notes in results.items():
            self._add_detected_part(
                piece, f"{stem_name}: {part.name}", notes
            )
            total += len(notes)

        self.notation_scene.refresh()
        self.signal_bus.status_message.emit(
            f"{total} Noten in {len(results)} Stimmen erkannt"
        )

    def _add_detected_part(self, piece, name: str,
                           notes_data: list[dict]) -> None:
        """Erkannte Noten als neue Stimme hinzufügen."""
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        from musiai.model.TimeSignature import TimeSignature

        new_part = Part(name=name, channel=min(len(piece.parts), 15))
        ts = TimeSignature(4, 4)
        bpm = ts.beats_per_measure()

        max_beat = max(n["start_beat"] + n["duration_beats"] for n in notes_data)
        n_measures = max(1, int(max_beat / bpm) + 1)
        for i in range(n_measures):
            new_part.add_measure(Measure(i + 1, ts))

        for nd in notes_data:
            m_idx = min(int(nd["start_beat"] / bpm), n_measures - 1)
            local = nd["start_beat"] - m_idx * bpm
            expr = Expression(velocity=nd["velocity"], cent_offset=nd["cent_offset"])
            note = Note(nd["pitch"], local, nd["duration_beats"], expr)
            new_part.measures[m_idx].add_note(note)

        piece.add_part(new_part)
        self.notation_scene.refresh()
        self.signal_bus.status_message.emit(
            f"{len(notes_data)} Noten → '{name}'"
        )

    def _on_part_label_clicked(self, part_idx: int) -> None:
        """Stimm-Label angeklickt → Eigenschaften im Panel zeigen."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        self.edit_controller.deselect()
        self.notation_scene.clear_measure_highlight()
        self.main_window.properties_panel.show_part(part, part_idx)
        self.signal_bus.status_message.emit(
            f"Stimme '{part.name}' (Kanal {part.channel})"
        )

    def _on_part_mute_clicked(self, part_idx: int) -> None:
        """Mute-Icon angeklickt → Mute togglen."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.muted = not part.muted
        # Audio-Spur muten/unmuten
        if part.audio_track:
            self.playback_engine.audio_player.set_muted(part.muted)
        self.notation_scene.refresh()
        status = "stumm" if part.muted else "aktiv"
        self.signal_bus.status_message.emit(f"Stimme '{part.name}': {status}")

    def _on_part_instrument_changed(self, part_idx: int, program: int) -> None:
        """Instrument geändert → MIDI Program setzen."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.instrument = program
        self.playback_engine.player.set_instrument(part.channel, 0, program)
        self.signal_bus.status_message.emit(
            f"Stimme '{part.name}': Instrument → Program {program}"
        )

    def _on_part_muted_changed(self, part_idx: int, muted: bool) -> None:
        """Mute über Properties Panel geändert."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.muted = muted
        if part.audio_track:
            self.playback_engine.audio_player.set_muted(muted)
        self.notation_scene.refresh()

    def _on_part_name_changed(self, part_idx: int, name: str) -> None:
        """Stimm-Name geändert."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        piece.parts[part_idx].name = name
        self.notation_scene.refresh()

    def _on_part_soundfont(self, part_idx: int) -> None:
        """SoundFont für Stimme laden."""
        piece = self.notation_scene.piece
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "SoundFont laden", "media/soundfonts",
            "SoundFont Dateien (*.sf2);;Alle Dateien (*)"
        )
        if not path:
            return
        if self.playback_engine.load_soundfont(path):
            self.playback_engine.set_soundfont_for_part(
                part.channel, path, part.instrument
            )
            self.main_window.properties_panel._sf_label.setText(
                path.split("/")[-1].split("\\")[-1]
            )
            self.signal_bus.status_message.emit(
                f"SoundFont geladen für '{part.name}'"
            )
        else:
            self.signal_bus.status_message.emit("SoundFont konnte nicht geladen werden")

    def _on_clef_clicked(self, measure) -> None:
        """Schlüssel angeklickt → Properties zeigen."""
        self.main_window.properties_panel.show_clef()
        self.signal_bus.status_message.emit("Notenschlüssel ausgewählt")

    def _on_ts_clicked_from_view(self, measure) -> None:
        """Taktart in Notation angeklickt → Properties zeigen."""
        tempo = self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
        self.main_window.properties_panel.show_time_signature(
            measure.time_signature, tempo
        )
        self.signal_bus.status_message.emit(
            f"Taktart {measure.time_signature} ausgewählt"
        )

    def _on_ts_clicked(self, ts_item) -> None:
        """Taktart angeklickt → Properties zeigen (legacy)."""
        ts = ts_item.time_sig
        tempo = self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
        self.main_window.properties_panel.show_time_signature(ts, tempo)

    def _load_default_file(self) -> None:
        """Standard-Datei beim Start laden wenn vorhanden."""
        import os
        default = os.path.abspath("media/music/test.musicxml")
        if os.path.exists(default):
            try:
                from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
                piece = MusicXmlImporter().import_file(default)
                self.project.add_piece(piece)
                self.signal_bus.piece_loaded.emit(piece)
                logger.info(f"Standard-Datei geladen: {default}")
            except Exception as e:
                logger.warning(f"Standard-Datei konnte nicht geladen werden: {e}")

    def start(self) -> None:
        """App starten."""
        self.main_window.show()
        self._load_default_file()
        if not self.project.current_piece:
            self.signal_bus.status_message.emit("Bereit. MIDI oder MusicXML importieren.")
        logger.info("MusiAI gestartet")

    def shutdown(self) -> None:
        """Aufräumen beim Beenden."""
        self.playback_engine.shutdown()
        self.midi_keyboard.shutdown()
        logger.info("MusiAI beendet")
