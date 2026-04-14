"""FileController - Import/Export/Save/Load."""

import logging
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QWidget
from musiai.model.Project import Project
from musiai.model.Piece import Piece
from musiai.midi.MidiImporter import MidiImporter
from musiai.midi.MusicXmlImporterCompat import MusicXmlImporter
from musiai.util.SignalBus import SignalBus
from PySide6.QtWidgets import QMessageBox
from musiai.util.Constants import MIDI_EXTENSIONS, MUSICXML_EXTENSIONS, PROJECT_EXTENSION

logger = logging.getLogger("musiai.controller.FileController")


class FileController:
    """Verwaltet Datei-Operationen: Import, Export, Save, Load."""

    def __init__(self, project: Project, signal_bus: SignalBus, parent_widget: QWidget):
        self.project = project
        self.signal_bus = signal_bus
        self.parent = parent_widget
        self._midi_importer = MidiImporter()
        self._musicxml_importer = MusicXmlImporter()
        self._source_path: str | None = None  # Pfad der geladenen Datei
        self._source_type: str | None = None  # "midi" oder "musicxml"

    def import_midi(self) -> Piece | None:
        """MIDI-Datei per Dialog auswählen und importieren."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "MIDI importieren", "../media/music",
            "MIDI Dateien (*.mid *.midi);;Alle Dateien (*)"
        )
        if not path:
            return None

        try:
            piece = self._midi_importer.import_file(path)
            piece.source_file = path
            self.project.add_piece(piece)
            self._source_path = path
            self._source_type = "midi"
            self.signal_bus.piece_loaded.emit(piece)
            self.signal_bus.status_message.emit(f"MIDI importiert: {Path(path).name}")
            logger.info(f"MIDI importiert: {path} "
                        f"({len(piece.parts)} Parts)")
            return piece
        except Exception as e:
            logger.error(f"MIDI Import fehlgeschlagen: {e}", exc_info=True)
            self._show_error("MIDI Import fehlgeschlagen", path, e)
            return None

    def import_musicxml(self) -> Piece | None:
        """MusicXML-Datei per Dialog auswählen und importieren."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "MusicXML importieren", "../media/music",
            "MusicXML Dateien (*.xml *.musicxml *.mxl);;Alle Dateien (*)"
        )
        if not path:
            return None

        try:
            piece = self._musicxml_importer.import_file(path)
            piece.source_file = path
            self.project.add_piece(piece)
            self._source_path = path
            self._source_type = "musicxml"
            self.signal_bus.piece_loaded.emit(piece)
            self.signal_bus.status_message.emit(f"MusicXML importiert: {Path(path).name}")
            logger.info(f"MusicXML importiert: {path} "
                        f"({len(piece.parts)} Parts)")
            return piece
        except Exception as e:
            logger.error(f"MusicXML Import fehlgeschlagen: {e}", exc_info=True)
            self._show_error("MusicXML Import fehlgeschlagen", path, e)
            return None

    def save_music(self) -> None:
        """Musik-Datei speichern (ins Originalformat)."""
        if not self._source_path:
            self.save_music_as()
            return
        self._save_to_path(self._source_path, self._source_type)

    def save_music_as(self) -> None:
        """Musik-Datei speichern unter (mit Dateiauswahl)."""
        path, selected_filter = QFileDialog.getSaveFileName(
            self.parent, "Musik speichern unter", "../media/music",
            "MusicXML (*.musicxml);;MIDI (*.mid);;Alle Dateien (*)"
        )
        if not path:
            return
        if path.endswith((".mid", ".midi")):
            self._save_to_path(path, "midi")
        else:
            self._save_to_path(path, "musicxml")

    def _save_to_path(self, path: str, file_type: str) -> None:
        """Datei speichern je nach Typ."""
        piece = self.project.current_piece
        if not piece:
            self.signal_bus.status_message.emit("Kein Stück zum Speichern")
            return
        try:
            if file_type == "midi":
                from musiai.midi.MidiExporter import MidiExporter
                MidiExporter().export_file(piece, path)
            else:
                from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
                MusicXmlExporter().export_file(piece, path)
            self._source_path = path
            self._source_type = file_type
            self.signal_bus.status_message.emit(f"Gespeichert: {Path(path).name}")
            logger.info(f"Musik gespeichert: {path}")
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}", exc_info=True)
            self._show_error("Speichern fehlgeschlagen", path, e)

    def save_project(self) -> None:
        """Projekt speichern."""
        path = self.project.file_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self.parent, "Projekt speichern", "../media/projects",
                f"MusiAI Projekte (*{PROJECT_EXTENSION});;Alle Dateien (*)"
            )
        if not path:
            return

        try:
            self.project.save(path)
            self.signal_bus.project_saved.emit(path)
            self.signal_bus.status_message.emit(f"Gespeichert: {Path(path).name}")
            logger.info(f"Projekt gespeichert: {path}")
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}", exc_info=True)
            self._show_error("Projekt speichern fehlgeschlagen", path, e)

    def load_project(self) -> None:
        """Projekt laden."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "Projekt laden", "../media/projects",
            f"MusiAI Projekte (*{PROJECT_EXTENSION});;Alle Dateien (*)"
        )
        if not path:
            return

        try:
            self.project.load(path)
            if self.project.current_piece:
                self.signal_bus.piece_loaded.emit(self.project.current_piece)
            self.signal_bus.status_message.emit(f"Geladen: {Path(path).name}")
            logger.info(f"Projekt geladen: {path}")
        except Exception as e:
            logger.error(f"Laden fehlgeschlagen: {e}", exc_info=True)
            self._show_error("Projekt laden fehlgeschlagen", path, e)

    def _show_error(self, title: str, path: str, error: Exception) -> None:
        """Fehler-Dialog anzeigen und Status-Nachricht setzen."""
        msg = f"{title}\n\nDatei: {Path(path).name}\n\nFehler: {error}"
        self.signal_bus.status_message.emit(f"Fehler: {error}")
        QMessageBox.critical(self.parent, title, msg)
