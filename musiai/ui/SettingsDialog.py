"""SettingsDialog - Einstellungen mit Tab-Controls."""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QLabel, QPushButton,
)
from PySide6.QtCore import Qt

logger = logging.getLogger("musiai.ui.SettingsDialog")


class SettingsDialog(QDialog):
    """Einstellungen-Dialog mit Tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(450, 350)
        self._selected_engine = "pyin"
        self._setup_ui()
        self._detect_engines()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Tab 1: Notenerkennung
        self._tabs.addTab(self._build_detection_tab(), "Notenerkennung")

        # Weitere Tabs können hier hinzugefügt werden
        self._tabs.addTab(self._build_audio_tab(), "Audio")

        # OK/Cancel
        from PySide6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_detection_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Engine für Notenerkennung")
        g_lay = QVBoxLayout(group)
        self._engine_group = QButtonGroup(self)

        self._engines = {}
        engines_info = [
            ("pyin", "librosa pyin (monophon)",
             "Schnell, erkennt eine Stimme. Gut für Solo-Instrumente."),
            ("demucs+pyin", "demucs + pyin (polyphon)",
             "Trennt Audio in Stimmen (Vocals/Bass/Drums/Other),\n"
             "dann erkennt pyin jede Stimme einzeln. Beste Qualität."),
            ("madmom", "madmom (Beat/Onset)",
             "Erkennt Beats und Onsets. Ergänzung zu pyin."),
        ]

        for i, (key, name, desc) in enumerate(engines_info):
            radio = QRadioButton(name)
            info = QLabel(desc)
            info.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
            self._status_labels = {}
            status = QLabel("")
            status.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self._status_labels[key] = status
            self._engine_group.addButton(radio, i)
            self._engines[key] = radio
            g_lay.addWidget(radio)
            g_lay.addWidget(info)
            g_lay.addWidget(status)

        layout.addWidget(group)
        return page

    def _build_audio_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Audio-Einstellungen (zukünftig)"))
        layout.addStretch()
        return page

    def _detect_engines(self) -> None:
        """Prüft welche Engines installiert sind."""
        checks = {
            "pyin": "librosa",
            "demucs+pyin": "demucs",
            "madmom": "madmom",
        }
        for key, module in checks.items():
            try:
                __import__(module)
                self._status_labels[key].setText("installiert")
                self._status_labels[key].setStyleSheet(
                    "font-weight: bold; color: #2a7a2a; margin-left: 20px;"
                )
                self._engines[key].setEnabled(True)
            except ImportError:
                self._status_labels[key].setText("nicht installiert")
                self._status_labels[key].setStyleSheet(
                    "font-weight: bold; color: #c03030; margin-left: 20px;"
                )
                self._engines[key].setEnabled(False)

        # Default Engine auswählen (beste verfügbare)
        if self._engines.get("demucs+pyin") and self._engines["demucs+pyin"].isEnabled():
            self._engines["demucs+pyin"].setChecked(True)
            self._selected_engine = "demucs+pyin"
        elif self._engines.get("pyin") and self._engines["pyin"].isEnabled():
            self._engines["pyin"].setChecked(True)
            self._selected_engine = "pyin"

    @property
    def selected_engine(self) -> str:
        for key, radio in self._engines.items():
            if radio.isChecked():
                return key
        return "pyin"
