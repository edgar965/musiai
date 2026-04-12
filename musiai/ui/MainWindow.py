"""Hauptfenster der Anwendung."""

import logging
from PySide6.QtWidgets import QMainWindow, QMenu
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt
from musiai.notation.NotationScene import NotationScene
from musiai.ui.NotationView import NotationView
from musiai.ui.Toolbar import Toolbar
from musiai.ui.StatusBar import StatusBar
from musiai.ui.PropertiesPanel import PropertiesPanel

logger = logging.getLogger("musiai.ui.MainWindow")


class MainWindow(QMainWindow):
    """MusiAI Hauptfenster."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusiAI - Music Expression Editor")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        # Toolbar
        self.toolbar = Toolbar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # StatusBar
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        # Properties Panel (rechts)
        self.properties_panel = PropertiesPanel()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_panel)

        # NotationView
        self.notation_view: NotationView | None = None

        # Menüleiste
        self._setup_menus()

        logger.debug("MainWindow erstellt")

    def set_notation_scene(self, scene: NotationScene) -> None:
        """NotationScene setzen und als zentrales Widget einbinden."""
        self.notation_view = NotationView(scene)
        self.setCentralWidget(self.notation_view)
        logger.debug("NotationScene an MainWindow gebunden")

    def _show_about(self) -> None:
        from musiai.ui.AboutDialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()

    def _setup_menus(self) -> None:
        menu_bar = self.menuBar()

        # Datei-Menü
        file_menu = menu_bar.addMenu("&Datei")
        file_menu.addAction("MIDI importieren", self.toolbar.import_midi_clicked.emit)
        file_menu.addAction("MusicXML importieren", self.toolbar.import_musicxml_clicked.emit)
        file_menu.addSeparator()

        # Musik Datei speichern
        self._save_music_action = file_menu.addAction("Musik speichern")
        self._save_music_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_music_as_action = file_menu.addAction("Musik speichern unter...")
        self._save_music_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()

        # Projekt
        file_menu.addAction("Projekt speichern", self.toolbar.save_project_clicked.emit)
        file_menu.addAction("Projekt laden", self.toolbar.load_project_clicked.emit, QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        file_menu.addAction("MIDI exportieren", self.toolbar.export_midi_clicked.emit)

        # Bearbeiten-Menü
        edit_menu = menu_bar.addMenu("&Bearbeiten")
        self._delete_action = edit_menu.addAction("Note löschen")
        self._delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        edit_menu.addSeparator()
        self._new_voice_action = edit_menu.addAction("Neue Stimme")
        self._new_audio_action = edit_menu.addAction("Neue Stimme — Aufnahme...")

        # Ansicht-Menü
        view_menu = menu_bar.addMenu("&Ansicht")
        view_menu.addAction("Zoom +", self.toolbar.zoom_in_clicked.emit, "Ctrl+=")
        view_menu.addAction("Zoom -", self.toolbar.zoom_out_clicked.emit, "Ctrl+-")

        # Audio-Menü
        audio_menu = menu_bar.addMenu("&Audio")
        self._backend_gm_action = audio_menu.addAction("Windows GM Synth")
        self._backend_gm_action.setCheckable(True)
        self._backend_gm_action.setChecked(True)
        self._backend_sf_action = audio_menu.addAction("SoundFont laden...")
        self._backend_port_action = audio_menu.addAction("Externer MIDI-Port...")
        audio_menu.addSeparator()
        audio_menu.addAction("MIDI Device", self.toolbar.midi_device_clicked.emit)

        # Transport-Menü
        transport_menu = menu_bar.addMenu("&Transport")
        self._play_pause_action = transport_menu.addAction("Play / Pause")
        self._play_pause_action.setShortcut("Space")
        transport_menu.addAction("Stop", self.toolbar.stop_clicked.emit, "Escape")

        # Hilfe-Menü
        help_menu = menu_bar.addMenu("&Hilfe")
        help_menu.addAction("Info", self._show_about)
