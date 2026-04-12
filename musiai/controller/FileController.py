"""FileController - Import/Export/Save/Load."""

import logging
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QWidget
from musiai.model.Project import Project
from musiai.model.Piece import Piece
from musiai.midi.MidiImporter import MidiImporter
from musiai.midi.MusicXmlImporterCompat import MusicXmlImporter
from musiai.util.SignalBus import SignalBus
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

    def import_midi(self) -> Piece | None:
        """MIDI-Datei per Dialog auswählen und importieren."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "MIDI importieren", "media/music",
            "MIDI Dateien (*.mid *.midi);;Alle Dateien (*)"
        )
        if not path:
            return None

        try:
            piece = self._midi_importer.import_file(path)
            self.project.add_piece(piece)
            self.signal_bus.piece_loaded.emit(piece)
            self.signal_bus.status_message.emit(f"MIDI importiert: {Path(path).name}")
            return piece
        except Exception as e:
            logger.error(f"MIDI Import fehlgeschlagen: {e}", exc_info=True)
            self.signal_bus.status_message.emit(f"Fehler: {e}")
            return None

    def import_musicxml(self) -> Piece | None:
        """MusicXML-Datei per Dialog auswählen und importieren."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "MusicXML importieren", "media/music",
            "MusicXML Dateien (*.xml *.musicxml *.mxl);;Alle Dateien (*)"
        )
        if not path:
            return None

        try:
            piece = self._musicxml_importer.import_file(path)
            self.project.add_piece(piece)
            self.signal_bus.piece_loaded.emit(piece)
            self.signal_bus.status_message.emit(f"MusicXML importiert: {Path(path).name}")
            return piece
        except Exception as e:
            logger.error(f"MusicXML Import fehlgeschlagen: {e}", exc_info=True)
            self.signal_bus.status_message.emit(f"Fehler: {e}")
            return None

    def save_project(self) -> None:
        """Projekt speichern."""
        path = self.project.file_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self.parent, "Projekt speichern", "media/projects",
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
            self.signal_bus.status_message.emit(f"Fehler beim Speichern: {e}")

    def load_project(self) -> None:
        """Projekt laden."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "Projekt laden", "media/projects",
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
            self.signal_bus.status_message.emit(f"Fehler beim Laden: {e}")
