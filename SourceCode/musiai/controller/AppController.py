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
        self._dirty = False
        from PySide6.QtCore import QSettings
        _s = QSettings("MusiAI", "MusiAI")
        self._beat_engine = _s.value("engines/beat", "librosa")
        self._omr_engine = _s.value("engines/omr", "oemer")

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
        from PySide6.QtCore import QSettings as _QS
        _es = _QS("MusiAI", "MusiAI")
        self._detection_engine = _es.value("engines/detection", "pyin")
        self._pdf_import_engine = _es.value("engines/pdf_import", "audiveris")
        self._pdf_export_engine = _es.value("engines/pdf_export", "lilypond")

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
        # View zum Anfang scrollen
        view.centerOn(0, 0)
        # currentChanged wird automatisch gefeuert → _on_tab_switched

    def _on_tab_switched(self, index: int) -> None:
        """Tab gewechselt -> Signals umverdrahten."""
        logger.debug(f"Tab gewechselt: index={index}")
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
            (view.part_beat_detect_requested, self._on_beat_detect_part),
            (view.part_delete_requested, self._on_part_delete),
            (view.deselect_requested, self._on_deselect),
            (view.edit_mode_changed, self._on_edit_mode_changed),
            (view.cursor_moved, self._on_cursor_moved),
            (view.copy_requested, ec.copy),
            (view.paste_requested, self._on_paste),
            (view.play_from_beat_requested, self._play_from_beat),
            (view.interaction_mode_requested, self._on_interaction_mode_changed),
            (view.staff_note_clicked, self._on_staff_note_clicked),
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
        self.main_window._save_project_action.triggered.connect(
            self._save_project)
        toolbar.load_project_clicked.connect(self.file_controller.load_project)
        toolbar.export_midi_clicked.connect(self._export_midi)
        toolbar.export_pdf_clicked.connect(self._export_pdf)
        self.main_window._save_music_action.triggered.connect(
            self._save_and_refresh
        )
        self.main_window._save_music_as_action.triggered.connect(
            self.file_controller.save_music_as
        )
        self.main_window._save_project_as_action.triggered.connect(
            self._save_project_as
        )
        self.main_window._new_project_action.triggered.connect(
            self._new_project
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

        # --- Akkord-Anzeige ---
        self.main_window.chord_display_changed.connect(self._on_chord_display_changed)

        # --- Interaktionsmodus ---
        self.main_window.interaction_mode_changed.connect(
            self._on_interaction_mode_changed)

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
        props.save_requested.connect(self._save_and_refresh)

        # --- Delete ---
        self.main_window._delete_action.triggered.connect(self._delete_selected)

        # --- Neue Stimme ---
        self.main_window._new_voice_action.triggered.connect(self._add_new_voice)
        self.main_window._new_audio_action.triggered.connect(self._add_audio_voice)
        self.main_window._new_omr_action.triggered.connect(self._import_from_image)

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
        logger.info(f"Render-Modus gewechselt: {mode}")
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

    def _on_chord_display_changed(self, enabled: bool) -> None:
        """Akkord-Anzeige fuer alle offenen Tabs setzen."""
        tab_widget = self.main_window.tab_widget
        for i in range(tab_widget.tab_count()):
            doc_tab = tab_widget.document_tab_at(i)
            if doc_tab:
                doc_tab.notation_scene.set_show_chords(enabled)
        state = "ein" if enabled else "aus"
        self.signal_bus.status_message.emit(f"Akkorde: {state}")
        logger.info(f"Akkord-Anzeige: {state}")

    def _on_staff_note_clicked(self, chord, note_data, track_idx,
                               ctrl, shift) -> None:
        """Handle note click in Bravura/MidiSheet mode.

        Finds the corresponding model Note and shows its properties.
        """
        piece = self._active_piece()
        if not piece:
            return
        midi = note_data.number
        tick = chord.start_time
        beat = tick / 480.0  # TPB = 480

        # Find model note by matching pitch + beat in the track's part
        note_parts = [p for p in piece.parts
                      if not (p.audio_track and p.audio_track.blocks)]
        if track_idx >= len(note_parts):
            return
        part = note_parts[track_idx]

        best = None
        best_dist = float('inf')
        abs_beat = 0.0
        for m in part.measures:
            for n in m.notes:
                n_beat = abs_beat + n.start_beat
                if n.pitch == midi:
                    dist = abs(n_beat - beat)
                    if dist < best_dist:
                        best = n
                        best_dist = dist
            abs_beat += m.duration_beats

        if best and best_dist < 1.0:
            # Select note in EditController so property changes apply
            ec = self._active_edit_controller()
            if ec:
                ec._selected_notes = [best]
                logger.info(f"Staff note selected: {best.name} MIDI {best.pitch}, "
                           f"ec has {len(ec._selected_notes)} selected")
            self.main_window.properties_panel.show_note(best)
            self.signal_bus.status_message.emit(
                f"Note: {best.name} (MIDI {best.pitch}, "
                f"Vel {best.expression.velocity})")
        else:
            self.signal_bus.status_message.emit(
                f"Note: MIDI {midi}, Vel {note_data.velocity}")

    def _on_interaction_mode_changed(self, mode: str) -> None:
        """Interaktionsmodus für den aktiven Tab setzen."""
        if self._active_tab:
            self._active_tab.notation_view.set_interaction_mode(mode)
        self.main_window.set_interaction_mode(mode)
        labels = {"view": "View", "edit": "Edit", "midi_input": "MidiInput"}
        self.signal_bus.status_message.emit(
            f"Modus: {labels.get(mode, mode)}")
        logger.info(f"Interaktionsmodus: {mode}")

    def _active_edit_controller(self):
        return self._active_tab.edit_controller if self._active_tab else None

    def _active_scene(self):
        return self._active_tab.notation_scene if self._active_tab else None

    def _active_piece(self):
        return self._active_tab.piece if self._active_tab else None

    def _change_velocity(self, v):
        ec = self._active_edit_controller()
        if ec:
            logger.info(f"change_velocity({v}), selected={len(ec._selected_notes)}")
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
        source = getattr(piece, 'source_file', None)
        file_type = None
        if source:
            if source.endswith(('.mid', '.midi')):
                file_type = "midi"
            else:
                file_type = "musicxml"
        self._open_piece_in_tab(piece, source, file_type)

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
        logger.info("Wiedergabe gestartet")
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
        logger.info("Wiedergabe gestoppt")
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
            piece.source_file = self._pdf_source_path
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
        # Beat engine vorselektieren
        if hasattr(dialog, '_beat_engines'):
            if dialog._beat_engines.get(self._beat_engine):
                dialog._beat_engines[self._beat_engine].setChecked(True)
        if dialog.exec():
            self._detection_engine = dialog.selected_engine
            self._beat_engine = dialog.selected_beat_engine
            if hasattr(dialog, 'selected_omr_engine'):
                self._omr_engine = dialog.selected_omr_engine
            # Persist ALL engine choices
            from PySide6.QtCore import QSettings
            s = QSettings("MusiAI", "MusiAI")
            s.setValue("engines/detection", self._detection_engine)
            s.setValue("engines/beat", self._beat_engine)
            s.setValue("engines/omr", self._omr_engine)
            s.setValue("engines/pdf_import", self._pdf_import_engine)
            s.setValue("engines/pdf_export", self._pdf_export_engine)
            if hasattr(dialog, 'selected_pdf_import_engine'):
                self._pdf_import_engine = dialog.selected_pdf_import_engine
            if hasattr(dialog, 'selected_pdf_export_engine'):
                self._pdf_export_engine = dialog.selected_pdf_export_engine
            logger.info(
                f"Engines: detect={self._detection_engine}, "
                f"pdf_import={self._pdf_import_engine}, "
                f"pdf_export={self._pdf_export_engine}"
            )
            # Apply log level change
            from musiai.util.LoggingConfig import apply_log_level
            new_level = dialog.log_level
            apply_log_level(new_level)
            logger.info(f"Log-Level geändert: {new_level}")
            # Reload velocity colors from settings
            from musiai.notation.ColorScheme import ColorScheme
            ColorScheme.reload_colors()
            # Refresh notation to apply changes
            if self._active_tab and self._active_tab.notation_scene:
                self._active_tab.notation_scene.refresh()

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

    def _import_from_image(self) -> None:
        """Bearbeiten → Neue Spur aus Bild/PDF (async)."""
        from PySide6.QtWidgets import QFileDialog
        if (hasattr(self, '_omr_worker') and self._omr_worker
                and self._omr_worker.isRunning()):
            self.signal_bus.status_message.emit(
                "Notenerkennung läuft bereits...")
            return

        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Bild/PDF mit Noten laden",
            "../media",
            "Bilder/PDF (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf)"
            ";;Alle Dateien (*)")
        if not path:
            return

        from musiai.omr.OMRWorker import OMRWorker
        engine = self._omr_engine or "oemer"
        self.signal_bus.status_message.emit(
            f"Notenerkennung läuft ({engine})...")

        # Show progress on scene
        scene = self._active_scene()
        self._omr_progress_item = None
        if scene:
            from PySide6.QtGui import QFont, QColor, QBrush
            from PySide6.QtWidgets import QGraphicsSimpleTextItem
            item = QGraphicsSimpleTextItem(
                f"\u23F3 Notenerkennung läuft ({engine})...")
            item.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            item.setBrush(QBrush(QColor(0, 100, 200)))
            item.setZValue(100)
            rect = scene.sceneRect()
            item.setPos(120, max(rect.height() - 40, 100))
            scene.addItem(item)
            self._omr_progress_item = item
            view = self.main_window.notation_view
            if view:
                view.ensureVisible(item)

        self._omr_worker = OMRWorker(path, engine)
        self._omr_source_path = path
        self._omr_worker.finished.connect(self._on_omr_finished)
        self._omr_worker.error.connect(self._on_omr_error)
        self._omr_worker.start()

    def _remove_omr_progress(self) -> None:
        item = getattr(self, '_omr_progress_item', None)
        if item:
            scene = item.scene()
            if scene:
                scene.removeItem(item)
            self._omr_progress_item = None

    def _on_omr_finished(self, result) -> None:
        """OMR fertig — Ergebnis verarbeiten (Main Thread)."""
        from PySide6.QtWidgets import QMessageBox
        self._remove_omr_progress()
        path = self._omr_source_path

        if not result.success:
            QMessageBox.warning(
                self.main_window, "Fehler",
                f"Notenerkennung fehlgeschlagen:\n{result.error}")
            return

        try:
            from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
            import os
            # Save to persistent temp folder for debugging
            omr_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..",
                             "media", "omr_output"))
            os.makedirs(omr_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(path))[0]
            tmp = os.path.join(omr_dir, f"{base}_omr.musicxml")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(result.musicxml)
            logger.info(f"OMR XML gespeichert: {tmp}")

            piece = MusicXmlImporter().import_file(tmp)

            piece.source_file = path
            self.project.add_piece(piece)
            self._open_piece_in_tab(piece, path, "musicxml")
            self.signal_bus.status_message.emit(
                f"Noten erkannt: {len(piece.parts)} Stimmen, "
                f"{piece.total_measures} Takte")
        except Exception as e:
            logger.error(f"OMR Import fehlgeschlagen: {e}", exc_info=True)
            QMessageBox.warning(
                self.main_window, "Fehler", f"Import fehlgeschlagen:\n{e}")

    def _on_omr_error(self, msg: str) -> None:
        """OMR Fehler (Main Thread)."""
        from PySide6.QtWidgets import QMessageBox
        self._remove_omr_progress()
        QMessageBox.warning(
            self.main_window, "Fehler",
            f"Notenerkennung fehlgeschlagen:\n{msg}")

    def _on_beat_detect_part(self, part_idx: int) -> None:
        """Beats erkennen für eine Audio-Stimme (Rechtsklick)."""
        piece = self._active_piece()
        if not piece or part_idx >= len(piece.parts):
            return
        part = piece.parts[part_idx]
        if not part.audio_track or not part.audio_track.file_path:
            self.signal_bus.status_message.emit(
                "Keine Audio-Datei in dieser Stimme")
            return
        self._run_beat_detection_on_file(part.audio_track.file_path)

    def _run_beat_detection(self) -> None:
        """Beat-Erkennung via Datei-Dialog."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Audio-Datei für Beat-Erkennung",
            "../media/mp3",
            "Audio (*.wav *.mp3 *.ogg *.flac);;Alle Dateien (*)")
        if not path:
            return
        self._run_beat_detection_on_file(path)

    def _run_beat_detection_on_file(self, path: str) -> None:
        """Beat-Erkennung auf eine Datei: async Beats erkennen → Stimme anlegen."""
        if (hasattr(self, '_beat_worker') and self._beat_worker
                and self._beat_worker.isRunning()):
            self.signal_bus.status_message.emit(
                "Beat-Erkennung läuft bereits...")
            return

        from musiai.audio.BeatDetectWorker import BeatDetectWorker

        engine = self._beat_engine or "librosa"
        self.signal_bus.status_message.emit(
            f"Beat-Erkennung läuft ({engine})...")

        # Show progress text on the scene below existing content
        scene = self._active_scene()
        self._beat_progress_item = None
        if scene:
            from PySide6.QtGui import QFont, QColor, QBrush
            from PySide6.QtWidgets import QGraphicsSimpleTextItem
            item = QGraphicsSimpleTextItem(
                f"⏳ Beat-Erkennung läuft ({engine})...")
            item.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            item.setBrush(QBrush(QColor(0, 100, 200)))
            item.setZValue(100)
            # Position below waveform or in center
            rect = scene.sceneRect()
            item.setPos(120, max(rect.height() - 40, 100))
            scene.addItem(item)
            self._beat_progress_item = item
            # Scroll to show it
            view = self.main_window.notation_view
            if view:
                view.ensureVisible(item)

        self._beat_worker = BeatDetectWorker(path, engine)
        self._beat_detect_path = path
        self._beat_worker.finished.connect(self._on_beat_detect_finished)
        self._beat_worker.error.connect(self._on_beat_detect_error)
        self._beat_worker.start()

    def _remove_beat_progress_item(self) -> None:
        """Entfernt den Fortschritts-Text von der Szene."""
        item = getattr(self, '_beat_progress_item', None)
        if item:
            scene = item.scene()
            if scene:
                scene.removeItem(item)
            self._beat_progress_item = None

    def _on_beat_detect_finished(self, result) -> None:
        """Callback nach erfolgreicher Beat-Erkennung (Main-Thread)."""
        from PySide6.QtWidgets import QMessageBox
        self._remove_beat_progress_item()
        path = self._beat_detect_path

        try:
            from musiai.model.AudioTrack import AudioTrack
            from musiai.model.Part import Part
            from musiai.model.Measure import Measure
            from musiai.model.Note import Note
            from musiai.model.TimeSignature import TimeSignature
            from musiai.model.Piece import Piece
            import os

            engine = self._beat_engine or "librosa"

            # 1) Load audio track
            audio_track = AudioTrack()
            if not audio_track.load(path):
                QMessageBox.warning(self.main_window, "Fehler",
                                    "Audio laden fehlgeschlagen")
                return

            # 2) Create or use active piece
            piece = self._active_piece()
            scene = self._active_scene()
            if not piece:
                name = os.path.splitext(os.path.basename(path))[0]
                piece = Piece(name)
                self.project.add_piece(piece)
                self._open_piece_in_tab(piece)
                scene = self._active_scene()

            # 3) Map beat times to piece beats
            #    Each detected beat = 1 beat in the piece.
            #    Group into measures by time signature.
            ts_num, ts_den = result.time_signature
            ts = TimeSignature(ts_num, ts_den)
            beats_per_measure = int(ts.beats_per_measure())
            total_beats = len(result.beat_times)
            # Calculate last beat position in piece-beats
            last_beat_pos = (result.beat_times[-1] * result.bpm / 60.0
                             if result.beat_times else 0)
            audio_end_pos = audio_track.duration_seconds * result.bpm / 60.0
            max_pos = max(last_beat_pos, audio_end_pos)
            n_measures = max(1, int(max_pos / beats_per_measure) + 1)

            # 4) Audio part — only add if not already present
            existing_audio = [p for p in piece.parts
                              if p.audio_track and
                              p.audio_track.file_path == path]
            if not existing_audio:
                audio_name = os.path.splitext(os.path.basename(path))[0]
                audio_part = Part(
                    name=f"Audio: {audio_name}",
                    channel=len(piece.parts))
                audio_part.audio_track = audio_track
                for i in range(n_measures):
                    audio_part.add_measure(Measure(i + 1, ts))
                piece.add_part(audio_part)

            # 5) Beat part — one note per detected beat,
            #    duration = time until next beat (variable lengths)
            beat_part = Part(
                name=f"Beats ({engine})", channel=len(piece.parts))
            # Calculate duration of each beat in beats (relative to BPM)
            beat_durations = []
            for bi in range(total_beats):
                if bi + 1 < total_beats:
                    dt_sec = result.beat_times[bi + 1] - result.beat_times[bi]
                    dur_beats = dt_sec * result.bpm / 60.0
                else:
                    dur_beats = 1.0
                beat_durations.append(dur_beats)

            # Place beat notes at their actual time positions
            # Beat time in seconds → beat position = time * bpm / 60
            from musiai.model.Tempo import Tempo
            for i in range(n_measures):
                m = Measure(i + 1, ts)
                measure_start_idx = i * beats_per_measure
                for j in range(beats_per_measure):
                    beat_idx = measure_start_idx + j
                    if beat_idx < total_beats:
                        # Convert absolute time to beat position
                        beat_pos = result.beat_times[beat_idx] * result.bpm / 60.0
                        # Position within this measure
                        measure_start_beat = i * beats_per_measure
                        local_beat = beat_pos - measure_start_beat
                        dur = beat_durations[beat_idx]
                        m.add_note(Note(60, local_beat, dur))
                beat_part.add_measure(m)
            piece.add_part(beat_part)

            # 6) Set tempo from detected BPM
            piece.tempos = [Tempo(result.bpm, 0.0)]

            # Add per-beat tempo variations as duration_deviation
            if len(result.tempo_curve) > 1:
                median_bpm = result.bpm
                beat_idx = 0
                for m in beat_part.measures:
                    for n in m.notes:
                        if beat_idx < len(result.tempo_curve):
                            _, local_bpm = result.tempo_curve[beat_idx]
                            dev = local_bpm / median_bpm
                            if abs(dev - 1.0) >= 0.02:
                                n.expression.duration_deviation = dev
                        beat_idx += 1

            # 7) Refresh
            self.playback_engine.set_piece(piece)
            if scene:
                scene.refresh()

            total_beat_notes = sum(len(m.notes) for m in beat_part.measures)
            self.signal_bus.status_message.emit(
                f"Beat-Erkennung: {result.bpm:.0f} BPM, "
                f"{total_beat_notes} Beats, Taktart {ts_num}/{ts_den}")
            logger.info(f"Beat-Erkennung fertig: {result.bpm:.0f} BPM, "
                        f"{total_beat_notes} Beats, engine={engine}")

        except Exception as e:
            logger.error(f"Beat-Erkennung fehlgeschlagen: {e}", exc_info=True)
            QMessageBox.warning(
                self.main_window, "Fehler",
                f"Beat-Erkennung fehlgeschlagen:\n{e}")

    def _on_beat_detect_error(self, msg: str) -> None:
        """Callback bei Fehler in der Beat-Erkennung (Main-Thread)."""
        from PySide6.QtWidgets import QMessageBox
        self._remove_beat_progress_item()
        logger.error(f"Beat-Erkennung fehlgeschlagen: {msg}")
        QMessageBox.warning(
            self.main_window, "Fehler",
            f"Beat-Erkennung fehlgeschlagen:\n{msg}")

    def _new_project(self) -> None:
        """Neues leeres Projekt in neuem Tab."""
        from musiai.model.Piece import Piece
        piece = Piece("Neues Projekt")
        from musiai.model.Part import Part
        part = Part("Stimme 1")
        from musiai.model.Measure import Measure
        part.add_measure(Measure(1))
        piece.add_part(part)
        self.project.add_piece(piece)
        self._open_piece_in_tab(piece)
        self.signal_bus.status_message.emit("Neues Projekt erstellt")

    def _save_and_refresh(self) -> None:
        """Apply pending property changes and refresh scene (no file dialog)."""
        props = self.main_window.properties_panel
        props.apply_pending_changes()
        self._dirty = False
        scene = self._active_scene()
        if scene:
            scene.refresh()
        self.signal_bus.status_message.emit("Änderungen übernommen")

    def _on_note_changed(self, note) -> None:
        ec = self._active_edit_controller()
        if ec and ec.selected_note is note:
            self.main_window.properties_panel.show_note(note)
        # Mark as dirty (refresh on save)
        self._dirty = True
        self.signal_bus.status_message.emit("Geändert — Ctrl+S zum Speichern")

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
        logger.info("_add_audio_voice aufgerufen")
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Audio laden", "../media/mp3",
            "Audio Dateien (*.wav *.mp3 *.flac *.ogg);;Alle Dateien (*)"
        )
        if not path:
            logger.warning("_add_audio_voice: kein Pfad ausgewählt")
            return
        logger.info(f"Audio-Datei ausgewählt: {path}")

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
        """Notenschlüssel-Klick: Stimm-Eigenschaften anzeigen."""
        piece = self._active_piece()
        if piece:
            for idx, part in enumerate(piece.parts):
                if measure in part.measures:
                    self.main_window.properties_panel.show_part(part, idx)
                    self.signal_bus.status_message.emit(
                        f"Stimme '{part.name}' — Schlüssel ausgewählt")
                    return
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
        from PySide6.QtCore import QSettings
        settings = QSettings("MusiAI", "MusiAI")

        # Check if we should reopen last project
        reopen = settings.value("ui/reopen_last_project", "false") == "true"
        last_project = settings.value("ui/last_project_path", "")
        if reopen and last_project and os.path.exists(last_project):
            if self._load_project_from_path(last_project):
                logger.info(f"Letztes Projekt geladen: {last_project}")
                return

        default_file = os.path.abspath(
            "../media/music/musicXML/_Echte/"
            "Beethoven - Sonata 30, Mvt.3. "
            "{Professional production score.}.mxl")
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
                piece.source_file = default_file
                self.project.add_piece(piece)
                self.file_controller._source_path = default_file
                self.file_controller._source_type = file_type
                self._open_piece_in_tab(piece, default_file, file_type)
                logger.info(f"Standard-Datei geladen: {default_file}")
            except Exception as e:
                logger.warning(f"Standard-Datei laden fehlgeschlagen: {e}")

    def _save_project(self) -> None:
        """Projekt speichern (inkl. Musik-Datei) und Pfad merken."""
        props = self.main_window.properties_panel
        props.apply_pending_changes()
        self._dirty = False
        # Save music file if path is known (no dialog)
        if self.file_controller._source_path:
            self.file_controller.save_music()
        # Save project
        self.file_controller.save_project()
        path = self.project.file_path
        if path:
            self._add_to_recent(path)
        scene = self._active_scene()
        if scene:
            scene.refresh()

    def _save_project_as(self) -> None:
        """Projekt speichern unter... und Pfad merken."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self.main_window, "Projekt speichern unter...",
            "../media/projects",
            "MusiAI Projekte (*.musiai);;Alle Dateien (*)")
        if not path:
            return
        try:
            self.project.save(path)
            self._add_to_recent(path)
            self.signal_bus.status_message.emit(
                f"Projekt gespeichert: {path}")
        except Exception as e:
            logger.error(f"Projekt speichern fehlgeschlagen: {e}")

    def _add_to_recent(self, path: str) -> None:
        """Add a project path to the recent list (max 10)."""
        from PySide6.QtCore import QSettings
        settings = QSettings("MusiAI", "MusiAI")
        recent = settings.value("ui/recent_projects", []) or []
        if isinstance(recent, str):
            recent = [recent] if recent else []
        # Remove if already in list, add to front
        recent = [p for p in recent if p != path]
        recent.insert(0, path)
        recent = recent[:10]
        settings.setValue("ui/recent_projects", recent)
        settings.setValue("ui/last_project_path", path)
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        """Update the recent projects submenu."""
        import os
        from PySide6.QtCore import QSettings
        menu = self.main_window._recent_menu
        menu.clear()
        settings = QSettings("MusiAI", "MusiAI")
        recent = settings.value("ui/recent_projects", []) or []
        if isinstance(recent, str):
            recent = [recent] if recent else []
        for path in recent:
            if os.path.exists(path):
                name = os.path.basename(path)
                menu.addAction(name, lambda p=path: self._open_recent(p))
        if not recent:
            menu.addAction("(keine)").setEnabled(False)

    def _open_recent(self, path: str) -> None:
        """Open a recent project."""
        self._load_project_from_path(path)

    def _load_project_from_path(self, path: str) -> bool:
        """Load a project file and open all pieces in tabs."""
        import os
        if not os.path.exists(path):
            self.signal_bus.status_message.emit(f"Nicht gefunden: {path}")
            return False
        try:
            self.project.load(path)
            # Open each piece in a tab
            for piece in self.project.pieces:
                # Try to find original source file path from piece metadata
                source = getattr(piece, 'source_file', None)
                file_type = "musicxml"
                if source and source.endswith(('.mid', '.midi')):
                    file_type = "midi"
                self._open_piece_in_tab(piece, source, file_type)
            self._add_to_recent(path)
            self.signal_bus.status_message.emit(
                f"Projekt geladen: {os.path.basename(path)}")
            return True
        except Exception as e:
            logger.error(f"Projekt laden fehlgeschlagen: {e}")
            return False

    def start(self) -> None:
        # Akkorde-Default aus Settings laden
        from PySide6.QtCore import QSettings
        settings = QSettings("MusiAI", "MusiAI")
        chords_default = settings.value("ui/chords_default", "false") == "true"
        if chords_default:
            self.main_window._chord_toggle.setChecked(True)

        self._update_recent_menu()
        self.main_window.show()
        self._load_default_file()

        # Akkorde-Einstellung auf geladene Tabs anwenden
        if chords_default and self._active_tab:
            self._active_tab.notation_scene.set_show_chords(True)

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
