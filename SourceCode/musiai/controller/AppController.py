"""AppController - Zentraler Controller, verkabelt alle Komponenten."""

import logging
from PySide6.QtWidgets import QFileDialog
from musiai.model.Project import Project
from musiai.util.SignalBus import SignalBus
from musiai.notation.NotationScene import NotationScene
from musiai.ui.MainWindow import MainWindow
from musiai.ui.DocumentTab import DocumentTab
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

        # MIDI
        self.midi_keyboard = MidiKeyboard()
        self.midi_mapping = MidiMapping()
        self.midi_exporter = MidiExporter()

        # Audio
        self.playback_engine = PlaybackEngine(self.signal_bus)

        # UI
        self.main_window = MainWindow()

        # Controller
        self.file_controller = FileController(
            self.project, self.signal_bus, self.main_window
        )
        self.recording_controller = RecordingController(
            self.midi_keyboard, self.midi_mapping,
            self.playback_engine.transport, self.signal_bus,
        )

        # Tab-Zustand
        self._active_tab: DocumentTab | None = None
        self._tempo_target_measure = None
        self._detection_engine = "demucs+pyin"
        self._pdf_import_engine = "audiveris"
        self._pdf_export_engine = "lilypond"

        self._connect_signals()
        logger.info("AppController initialisiert")

    # ------------------------------------------------------------------
    # Tab-Management
    # ------------------------------------------------------------------

    def _open_piece_in_tab(self, piece, file_path=None, file_type=None):
        """Neuen Tab für ein Piece erstellen und aktivieren."""
        scene = NotationScene()
        scene._source_file_path = file_path  # Für Verovio
        scene.set_piece(piece)

        from musiai.ui.NotationView import NotationView
        view = NotationView(scene)

        edit_ctrl = EditController(scene, self.signal_bus)
        doc_tab = DocumentTab(
            piece, scene, view, edit_ctrl, file_path, file_type
        )

        tab_widget = self.main_window.tab_widget
        tab_widget.add_document_tab(doc_tab)
        # currentChanged wird automatisch gefeuert → _on_tab_switched

    def _on_tab_switched(self, index: int) -> None:
        """Tab gewechselt → Signals umverdrahten."""
        tab_widget = self.main_window.tab_widget
        new_tab = tab_widget.document_tab_at(index)
        if new_tab is None or new_tab is self._active_tab:
            return

        old_tab = self._active_tab
        self._active_tab = new_tab

        # View-Signals umverdrahten
        if old_tab:
            self._wire_view(old_tab, connect=False)
            self._wire_playback(old_tab.notation_scene, connect=False)
        self._wire_view(new_tab, connect=True)
        self._wire_playback(new_tab.notation_scene, connect=True)

        # Engines aktualisieren
        self.playback_engine.set_piece(new_tab.piece)
        self.recording_controller.set_piece(new_tab.piece)

        # UI
        self._tempo_target_measure = None
        self.main_window.properties_panel.clear()
        self.main_window.setWindowTitle(f"MusiAI - {new_tab.title}")
        self.signal_bus.tab_activated.emit(new_tab)
        logger.info(f"Tab aktiviert: '{new_tab.title}'")

    def _on_tab_close(self, index: int) -> None:
        """Tab schließen."""
        tab_widget = self.main_window.tab_widget
        doc_tab = tab_widget.document_tab_at(index)
        if doc_tab is None:
            return

        # Wenn aktiver Tab geschlossen wird
        if doc_tab is self._active_tab:
            self._wire_view(doc_tab, connect=False)
            self._wire_playback(doc_tab.notation_scene, connect=False)
            self.playback_engine.stop()
            self._active_tab = None

        tab_widget.close_tab(index)
        self.signal_bus.tab_closed.emit(index)

        # Neuer aktiver Tab (currentChanged feuert automatisch)
        if tab_widget.tab_count() == 0:
            self.main_window.setWindowTitle("MusiAI - Music Expression Editor")
            self.main_window.properties_panel.clear()

    def _wire_view(self, doc_tab: DocumentTab, connect: bool = True) -> None:
        """View-Signals connecten oder disconnecten."""
        view = doc_tab.notation_view
        ec = doc_tab.edit_controller
        op = "connect" if connect else "disconnect"

        pairs = [
            (view.note_clicked, ec.select_note),
            (view.measure_clicked, self._on_measure_clicked),
            (view.clef_clicked, self._on_clef_clicked),
            (view.time_sig_clicked, self._on_ts_clicked_from_view),
            (view.tempo_clicked, self._on_tempo_clicked),
            (view.part_label_clicked, self._on_part_label_clicked),
            (view.part_mute_clicked, self._on_part_mute_clicked),
            (view.part_detect_requested, self._on_part_detect),
            (view.part_delete_requested, self._on_part_delete),
            (view.deselect_requested, self._on_deselect),
            (view.edit_mode_changed, self._on_edit_mode_changed),
            (view.cursor_moved, self._on_cursor_moved),
            (view.copy_requested, ec.copy),
            (view.paste_requested, self._on_paste),
            (view.play_from_beat_requested, self._play_from_beat),
        ]
        for signal, slot in pairs:
            getattr(signal, op)(slot)

    def _wire_playback(self, scene: NotationScene, connect: bool = True):
        """Playback-Position-Signals an Scene connecten/disconnecten."""
        op = "connect" if connect else "disconnect"
        getattr(self.signal_bus.playback_position, op)(scene.update_playhead)
        getattr(self.signal_bus.playback_stopped, op)(scene.hide_playhead)

    # ------------------------------------------------------------------
    # Signal-Verbindungen (einmalig)
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Alle Signals mit Slots verbinden."""
        toolbar = self.main_window.toolbar
        props = self.main_window.properties_panel
        tab_widget = self.main_window.tab_widget

        # --- Datei ---
        toolbar.import_midi_clicked.connect(self.file_controller.import_midi)
        toolbar.import_musicxml_clicked.connect(self.file_controller.import_musicxml)
        toolbar.import_pdf_clicked.connect(self._import_pdf)
        toolbar.save_project_clicked.connect(self.file_controller.save_project)
        toolbar.load_project_clicked.connect(self.file_controller.load_project)
        toolbar.export_midi_clicked.connect(self._export_midi)
        toolbar.export_pdf_clicked.connect(self._export_pdf)
        self.main_window._save_music_action.triggered.connect(
            self.file_controller.save_music
        )
        self.main_window._save_music_as_action.triggered.connect(
            self.file_controller.save_music_as
        )

        # --- Tabs ---
        tab_widget.currentChanged.connect(self._on_tab_switched)
        tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.main_window._close_tab_action.triggered.connect(
            lambda: self._on_tab_close(tab_widget.currentIndex())
        )

        # --- Zoom (delegiert an aktive View) ---
        toolbar.zoom_in_clicked.connect(self._zoom_in)
        toolbar.zoom_out_clicked.connect(self._zoom_out)

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

        # --- Render-Modus ---
        self.main_window.render_mode_changed.connect(self._on_render_mode_changed)

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

        # --- Stimm-Properties ---
        props.part_instrument_changed.connect(self._on_part_instrument_changed)
        props.part_muted_changed.connect(self._on_part_muted_changed)
        props.part_name_changed.connect(self._on_part_name_changed)
        props.part_soundfont_requested.connect(self._on_part_soundfont)
        props.part_delete_requested.connect(self._on_part_delete)
        props.part_detect_requested.connect(self._on_part_detect)
        self.signal_bus.note_selected.connect(self._on_note_selected)
        self.signal_bus.notes_deselected.connect(props.clear)

        # --- Properties → Edit ---
        props.velocity_changed.connect(self._change_velocity)
        props.cent_offset_changed.connect(self._change_cent_offset)
        props.duration_changed.connect(self._change_duration)
        props.glide_type_changed.connect(self._on_glide_type_changed)
        props.tempo_changed.connect(self._on_tempo_changed)

        # --- Delete ---
        self.main_window._delete_action.triggered.connect(self._delete_selected)

        # --- Neue Stimme ---
        self.main_window._new_voice_action.triggered.connect(self._add_new_voice)
        self.main_window._new_audio_action.triggered.connect(self._add_audio_voice)

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

    # ------------------------------------------------------------------
    # Delegierende Methoden (leiten an aktiven Tab weiter)
    # ------------------------------------------------------------------

    def _on_render_mode_changed(self, mode: str) -> None:
        """Render-Modus fuer alle offenen Tabs aendern."""
        tab_widget = self.main_window.tab_widget
        for i in range(tab_widget.tab_count()):
            doc_tab = tab_widget.document_tab_at(i)
            if doc_tab:
                doc_tab.notation_scene.set_render_mode(mode)
                doc_tab.notation_scene.refresh()
                # View zum Anfang scrollen
                doc_tab.notation_view.centerOn(0, 0)
        self.signal_bus.status_message.emit(f"Anzeige: {mode}")
        logger.info(f"Render-Modus gewechselt: {mode}")

    def _active_edit_controller(self):
        return self._active_tab.edit_controller if self._active_tab else None

    def _active_scene(self):
        return self._active_tab.notation_scene if self._active_tab else None

    def _active_piece(self):
        return self._active_tab.piece if self._active_tab else None

    def _change_velocity(self, v):
        ec = self._active_edit_controller()
        if ec:
            ec.change_velocity(v)

    def _change_cent_offset(self, c):
        ec = self._active_edit_controller()
        if ec:
            props = self.main_window.properties_panel
            ec.change_cent_offset(c, props._glide_combo.currentText())

    def _change_duration(self, d):
        ec = self._active_edit_controller()
        if ec:
            ec.change_duration_deviation(d)

    def _delete_selected(self):
        ec = self._active_edit_controller()
        if ec:
            ec.delete_selected()

    def _zoom_in(self):
        view = self.main_window.notation_view
        if view:
            view.zoom_in()

    def _zoom_out(self):
        view = self.main_window.notation_view
        if view:
            view.zoom_out()

    # ------------------------------------------------------------------
    # Piece / Playback
    # ------------------------------------------------------------------

    def _on_piece_loaded(self, piece) -> None:
        logger.info(f"Piece geladen: '{piece.title}'")
        self._open_piece_in_tab(piece)

    def _play_from_beat(self, beat: float) -> None:
        """Wiedergabe ab einer bestimmten Beat-Position starten."""
        if not self.playback_engine.piece:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return
        self.playback_engine.stop()
        self.playback_engine.transport.seek(beat)
        self.playback_engine.play()
        m, b = self._beat_to_measure_info(beat)
        self.signal_bus.status_message.emit(
            f"Wiedergabe ab Takt {m}, Beat {b:.1f}"
        )

    def _on_play(self) -> None:
        if not self.playback_engine.piece:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return
        self.playback_engine.play()
        self.signal_bus.status_message.emit("Wiedergabe...")

    def _on_play_pause(self) -> None:
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
        piece = self._active_piece()
        if not piece:
            self.signal_bus.status_message.emit("Kein Stück zum Exportieren")
            return
        path, _ = QFileDialog.getSaveFileName(
            self.main_window, "MIDI exportieren", "../media/music",
            "MIDI Dateien (*.mid);;Alle Dateien (*)"
        )
        if path:
            self.midi_exporter.export_file(piece, path)
            self.signal_bus.status_message.emit(f"MIDI exportiert: {path}")

    # ------------------------------------------------------------------
    # PDF Import/Export
    # ------------------------------------------------------------------

    def _import_pdf(self) -> None:
        """PDF-Datei importieren (OMR → MusicXML → Tab)."""
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "PDF importieren", "../media/music",
            "PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        if not path:
            return

        from musiai.pdf.PdfImportWorker import PdfImportWorker
        import tempfile
        self._pdf_temp_dir = tempfile.mkdtemp(prefix="musiai_pdf_")
        self._pdf_source_path = path

        self._pdf_worker = PdfImportWorker(
            self._pdf_import_engine, path, self._pdf_temp_dir
        )
        self._pdf_worker.progress.connect(
            self.signal_bus.status_message.emit
        )
        self._pdf_worker.finished.connect(self._on_pdf_import_finished)
        self._pdf_worker.error.connect(self._on_pdf_error)
        self._pdf_worker.start()
        self.signal_bus.status_message.emit(
            f"PDF-Import ({self._pdf_import_engine})..."
        )

    def _on_pdf_error(self, msg: str) -> None:
        """PDF-Fehler als Dialog anzeigen."""
        self.signal_bus.status_message.emit(f"PDF-Fehler: {msg}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self.main_window, "PDF-Fehler", msg)

    def _on_pdf_import_finished(self, musicxml_path: str) -> None:
        """PDF→MusicXML Konversion fertig → Piece laden."""
        try:
            from musiai.midi.MusicXmlImporterCompat import MusicXmlImporter
            piece = MusicXmlImporter().import_file(musicxml_path)
            self.project.add_piece(piece)
            self._open_piece_in_tab(
                piece, file_path=self._pdf_source_path, file_type="pdf"
            )
            self.signal_bus.status_message.emit(
                f"PDF importiert: {piece.title}"
            )
        except Exception as e:
            logger.error(f"PDF Import fehlgeschlagen: {e}", exc_info=True)
            self.signal_bus.status_message.emit(f"Fehler: {e}")

    def _export_pdf(self) -> None:
        """Aktives Piece als PDF exportieren."""
        piece = self._active_piece()
        if not piece:
            self.signal_bus.status_message.emit("Kein Stück zum Exportieren")
            return

        path, _ = QFileDialog.getSaveFileName(
            self.main_window, "PDF exportieren", "../media/music",
            "PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        if not path:
            return

        import tempfile, os
        temp_xml = os.path.join(
            tempfile.mkdtemp(prefix="musiai_pdf_"),
            "export.musicxml"
        )
        from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
        MusicXmlExporter().export_file(piece, temp_xml)

        from musiai.pdf.PdfExportWorker import PdfExportWorker
        self._pdf_export_worker = PdfExportWorker(
            self._pdf_export_engine, temp_xml, path
        )
        self._pdf_export_worker.progress.connect(
            self.signal_bus.status_message.emit
        )
        self._pdf_export_worker.finished.connect(
            lambda p: self.signal_bus.status_message.emit(f"PDF exportiert: {p}")
        )
        self._pdf_export_worker.error.connect(
            lambda msg: self.signal_bus.status_message.emit(f"PDF-Fehler: {msg}")
        )
        self._pdf_export_worker.start()
        self.signal_bus.status_message.emit(
            f"PDF-Export ({self._pdf_export_engine})..."
        )

    # ------------------------------------------------------------------
    # Settings / Backend
    # ------------------------------------------------------------------

    def _switch_backend(self, name: str) -> None:
        if self.playback_engine.switch_backend(name):
            mw = self.main_window
            mw._backend_gm_action.setChecked(name == "windows_gm")
            if self.playback_engine.piece:
                self.playback_engine.set_piece(self.playback_engine.piece)
            self.signal_bus.status_message.emit(f"Audio: {name}")

    def _load_global_soundfont(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "SoundFont laden", "../media/soundfonts",
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
        # Aktuelle Engines vorselektieren
        if dialog._engines.get(self._detection_engine):
            dialog._engines[self._detection_engine].setChecked(True)
        if hasattr(dialog, '_pdf_import_engines'):
            if dialog._pdf_import_engines.get(self._pdf_import_engine):
                dialog._pdf_import_engines[self._pdf_import_engine].setChecked(True)
            if dialog._pdf_export_engines.get(self._pdf_export_engine):
                dialog._pdf_export_engines[self._pdf_export_engine].setChecked(True)
        if dialog.exec():
            self._detection_engine = dialog.selected_engine
            if hasattr(dialog, 'selected_pdf_import_engine'):
                self._pdf_import_engine = dialog.selected_pdf_import_engine
            if hasattr(dialog, 'selected_pdf_export_engine'):
                self._pdf_export_engine = dialog.selected_pdf_export_engine
            logger.info(
                f"Engines: detect={self._detection_engine}, "
                f"pdf_import={self._pdf_import_engine}, "
                f"pdf_export={self._pdf_export_engine}"
            )

    def _show_midi_dialog(self) -> None:
        dialog = MidiDeviceDialog(self.midi_keyboard, self.main_window)
        dialog.exec()

    # ------------------------------------------------------------------
    # Note/Measure/Edit Handlers
    # ------------------------------------------------------------------

    def _on_glide_type_changed(self, glide_type: str) -> None:
        ec = self._active_edit_controller()
        if ec and ec.selected_note:
            ec.change_cent_offset(
                ec.selected_note.expression.cent_offset, glide_type
            )

    def _on_note_selected(self, note) -> None:
        if note:
            self._tempo_target_measure = None
            scene = self._active_scene()
            if scene:
                scene.clear_measure_highlight()
            self.main_window.properties_panel.show_note(note)

    def _on_measure_clicked(self, measure) -> None:
        scene = self._active_scene()
        ec = self._active_edit_controller()
        if not scene or not ec:
            return
        scene.highlight_measure(measure)
        ec.select_measure(measure)
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
        self.main_window.status_bar.set_edit_mode(active)
        scene = self._active_scene()
        view = self.main_window.notation_view
        if active and scene and view:
            scene.update_cursor(view.cursor_beat)
            self.signal_bus.status_message.emit(
                "Edit Mode — Pfeiltasten/Mausklick: Cursor bewegen, "
                "Ctrl+C/V: Copy/Paste, Esc: beenden"
            )
        elif scene:
            scene.hide_cursor()
            self.signal_bus.status_message.emit("Edit Mode beendet")

    def _on_cursor_moved(self, beat: float) -> None:
        scene = self._active_scene()
        if scene:
            scene.update_cursor(beat)
        measure_num, local_beat = self._beat_to_measure_info(beat)
        self.main_window.status_bar.set_position(measure_num, local_beat)

    def _on_paste(self) -> None:
        view = self.main_window.notation_view
        ec = self._active_edit_controller()
        if not view or not view.edit_mode or not ec:
            return
        beat = view.cursor_beat
        target_measure, local_beat = self._find_measure_at_beat(beat)
        ec.paste_at(target_measure, local_beat)

    def _beat_to_measure_info(self, global_beat: float) -> tuple[int, float]:
        piece = self._active_piece()
        if not piece or not piece.parts:
            return 1, global_beat
        cumulative = 0.0
        for m in piece.parts[0].measures:
            dur = m.duration_beats
            if global_beat < cumulative + dur:
                return m.number, global_beat - cumulative
            cumulative += dur
        last = piece.parts[0].measures[-1]
        return last.number, global_beat - (cumulative - last.duration_beats)

    def _find_measure_at_beat(self, global_beat: float):
        piece = self._active_piece()
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
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or not scene:
            return

        from musiai.model.Tempo import Tempo
        target = self._tempo_target_measure

        if target:
            target.tempo = Tempo(bpm, 0)
            logger.info(f"Takt {target.number} Tempo → {bpm:.0f} BPM")
        else:
            if piece.tempos:
                piece.tempos[0].bpm = bpm
            for part in piece.parts:
                for m in part.measures:
                    if m.tempo:
                        m.tempo.bpm = bpm
            logger.info(f"Globales Tempo → {bpm:.0f} BPM")

        self.playback_engine.transport.tempo_bpm = bpm
        scene.refresh()
        if target:
            scene.highlight_measure(target)
        self.signal_bus.status_message.emit(
            f"Tempo: {bpm:.0f} BPM ({'Takt ' + str(target.number) if target else 'global'})"
        )

    def _on_deselect(self) -> None:
        self._tempo_target_measure = None
        ec = self._active_edit_controller()
        scene = self._active_scene()
        if ec:
            ec.deselect()
        if scene:
            scene.clear_measure_highlight()
        self.main_window.properties_panel.clear()
        self.signal_bus.status_message.emit("Auswahl aufgehoben")

    def _on_note_changed(self, note) -> None:
        ec = self._active_edit_controller()
        if ec and ec.selected_note is note:
            self.main_window.properties_panel.show_note(note)

    # ------------------------------------------------------------------
    # Voice / Part Management
    # ------------------------------------------------------------------

    def _add_new_voice(self) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or not scene:
            self.signal_bus.status_message.emit("Kein Stück geladen")
            return

        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.TimeSignature import TimeSignature

        part_num = len(piece.parts) + 1
        new_part = Part(name=f"Stimme {part_num}", channel=min(part_num, 15))

        if piece.parts:
            for existing in piece.parts[0].measures:
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
        scene.refresh()
        self.signal_bus.status_message.emit(
            f"Neue Stimme '{new_part.name}' hinzugefügt"
        )
        logger.info(f"Neue Stimme: {new_part.name} (Part {part_num})")

    def _on_tempo_clicked(self) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        ec = self._active_edit_controller()
        if not piece or not scene:
            return
        if ec:
            ec.deselect()
        scene.clear_measure_highlight()
        self._tempo_target_measure = None
        tempo = piece.initial_tempo
        ts = piece.parts[0].measures[0].time_signature if piece.parts else None
        if ts:
            self.main_window.properties_panel.show_time_signature(ts, tempo)
        self.signal_bus.status_message.emit(
            f"Globales Tempo: {tempo:.0f} BPM (gilt für alle Takte)"
        )

    def _add_audio_voice(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Audio laden", "../media/mp3",
            "Audio Dateien (*.wav *.mp3 *.flac *.ogg);;Alle Dateien (*)"
        )
        if not path:
            return

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure

        track = AudioTrack()
        if not track.load(path):
            QApplication.restoreOverrideCursor()
            self.signal_bus.status_message.emit("Audio laden fehlgeschlagen")
            return

        piece = self._active_piece()
        scene = self._active_scene()
        if not piece:
            from musiai.model.Piece import Piece
            piece = Piece("Audio Import")
            self.project.add_piece(piece)
            self._open_piece_in_tab(piece)
            scene = self._active_scene()

        import os
        name = os.path.splitext(os.path.basename(path))[0]
        part = Part(name=f"Audio: {name}", channel=len(piece.parts))
        part.audio_track = track

        tempo = piece.initial_tempo
        beats = track.duration_seconds * (tempo / 60.0)
        from musiai.model.TimeSignature import TimeSignature
        ts = TimeSignature(4, 4)
        n_measures = max(1, int(beats / ts.beats_per_measure()) + 1)
        for i in range(n_measures):
            part.add_measure(Measure(i + 1, ts))

        piece.add_part(part)
        self.playback_engine.set_piece(piece)
        if scene:
            scene.refresh()
        QApplication.restoreOverrideCursor()
        self.signal_bus.status_message.emit(
            f"Audio-Stimme '{part.name}' geladen ({track.duration_seconds:.1f}s)"
        )

    def _on_part_delete(self, part_idx: int) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        if len(piece.parts) <= 1:
            self.signal_bus.status_message.emit("Letzte Stimme kann nicht gelöscht werden")
            return
        name = piece.parts[part_idx].name
        del piece.parts[part_idx]
        self.playback_engine.set_piece(piece)
        self.main_window.properties_panel.clear()
        if scene:
            scene.refresh()
        self.signal_bus.status_message.emit(f"Stimme '{name}' gelöscht")

    def _on_part_detect(self, part_idx: int) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        if not part.audio_track or not part.audio_track.file_path:
            self.signal_bus.status_message.emit("Keine Audio-Daten vorhanden")
            return

        if hasattr(self, '_detect_worker') and self._detect_worker and self._detect_worker.isRunning():
            self.signal_bus.status_message.emit("Erkennung läuft bereits...")
            return

        from musiai.audio.DetectionWorker import DetectionWorker

        engine = self._detection_engine
        self._detect_worker = DetectionWorker(
            engine, part.audio_track.file_path,
            piece.initial_tempo, 4.0
        )
        self._detect_worker.progress.connect(
            self.signal_bus.status_message.emit
        )
        self._detect_worker.finished.connect(
            lambda results: self._on_detect_finished(results, part)
        )
        self._detect_worker.error.connect(
            lambda msg: self.signal_bus.status_message.emit(f"Fehler: {msg}")
        )
        self._detect_worker.start()
        self.signal_bus.status_message.emit(f"Erkenne Noten ({engine})...")

    def _on_detect_finished(self, results: dict, source_part) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece:
            return

        total = 0
        for stem_name, notes in results.items():
            if notes:
                self._add_detected_part(
                    piece, f"{stem_name}: {source_part.name}", notes
                )
                total += len(notes)

        if total > 0:
            self.playback_engine.set_piece(piece)
            if scene:
                scene.refresh()
            self.signal_bus.status_message.emit(
                f"{total} Noten in {len(results)} Stimmen erkannt"
            )
        else:
            self.signal_bus.status_message.emit("Keine Noten erkannt")

    def _add_detected_part(self, piece, name: str,
                           notes_data: list[dict]) -> None:
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
        self.playback_engine.set_piece(piece)
        scene = self._active_scene()
        if scene:
            scene.refresh()
        self.signal_bus.status_message.emit(
            f"{len(notes_data)} Noten → '{name}'"
        )

    def _on_part_label_clicked(self, part_idx: int) -> None:
        piece = self._active_piece()
        ec = self._active_edit_controller()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        if ec:
            ec.deselect()
        if scene:
            scene.clear_measure_highlight()
        self.main_window.properties_panel.show_part(part, part_idx)
        self.signal_bus.status_message.emit(
            f"Stimme '{part.name}' (Kanal {part.channel})"
        )

    def _on_part_mute_clicked(self, part_idx: int) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.muted = not part.muted
        if part.audio_track:
            self.playback_engine.audio_player.set_muted(part.muted)
        if scene:
            scene.refresh()
        status = "stumm" if part.muted else "aktiv"
        self.signal_bus.status_message.emit(f"Stimme '{part.name}': {status}")

    def _on_part_instrument_changed(self, part_idx: int, program: int) -> None:
        piece = self._active_piece()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.instrument = program
        self.playback_engine.player.set_instrument(part.channel, 0, program)
        self.signal_bus.status_message.emit(
            f"Stimme '{part.name}': Instrument → Program {program}"
        )

    def _on_part_muted_changed(self, part_idx: int, muted: bool) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        part.muted = muted
        if part.audio_track:
            self.playback_engine.audio_player.set_muted(muted)
        if scene:
            scene.refresh()

    def _on_part_name_changed(self, part_idx: int, name: str) -> None:
        piece = self._active_piece()
        scene = self._active_scene()
        if not piece or part_idx >= len(piece.parts):
            return
        piece.parts[part_idx].name = name
        if scene:
            scene.refresh()

    def _on_part_soundfont(self, part_idx: int) -> None:
        piece = self._active_piece()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "SoundFont laden", "../media/soundfonts",
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
        self.main_window.properties_panel.show_clef()
        self.signal_bus.status_message.emit("Notenschlüssel ausgewählt")

    def _on_ts_clicked_from_view(self, measure) -> None:
        tempo = self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
        self.main_window.properties_panel.show_time_signature(
            measure.time_signature, tempo
        )
        self.signal_bus.status_message.emit(
            f"Taktart {measure.time_signature} ausgewählt"
        )

    # ------------------------------------------------------------------
    # Startup / Shutdown
    # ------------------------------------------------------------------

    def _load_default_file(self) -> None:
        import os

        default_file = os.path.abspath("../media/music/midi/Brahms_Valse_15.mid")
        if os.path.exists(default_file):
            try:
                if default_file.endswith((".mid", ".midi")):
                    from musiai.midi.MidiImporter import MidiImporter
                    piece = MidiImporter().import_file(default_file)
                    file_type = "midi"
                else:
                    from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
                    piece = MusicXmlImporter().import_file(default_file)
                    file_type = "musicxml"
                self.project.add_piece(piece)
                self._open_piece_in_tab(piece, default_file, file_type)
                logger.info(f"Standard-Datei geladen: {default_file}")
            except Exception as e:
                logger.warning(f"Standard-Datei laden fehlgeschlagen: {e}")

        # Audio-Stimme nur laden wenn explizit gewünscht (nicht automatisch)

    def start(self) -> None:
        self.main_window.show()
        self._load_default_file()
        if not self._active_piece():
            self.signal_bus.status_message.emit("Bereit. MIDI oder MusicXML importieren.")
        logger.info("MusiAI gestartet")

    def shutdown(self) -> None:
        """Aufräumen — wird von aboutToQuit aufgerufen."""
        try:
            self.playback_engine.transport._timer.stop()
            self.playback_engine.shutdown()
        except Exception:
            pass
        try:
            self.midi_keyboard.shutdown()
        except Exception:
            pass
        logger.info("MusiAI beendet")
