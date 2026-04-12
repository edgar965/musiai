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
        view.copy_requested.connect(self.edit_controller.copy)
        view.paste_requested.connect(self.edit_controller.paste)
        self.signal_bus.note_selected.connect(self._on_note_selected)
        self.signal_bus.notes_deselected.connect(props.clear)

        # --- Properties → Edit ---
        props.velocity_changed.connect(self.edit_controller.change_velocity)
        props.cent_offset_changed.connect(
            lambda c: self.edit_controller.change_cent_offset(
                c, props._glide_combo.currentText()
            )
        )
        props.duration_changed.connect(self.edit_controller.change_duration_deviation)
        props.glide_type_changed.connect(self._on_glide_type_changed)
        props.measure_duration_changed.connect(self._on_measure_duration_changed)

        # --- Delete ---
        self.main_window._delete_action.triggered.connect(
            self.edit_controller.delete_selected
        )

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
        """Note ausgewählt → Properties Panel anzeigen."""
        if note:
            self.main_window.properties_panel.show_note(note)

    def _on_measure_clicked(self, measure) -> None:
        """Klick in Takt-Bereich → Takt selektieren, Properties zeigen."""
        self.notation_scene.highlight_measure(measure)
        self.edit_controller.select_measure(measure)
        tempo = self.playback_engine.piece.initial_tempo if self.playback_engine.piece else 120
        self.main_window.properties_panel.show_time_signature(
            measure.time_signature, tempo, measure.duration_deviation
        )
        self.signal_bus.status_message.emit(
            f"Takt {measure.number} ausgewählt ({len(measure.notes)} Noten)"
        )

    def _on_measure_duration_changed(self, deviation: float) -> None:
        """Taktlänge geändert → Model updaten und neu rendern."""
        measure = self.edit_controller.selected_measure
        if not measure:
            return
        measure.duration_deviation = deviation
        self.notation_scene.refresh()
        logger.debug(f"Takt {measure.number} Dauer → {deviation:.0%}")

    def _on_note_changed(self, note) -> None:
        """Note wurde geändert → Panel updaten falls selektiert."""
        if self.edit_controller.selected_note is note:
            self.main_window.properties_panel.show_note(note)

    def _on_ts_clicked(self, ts_item) -> None:
        """Taktart angeklickt → Properties zeigen."""
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
