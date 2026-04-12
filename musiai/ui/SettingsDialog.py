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
            ("basic-pitch", "Spotify basic-pitch (polyphon)",
             "Beste polyphone Erkennung. Nutzt TF-Modell\n"
             "in separater Python 3.10 Umgebung."),
            ("demucs+pyin", "demucs + pyin (polyphon)",
             "Trennt Audio in Stimmen (Vocals/Bass/Drums/Other),\n"
             "dann erkennt pyin jede Stimme einzeln."),
            ("pyin", "librosa pyin (monophon)",
             "Schnell, erkennt eine Stimme. Gut für Solo-Instrumente."),
        ]

        self._status_labels = {}
        for i, (key, name, desc) in enumerate(engines_info):
            radio = QRadioButton(name)
            info = QLabel(desc)
            info.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
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
            "basic-pitch": None,  # Special check via subprocess
            "demucs+pyin": "demucs",
            "pyin": "librosa",
        }
        for key, module in checks.items():
            available = False
            if key == "basic-pitch":
                # Nur prüfen ob python310ENV existiert (schnell)
                import os
                available = os.path.exists(os.path.join("python310ENV", "python.exe"))
            else:
                try:
                    __import__(module)
                    available = True
                except ImportError:
                    pass

            if available:
                self._status_labels[key].setText("installiert")
                self._status_labels[key].setStyleSheet(
                    "font-weight: bold; color: #2a7a2a; margin-left: 20px;"
                )
                self._engines[key].setEnabled(True)
            else:
                self._status_labels[key].setText("nicht installiert")
                self._status_labels[key].setStyleSheet(
                    "font-weight: bold; color: #c03030; margin-left: 20px;"
                )
                self._engines[key].setEnabled(False)

        # Default: beste verfügbare Engine
        for pref in ["basic-pitch", "demucs+pyin", "pyin"]:
            if self._engines.get(pref) and self._engines[pref].isEnabled():
                self._engines[pref].setChecked(True)
                self._selected_engine = pref
                break

    @property
    def selected_engine(self) -> str:
        for key, radio in self._engines.items():
            if radio.isChecked():
                return key
        return "pyin"
