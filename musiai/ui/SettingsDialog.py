"""SettingsDialog - Einstellungen mit Tab-Controls."""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QLabel, QPushButton,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

logger = logging.getLogger("musiai.ui.SettingsDialog")


class SettingsDialog(QDialog):
    """Einstellungen-Dialog mit Tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(500, 420)
        self._selected_engine = "pyin"
        self._setup_ui()
        self._detect_engines()
        self._detect_pdf_engines()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_detection_tab(), "Notenerkennung")
        self._tabs.addTab(self._build_audio_tab(), "Audio")
        self._tabs.addTab(self._build_pdf_tab(), "PDF")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---- Notenerkennung Tab ----

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

    # ---- PDF Tab ----

    def _build_pdf_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Import-Engines
        import_group = QGroupBox("PDF → Noten (OMR Import-Engine)")
        ig_lay = QVBoxLayout(import_group)
        self._pdf_import_group = QButtonGroup(self)
        self._pdf_import_engines = {}
        self._pdf_import_status = {}

        from musiai.pdf.PdfEngineConfig import PdfEngineConfig
        for i, (key, info) in enumerate(PdfEngineConfig.IMPORT_ENGINES.items()):
            radio = QRadioButton(info["name"])
            desc = QLabel(info["desc"])
            desc.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
            status = QLabel("")
            status.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self._pdf_import_group.addButton(radio, i)
            self._pdf_import_engines[key] = radio
            self._pdf_import_status[key] = status
            ig_lay.addWidget(radio)
            ig_lay.addWidget(desc)
            ig_lay.addWidget(status)

        layout.addWidget(import_group)

        # Export-Engines
        export_group = QGroupBox("Noten → PDF (Export-Engine)")
        eg_lay = QVBoxLayout(export_group)
        self._pdf_export_group = QButtonGroup(self)
        self._pdf_export_engines = {}
        self._pdf_export_status = {}

        for i, (key, info) in enumerate(PdfEngineConfig.EXPORT_ENGINES.items()):
            radio = QRadioButton(info["name"])
            desc = QLabel(info["desc"])
            desc.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
            status = QLabel("")
            status.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self._pdf_export_group.addButton(radio, i)
            self._pdf_export_engines[key] = radio
            self._pdf_export_status[key] = status
            eg_lay.addWidget(radio)
            eg_lay.addWidget(desc)
            eg_lay.addWidget(status)

        layout.addWidget(export_group)
        return page

    # ---- Engine Detection ----

    def _detect_engines(self) -> None:
        """Prüft welche Noten-Erkennungs-Engines installiert sind."""
        checks = {
            "basic-pitch": None,
            "demucs+pyin": "demucs",
            "pyin": "librosa",
        }
        for key, module in checks.items():
            available = False
            if key == "basic-pitch":
                import os
                available = os.path.exists(os.path.join("python310ENV", "python.exe"))
            else:
                try:
                    __import__(module)
                    available = True
                except ImportError:
                    pass

            self._set_engine_status(
                self._status_labels[key], self._engines[key], available
            )

        for pref in ["basic-pitch", "demucs+pyin", "pyin"]:
            if self._engines.get(pref) and self._engines[pref].isEnabled():
                self._engines[pref].setChecked(True)
                self._selected_engine = pref
                break

    def _detect_pdf_engines(self) -> None:
        """Prüft welche PDF-Engines installiert sind."""
        from musiai.pdf.PdfEngineConfig import PdfEngineConfig

        import_avail = PdfEngineConfig.detect_import_engines()
        for key, available in import_avail.items():
            self._set_engine_status(
                self._pdf_import_status[key],
                self._pdf_import_engines[key],
                available,
            )

        # Erste verfügbare Import-Engine selektieren
        for key in PdfEngineConfig.IMPORT_ENGINES:
            if self._pdf_import_engines[key].isEnabled():
                self._pdf_import_engines[key].setChecked(True)
                break

        export_avail = PdfEngineConfig.detect_export_engines()
        for key, available in export_avail.items():
            self._set_engine_status(
                self._pdf_export_status[key],
                self._pdf_export_engines[key],
                available,
            )

        for key in PdfEngineConfig.EXPORT_ENGINES:
            if self._pdf_export_engines[key].isEnabled():
                self._pdf_export_engines[key].setChecked(True)
                break

    @staticmethod
    def _set_engine_status(label: QLabel, radio: QRadioButton,
                           available: bool) -> None:
        """Status-Label und Radio-Button für eine Engine setzen."""
        if available:
            label.setText("installiert")
            label.setStyleSheet(
                "font-weight: bold; color: #2a7a2a; margin-left: 20px;"
            )
            radio.setEnabled(True)
        else:
            label.setText("nicht installiert")
            label.setStyleSheet(
                "font-weight: bold; color: #c03030; margin-left: 20px;"
            )
            radio.setEnabled(False)

    # ---- Properties ----

    @property
    def selected_engine(self) -> str:
        for key, radio in self._engines.items():
            if radio.isChecked():
                return key
        return "pyin"

    @property
    def selected_pdf_import_engine(self) -> str:
        for key, radio in self._pdf_import_engines.items():
            if radio.isChecked():
                return key
        return "audiveris"

    @property
    def selected_pdf_export_engine(self) -> str:
        for key, radio in self._pdf_export_engines.items():
            if radio.isChecked():
                return key
        return "lilypond"
