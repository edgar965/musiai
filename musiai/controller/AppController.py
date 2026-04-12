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

        # --- Playback Position → Playhead ---
        self.signal_bus.playback_position.connect(
            self.notation_scene.update_playhead
        )
        self.signal_bus.playback_stopped.connect(
            self.notation_scene.hide_playhead
        )

        # --- Note changed → Refresh ---
        self.signal_bus.note_changed.connect(self._on_note_changed)

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
            self.notation_scene.clear_measure_highlight()
            self.main_window.properties_panel.show_note(note)

    def _on_measure_clicked(self, measure) -> None:
        """Klick in Takt-Bereich → Takt selektieren, Properties zeigen."""
        self.notation_scene.highlight_measure(measure)
        self.edit_controller.select_measure(measure)
        tempo = self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
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
        """Tempo geändert → NUR den selektierten Takt oder globales Tempo."""
        piece = self.notation_scene.piece
        if not piece:
            return

        sel_measure = self.edit_controller.selected_measure
        from musiai.model.Tempo import Tempo

        if sel_measure:
            # Nur diesen Takt ändern
            sel_measure.tempo = Tempo(bpm, 0)
        else:
            # Kein Takt selektiert → globales Tempo
            if piece.tempos:
                piece.tempos[0].bpm = bpm

        self.playback_engine.transport.tempo_bpm = bpm

        # Selektion nach refresh wiederherstellen
        self.notation_scene.refresh()
        if sel_measure:
            self.notation_scene.highlight_measure(sel_measure)
        self.signal_bus.status_message.emit(f"Tempo: {bpm:.0f} BPM")
        logger.info(f"Tempo → {bpm:.0f} BPM")

    def _on_deselect(self) -> None:
        """Escape (outside edit mode): Alles deselektieren."""
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
        # Takt-Selektion aufheben damit Tempo global geändert wird
        self.edit_controller.deselect()
        self.notation_scene.clear_measure_highlight()
        tempo = piece.initial_tempo
        # Zeige Taktart-Panel mit globalem Tempo (kein Takt selektiert)
        ts = piece.parts[0].measures[0].time_signature if piece.parts else None
        if ts:
            self.main_window.properties_panel.show_time_signature(ts, tempo)
        self.signal_bus.status_message.emit(
            f"Globales Tempo: {tempo:.0f} BPM (gilt für alle Takte)"
        )

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
