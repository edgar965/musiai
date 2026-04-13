"""Toolbar mit Aktions-Buttons."""

import logging
from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

logger = logging.getLogger("musiai.ui.Toolbar")


class Toolbar(QToolBar):
    """Haupttoolbar mit Import/Export/Play/Record Buttons."""

    import_midi_clicked = Signal()
    import_musicxml_clicked = Signal()
    import_pdf_clicked = Signal()
    export_midi_clicked = Signal()
    export_pdf_clicked = Signal()
    save_project_clicked = Signal()
    load_project_clicked = Signal()
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    record_clicked = Signal()
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    midi_device_clicked = Signal()

    def __init__(self):
        super().__init__("Hauptleiste")
        self.setMovable(False)
        self._setup_actions()
        logger.debug("Toolbar erstellt")

    def _setup_actions(self) -> None:
        # Datei
        self._add_action("MIDI Import", self.import_midi_clicked)
        self._add_action("XML Import", self.import_musicxml_clicked)
        self._add_action("PDF Import", self.import_pdf_clicked)
        self.addSeparator()
        self._add_action("Speichern", self.save_project_clicked)
        self._add_action("Laden", self.load_project_clicked)
        self._add_action("MIDI Export", self.export_midi_clicked)
        self.addSeparator()

        # Transport
        self._play_action = self._add_action("Play", self.play_clicked)
        self._add_action("Pause", self.pause_clicked)
        self._add_action("Stop", self.stop_clicked)
        self.addSeparator()

        # Recording
        self._record_action = self._add_action("Record Expr.", self.record_clicked)
        self._record_action.setCheckable(True)
        self.addSeparator()

        # Ansicht
        self._add_action("Zoom +", self.zoom_in_clicked)
        self._add_action("Zoom -", self.zoom_out_clicked)
        self.addSeparator()

        # MIDI
        self._add_action("MIDI Device", self.midi_device_clicked)

    def _add_action(self, text: str, signal: Signal) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(signal.emit)
        self.addAction(action)
        return action
