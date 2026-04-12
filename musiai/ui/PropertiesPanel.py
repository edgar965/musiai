"""PropertiesPanel - Sidebar zum Bearbeiten der Note-Expression."""

import logging
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QSlider,
    QComboBox, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt, Signal
from musiai.model.Note import Note
from musiai.util.PitchUtils import note_name

logger = logging.getLogger("musiai.ui.PropertiesPanel")


class PropertiesPanel(QDockWidget):
    """Sidebar: Zeigt und editiert Expression-Daten der ausgewählten Note."""

    velocity_changed = Signal(int)
    cent_offset_changed = Signal(float)
    duration_changed = Signal(float)
    glide_type_changed = Signal(str)

    def __init__(self):
        super().__init__("Eigenschaften")
        self.setMinimumWidth(220)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self._current_note: Note | None = None
        self._updating = False  # Verhindert Signal-Loops
        self._setup_ui()
        self.set_enabled(False)
        logger.debug("PropertiesPanel erstellt")

    def _setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        # Note Info
        self._note_label = QLabel("Keine Note ausgewählt")
        self._note_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ccc;")
        layout.addWidget(self._note_label)

        # Velocity
        vel_group = QGroupBox("Velocity (Lautstärke)")
        vel_layout = QFormLayout(vel_group)
        self._vel_slider = QSlider(Qt.Orientation.Horizontal)
        self._vel_slider.setRange(0, 127)
        self._vel_slider.setValue(80)
        self._vel_label = QLabel("80")
        self._vel_slider.valueChanged.connect(self._on_velocity_changed)
        vel_layout.addRow(self._vel_label, self._vel_slider)
        layout.addWidget(vel_group)

        # Cent Offset
        cent_group = QGroupBox("Tonhöhe (Cent)")
        cent_layout = QFormLayout(cent_group)
        self._cent_slider = QSlider(Qt.Orientation.Horizontal)
        self._cent_slider.setRange(-50, 50)
        self._cent_slider.setValue(0)
        self._cent_label = QLabel("0 ct")
        self._cent_slider.valueChanged.connect(self._on_cent_changed)
        cent_layout.addRow(self._cent_label, self._cent_slider)

        # Glide Type
        self._glide_combo = QComboBox()
        self._glide_combo.addItems(["none", "zigzag", "curve"])
        self._glide_combo.currentTextChanged.connect(self._on_glide_changed)
        cent_layout.addRow("Typ:", self._glide_combo)
        layout.addWidget(cent_group)

        # Duration Deviation
        dur_group = QGroupBox("Dauer-Abweichung")
        dur_layout = QFormLayout(dur_group)
        self._dur_slider = QSlider(Qt.Orientation.Horizontal)
        self._dur_slider.setRange(80, 120)
        self._dur_slider.setValue(100)
        self._dur_label = QLabel("100%")
        self._dur_slider.valueChanged.connect(self._on_duration_changed)
        dur_layout.addRow(self._dur_label, self._dur_slider)
        layout.addWidget(dur_group)

        layout.addStretch()
        self.setWidget(container)

    def show_note(self, note: Note) -> None:
        """Note-Daten im Panel anzeigen."""
        self._updating = True
        self._current_note = note
        self._note_label.setText(f"{note.name} (MIDI {note.pitch})")

        self._vel_slider.setValue(note.expression.velocity)
        self._vel_label.setText(str(note.expression.velocity))

        self._cent_slider.setValue(int(note.expression.cent_offset))
        self._cent_label.setText(f"{note.expression.cent_offset:.0f} ct")

        self._dur_slider.setValue(int(note.expression.duration_deviation * 100))
        self._dur_label.setText(f"{note.expression.duration_deviation * 100:.0f}%")

        idx = self._glide_combo.findText(note.expression.glide_type)
        if idx >= 0:
            self._glide_combo.setCurrentIndex(idx)

        self.set_enabled(True)
        self._updating = False

    def clear(self) -> None:
        """Panel zurücksetzen."""
        self._current_note = None
        self._note_label.setText("Keine Note ausgewählt")
        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        self._vel_slider.setEnabled(enabled)
        self._cent_slider.setEnabled(enabled)
        self._dur_slider.setEnabled(enabled)
        self._glide_combo.setEnabled(enabled)

    def _on_velocity_changed(self, value: int) -> None:
        if self._updating:
            return
        self._vel_label.setText(str(value))
        self.velocity_changed.emit(value)

    def _on_cent_changed(self, value: int) -> None:
        if self._updating:
            return
        self._cent_label.setText(f"{value} ct")
        self.cent_offset_changed.emit(float(value))

    def _on_duration_changed(self, value: int) -> None:
        if self._updating:
            return
        deviation = value / 100.0
        self._dur_label.setText(f"{value}%")
        self.duration_changed.emit(deviation)

    def _on_glide_changed(self, text: str) -> None:
        if self._updating:
            return
        self.glide_type_changed.emit(text)
