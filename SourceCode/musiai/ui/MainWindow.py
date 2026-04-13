"""Hauptfenster der Anwendung."""

import logging
from PySide6.QtWidgets import QMainWindow, QMenu, QComboBox, QWidget, QHBoxLayout
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, Signal
from musiai.ui.TabWidget import TabWidget
from musiai.ui.Toolbar import Toolbar
from musiai.ui.StatusBar import StatusBar
from musiai.ui.PropertiesPanel import PropertiesPanel

logger = logging.getLogger("musiai.ui.MainWindow")


class MainWindow(QMainWindow):
    """MusiAI Hauptfenster."""

    render_mode_changed = Signal(str)  # "musicxml", "svg", "pianoroll"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusiAI - Music Expression Editor")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        # Toolbar (versteckt - alle Funktionen im Menü)
        self.toolbar = Toolbar()
        self.toolbar.setVisible(False)

        # StatusBar
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        # Properties Panel (rechts)
        self.properties_panel = PropertiesPanel()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_panel)

        # TabWidget als zentrales Widget
        self.tab_widget = TabWidget()
        self.setCentralWidget(self.tab_widget)

        # Menüleiste
        self._setup_menus()

        # Render-Modus ComboBox (rechts in der Menüleiste)
        self._setup_render_mode_combo()

        logger.debug("MainWindow erstellt")

    def _setup_render_mode_combo(self) -> None:
        """ComboBox fuer Render-Modus rechts in der Menüleiste."""
        self._render_mode_combo = QComboBox()
        self._render_mode_combo.addItem("MusicXML", "musicxml")
        self._render_mode_combo.addItem("SVG (Verovio)", "svg")
        self._render_mode_combo.addItem("Piano Roll", "pianoroll")
        self._render_mode_combo.setFixedWidth(140)
        self._render_mode_combo.setToolTip("Darstellungsmodus wechseln")
        self._render_mode_combo.currentIndexChanged.connect(
            self._on_render_mode_changed
        )

        # Spacer + ComboBox als Corner-Widget der Menüleiste
        corner = QWidget()
        layout = QHBoxLayout(corner)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.addWidget(self._render_mode_combo)
        self.menuBar().setCornerWidget(corner, Qt.Corner.TopRightCorner)

    def _on_render_mode_changed(self, index: int) -> None:
        mode = self._render_mode_combo.itemData(index)
        if mode:
            self.render_mode_changed.emit(mode)

    def closeEvent(self, event) -> None:
        """Fenster geschlossen → Prozess sofort beenden."""
        event.accept()
        import os
        os._exit(0)

    @property
    def notation_view(self):
        """Aktuelle NotationView (Kompatibilität)."""
        doc = self.tab_widget.current_document_tab()
        return doc.notation_view if doc else None

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
        file_menu.addAction("PDF importieren...", self.toolbar.import_pdf_clicked.emit)
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
        file_menu.addAction("PDF exportieren...", self.toolbar.export_pdf_clicked.emit)
        file_menu.addSeparator()

        # Tab schließen
        self._close_tab_action = file_menu.addAction("Tab schließen")
        self._close_tab_action.setShortcut(QKeySequence("Ctrl+W"))

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

        # Tools-Menü
        tools_menu = menu_bar.addMenu("&Tools")
        self._settings_action = tools_menu.addAction("Einstellungen...")

        # Hilfe-Menü
        help_menu = menu_bar.addMenu("&Hilfe")
        help_menu.addAction("Info", self._show_about)
