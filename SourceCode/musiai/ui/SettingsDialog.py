"""SettingsDialog - Einstellungen mit Tab-Controls."""

import logging
import os
import subprocess
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QLabel, QPushButton,
    QDialogButtonBox, QFontComboBox, QSpinBox, QCheckBox,
    QColorDialog, QHBoxLayout, QSlider,
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QSettings

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
        self._tabs.addTab(self._build_beat_tab(), "Beat-Erkennung")
        self._tabs.addTab(self._build_omr_tab(), "Noten von Bild")
        self._tabs.addTab(self._build_audio_tab(), "Audio")
        self._tabs.addTab(self._build_ui_tab(), "UI")
        self._tabs.addTab(self._build_musicxml_tab(), "MusicXML")
        self._tabs.addTab(self._build_pdf_tab(), "PDF")
        self._tabs.addTab(self._build_logging_tab(), "Logging")

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

    def _build_beat_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Engine für Beat-Erkennung")
        g_lay = QVBoxLayout(group)
        self._beat_engine_group = QButtonGroup(self)
        self._beat_engines = {}
        self._beat_status = {}

        from musiai.audio.BeatDetector import BeatDetector
        for i, (key, info) in enumerate(BeatDetector.ENGINES.items()):
            radio = QRadioButton(info["name"])
            desc = QLabel(info["desc"])
            desc.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
            status = QLabel("")
            status.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self._beat_engine_group.addButton(radio, i)
            self._beat_engines[key] = radio
            self._beat_status[key] = status
            g_lay.addWidget(radio)
            g_lay.addWidget(desc)
            g_lay.addWidget(status)

        layout.addWidget(group)

        # Detect available engines
        avail = BeatDetector.detect_available()
        for key, available in avail.items():
            self._set_engine_status(
                self._beat_status[key], self._beat_engines[key], available)
        # Select first available
        for key in BeatDetector.ENGINES:
            if self._beat_engines[key].isEnabled():
                self._beat_engines[key].setChecked(True)
                break

        layout.addStretch()
        return page

    @property
    def selected_beat_engine(self) -> str:
        for key, radio in self._beat_engines.items():
            if radio.isChecked():
                return key
        return "librosa"

    def _build_omr_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Engine für Noten-Erkennung aus Bild/PDF")
        g_lay = QVBoxLayout(group)
        self._omr_engine_group = QButtonGroup(self)
        self._omr_engines = {}
        self._omr_status = {}

        from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
        for i, (key, info) in enumerate(SheetMusicRecognizer.ENGINES.items()):
            radio = QRadioButton(info["name"])
            desc = QLabel(info["desc"])
            desc.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
            status = QLabel("")
            status.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self._omr_engine_group.addButton(radio, i)
            self._omr_engines[key] = radio
            self._omr_status[key] = status
            g_lay.addWidget(radio)
            g_lay.addWidget(desc)
            g_lay.addWidget(status)

        layout.addWidget(group)

        avail = SheetMusicRecognizer.detect_available()
        for key, available in avail.items():
            self._set_engine_status(
                self._omr_status[key], self._omr_engines[key], available)
        for key in SheetMusicRecognizer.ENGINES:
            if self._omr_engines[key].isEnabled():
                self._omr_engines[key].setChecked(True)
                break

        layout.addStretch()
        return page

    @property
    def selected_omr_engine(self) -> str:
        for key, radio in self._omr_engines.items():
            if radio.isChecked():
                return key
        return "oemer"

    def _build_audio_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Audio-Einstellungen (zukünftig)"))
        layout.addStretch()
        return page

    # ---- UI Tab ----

    def _build_ui_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        settings = QSettings("MusiAI", "MusiAI")

        # Letztes Projekt beim Start öffnen
        self._reopen_last = QCheckBox(
            "Letztes Projekt beim Start öffnen")
        self._reopen_last.setChecked(
            settings.value("ui/reopen_last_project", "false") == "true"
        )
        layout.addWidget(self._reopen_last)

        layout.addStretch()
        return page

    def _update_color_button(self) -> None:
        self._chord_color_btn.setStyleSheet(
            f"background-color: {self._chord_color_hex}; "
            f"min-width: 60px; min-height: 24px; border: 1px solid #888;"
        )
        self._chord_color_btn.setText(self._chord_color_hex)

    def _pick_chord_color(self) -> None:
        color = QColorDialog.getColor(
            QColor(self._chord_color_hex), self, "Akkord-Farbe wählen"
        )
        if color.isValid():
            self._chord_color_hex = color.name()
            self._update_color_button()

    # ---- MusicXML Tab ----

    def _build_musicxml_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        settings = QSettings("MusiAI", "MusiAI")

        # Bravura-Glyphen (moved from UI tab)
        self._musicxml_bravura = QCheckBox(
            "Bravura-Glyphen für Noten (MusicXML-Ansicht)")
        self._musicxml_bravura.setChecked(
            settings.value("ui/musicxml_bravura", "false") == "true"
        )
        layout.addWidget(self._musicxml_bravura)

        # Akkorde (moved from UI tab)
        self._chords_default = QCheckBox("Akkorde per Default anzeigen")
        self._chords_default.setChecked(
            settings.value("ui/chords_default", "false") == "true"
        )
        layout.addWidget(self._chords_default)

        chord_group = QGroupBox("Font Akkorde")
        chord_form = QFormLayout(chord_group)
        self._chord_font_combo = QFontComboBox()
        family = settings.value("ui/chord_font_family", "Arial")
        self._chord_font_combo.setCurrentFont(QFont(family))
        chord_form.addRow("Schriftart:", self._chord_font_combo)
        self._chord_font_size = QSpinBox()
        self._chord_font_size.setRange(6, 72)
        self._chord_font_size.setValue(
            int(settings.value("ui/chord_font_size", 11)))
        chord_form.addRow("Schriftgröße:", self._chord_font_size)
        self._chord_bold = QCheckBox("Fett")
        self._chord_bold.setChecked(
            settings.value("ui/chord_font_bold", "true") == "true")
        chord_form.addRow("", self._chord_bold)
        self._chord_italic = QCheckBox("Kursiv")
        self._chord_italic.setChecked(
            settings.value("ui/chord_font_italic", "false") == "true")
        chord_form.addRow("", self._chord_italic)
        color_row = QHBoxLayout()
        self._chord_color_btn = QPushButton()
        self._chord_color_hex = settings.value(
            "ui/chord_font_color", "#0044AA")
        self._update_color_button()
        self._chord_color_btn.clicked.connect(self._pick_chord_color)
        color_row.addWidget(self._chord_color_btn)
        color_row.addStretch()
        chord_form.addRow("Farbe:", color_row)
        layout.addWidget(chord_group)

        group = QGroupBox("Lautstärke-Farben (Velocity)")
        form = QFormLayout(group)

        info = QLabel(
            "Velocity 0-127 (Standard=80, mf).\n"
            "Noten werden zwischen diesen drei Farben interpoliert."
        )
        info.setStyleSheet("color: #666; font-size: 10px;")
        form.addRow(info)

        # Standard color (velocity = 80)
        self._vel_color_std_hex = settings.value(
            "musicxml/vel_color_std", "#FF0000")
        self._vel_color_std_btn = QPushButton()
        self._update_vel_btn(self._vel_color_std_btn, self._vel_color_std_hex)
        self._vel_color_std_btn.clicked.connect(
            lambda: self._pick_vel_color("std"))
        form.addRow("Standard (mf, Vel 80):", self._vel_color_std_btn)

        # Soft color (velocity = 0)
        self._vel_color_soft_hex = settings.value(
            "musicxml/vel_color_soft", "#FFFF00")
        self._vel_color_soft_btn = QPushButton()
        self._update_vel_btn(self._vel_color_soft_btn, self._vel_color_soft_hex)
        self._vel_color_soft_btn.clicked.connect(
            lambda: self._pick_vel_color("soft"))
        form.addRow("Leiser (pp, Vel 0):", self._vel_color_soft_btn)

        # Loud color (velocity = 127)
        self._vel_color_loud_hex = settings.value(
            "musicxml/vel_color_loud", "#0000FF")
        self._vel_color_loud_btn = QPushButton()
        self._update_vel_btn(self._vel_color_loud_btn, self._vel_color_loud_hex)
        self._vel_color_loud_btn.clicked.connect(
            lambda: self._pick_vel_color("loud"))
        form.addRow("Lauter (ff, Vel 127):", self._vel_color_loud_btn)

        layout.addWidget(group)

        # Pitch (cent offset) colors
        pitch_group = QGroupBox("Tonhöhen-Farben (Cent-Abweichung)")
        pitch_form = QFormLayout(pitch_group)

        pitch_info = QLabel(
            "Farben für Tonhöhen-Abweichung (Zacken/Bögen)."
        )
        pitch_info.setStyleSheet("color: #666; font-size: 10px;")
        pitch_form.addRow(pitch_info)

        self._pitch_color_std_hex = settings.value(
            "musicxml/pitch_color_std", "#FF8C1E")
        self._pitch_color_std_btn = QPushButton()
        self._update_vel_btn(self._pitch_color_std_btn, self._pitch_color_std_hex)
        self._pitch_color_std_btn.clicked.connect(
            lambda: self._pick_pitch_color("std"))
        pitch_form.addRow("Standard:", self._pitch_color_std_btn)

        self._pitch_color_high_hex = settings.value(
            "musicxml/pitch_color_high", "#FF4400")
        self._pitch_color_high_btn = QPushButton()
        self._update_vel_btn(self._pitch_color_high_btn, self._pitch_color_high_hex)
        self._pitch_color_high_btn.clicked.connect(
            lambda: self._pick_pitch_color("high"))
        pitch_form.addRow("Höher (+Cent):", self._pitch_color_high_btn)

        self._pitch_color_low_hex = settings.value(
            "musicxml/pitch_color_low", "#0088FF")
        self._pitch_color_low_btn = QPushButton()
        self._update_vel_btn(self._pitch_color_low_btn, self._pitch_color_low_hex)
        self._pitch_color_low_btn.clicked.connect(
            lambda: self._pick_pitch_color("low"))
        pitch_form.addRow("Tiefer (-Cent):", self._pitch_color_low_btn)

        layout.addWidget(pitch_group)
        layout.addStretch()
        return page

    def _pick_pitch_color(self, which: str) -> None:
        mapping = {
            "std": (self._pitch_color_std_btn, "_pitch_color_std_hex"),
            "high": (self._pitch_color_high_btn, "_pitch_color_high_hex"),
            "low": (self._pitch_color_low_btn, "_pitch_color_low_hex"),
        }
        btn, attr = mapping[which]
        current = getattr(self, attr)
        color = QColorDialog.getColor(QColor(current), self, "Farbe wählen")
        if color.isValid():
            setattr(self, attr, color.name())
            self._update_vel_btn(btn, color.name())

    @staticmethod
    def _update_vel_btn(btn: QPushButton, hex_color: str) -> None:
        btn.setStyleSheet(
            f"background-color: {hex_color}; "
            f"min-width: 60px; min-height: 24px; border: 1px solid #888;"
        )
        btn.setText(hex_color)

    def _pick_vel_color(self, which: str) -> None:
        mapping = {
            "std": (self._vel_color_std_btn, "_vel_color_std_hex"),
            "soft": (self._vel_color_soft_btn, "_vel_color_soft_hex"),
            "loud": (self._vel_color_loud_btn, "_vel_color_loud_hex"),
        }
        btn, attr = mapping[which]
        current = getattr(self, attr)
        color = QColorDialog.getColor(QColor(current), self, "Farbe wählen")
        if color.isValid():
            setattr(self, attr, color.name())
            self._update_vel_btn(btn, color.name())

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

    # ---- Logging Tab ----

    def _build_logging_tab(self) -> QWidget:
        from musiai.util.LoggingConfig import LOG_DIR, LEVEL_NAMES

        page = QWidget()
        layout = QVBoxLayout(page)

        settings = QSettings("MusiAI", "MusiAI")
        current_level = int(settings.value("logging/level", 4))

        group = QGroupBox("Log-Level")
        g_lay = QFormLayout(group)

        self._log_level_slider = QSlider(Qt.Orientation.Horizontal)
        self._log_level_slider.setRange(1, 10)
        self._log_level_slider.setValue(current_level)
        self._log_level_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._log_level_slider.setTickInterval(1)
        self._log_level_slider.setSingleStep(1)

        self._log_level_label = QLabel(
            f"{current_level} - {LEVEL_NAMES.get(current_level, 'INFO')}"
        )
        self._log_level_label.setStyleSheet("font-weight: bold;")
        self._log_level_slider.valueChanged.connect(self._on_log_level_changed)

        g_lay.addRow("Level (1-10):", self._log_level_slider)
        g_lay.addRow("Aktuell:", self._log_level_label)

        desc = QLabel(
            "1 = CRITICAL  |  2 = ERROR  |  3 = WARNING\n"
            "4 = INFO (Standard)  |  5-10 = DEBUG (zunehmend detailliert)"
        )
        desc.setStyleSheet("color: #666; font-size: 9px;")
        g_lay.addRow(desc)

        layout.addWidget(group)

        # Open logs button
        open_btn = QPushButton("Log-Dateien offnen")
        open_btn.clicked.connect(lambda: self._open_log_dir(str(LOG_DIR)))
        layout.addWidget(open_btn)

        layout.addStretch()
        return page

    def _on_log_level_changed(self, value: int) -> None:
        from musiai.util.LoggingConfig import LEVEL_NAMES
        name = LEVEL_NAMES.get(value, "INFO")
        self._log_level_label.setText(f"{value} - {name}")

    @staticmethod
    def _open_log_dir(path: str) -> None:
        """Open the log directory in file explorer."""
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

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
                base = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", "..", ".."))
                available = os.path.exists(
                    os.path.join(base, "python310ENV", "python.exe"))
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

    @property
    def chord_font(self) -> QFont:
        font = QFont(self._chord_font_combo.currentFont().family(),
                      self._chord_font_size.value())
        if self._chord_bold.isChecked():
            font.setWeight(QFont.Weight.Bold)
        if self._chord_italic.isChecked():
            font.setItalic(True)
        return font

    @property
    def chord_color(self) -> QColor:
        return QColor(self._chord_color_hex)

    @property
    def log_level(self) -> int:
        """Return the selected log level (1-10)."""
        return self._log_level_slider.value()

    def accept(self) -> None:
        settings = QSettings("MusiAI", "MusiAI")
        settings.setValue("ui/musicxml_bravura",
                          "true" if self._musicxml_bravura.isChecked()
                          else "false")
        settings.setValue("ui/chord_font_family",
                          self._chord_font_combo.currentFont().family())
        settings.setValue("ui/chord_font_size", self._chord_font_size.value())
        settings.setValue("ui/chord_font_bold",
                          "true" if self._chord_bold.isChecked() else "false")
        settings.setValue("ui/chord_font_italic",
                          "true" if self._chord_italic.isChecked() else "false")
        settings.setValue("ui/chord_font_color", self._chord_color_hex)
        settings.setValue("ui/chords_default",
                          "true" if self._chords_default.isChecked() else "false")
        # MusicXML velocity colors
        settings.setValue("musicxml/vel_color_std", self._vel_color_std_hex)
        settings.setValue("musicxml/vel_color_soft", self._vel_color_soft_hex)
        settings.setValue("musicxml/vel_color_loud", self._vel_color_loud_hex)
        # Pitch colors
        settings.setValue("musicxml/pitch_color_std", self._pitch_color_std_hex)
        settings.setValue("musicxml/pitch_color_high", self._pitch_color_high_hex)
        settings.setValue("musicxml/pitch_color_low", self._pitch_color_low_hex)
        # UI
        settings.setValue("ui/reopen_last_project",
                          "true" if self._reopen_last.isChecked() else "false")
        settings.setValue("logging/level", self._log_level_slider.value())
        super().accept()
