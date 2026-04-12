"""PropertiesPanel - Sidebar zum Bearbeiten der Eigenschaften."""

import logging
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QSlider,
    QComboBox, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from musiai.model.Note import Note
from musiai.model.TimeSignature import TimeSignature

logger = logging.getLogger("musiai.ui.PropertiesPanel")


class PropertiesPanel(QDockWidget):
    """Sidebar: Zeigt und editiert Eigenschaften des ausgewählten Objekts."""

    velocity_changed = Signal(int)
    cent_offset_changed = Signal(float)
    duration_changed = Signal(float)
    glide_type_changed = Signal(str)
    time_sig_changed = Signal(int, int)
    # Stimme
    part_instrument_changed = Signal(int, int)  # part_index, program
    part_muted_changed = Signal(int, bool)      # part_index, muted
    part_name_changed = Signal(int, str)        # part_index, name
    part_soundfont_requested = Signal(int)      # part_index → Datei-Dialog
    part_delete_requested = Signal(int)         # part_index → Stimme löschen
    part_detect_requested = Signal(int)         # part_index → Noten erkennen
    tempo_changed = Signal(float)

    def __init__(self):
        super().__init__("Eigenschaften")
        self.setMinimumWidth(230)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self._current_note: Note | None = None
        self._updating = False
        self._setup_ui()
        self._show_empty()

    def _setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._type_label = QLabel("Nichts ausgewählt")
        self._type_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #555; "
            "padding: 6px; background: #f0f0f5; border-radius: 4px;"
        )
        layout.addWidget(self._type_label)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(QWidget())                    # 0: Leer
        self._stack.addWidget(self._build_note_page())      # 1: Note
        self._stack.addWidget(self._build_time_sig_page())  # 2: Taktart
        self._stack.addWidget(self._build_clef_page())      # 3: Schlüssel
        self._stack.addWidget(self._build_part_page())      # 4: Stimme

        layout.addStretch()
        self.setWidget(container)

    def _build_note_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self._note_label = QLabel("")
        self._note_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._note_label)

        vel_group = QGroupBox("Velocity (Lautstärke)")
        vel_lay = QFormLayout(vel_group)
        self._vel_slider = QSlider(Qt.Orientation.Horizontal)
        self._vel_slider.setRange(0, 127)
        self._vel_slider.setValue(80)
        self._vel_label = QLabel("80 — f (forte)")
        self._vel_slider.valueChanged.connect(self._on_velocity_changed)
        vel_lay.addRow(self._vel_label, self._vel_slider)
        layout.addWidget(vel_group)

        cent_group = QGroupBox("Tonhöhe (Cent-Offset)")
        cent_lay = QFormLayout(cent_group)
        self._cent_slider = QSlider(Qt.Orientation.Horizontal)
        self._cent_slider.setRange(-50, 50)
        self._cent_slider.setValue(0)
        self._cent_label = QLabel("0 ct")
        self._cent_slider.valueChanged.connect(self._on_cent_changed)
        cent_lay.addRow(self._cent_label, self._cent_slider)
        self._glide_combo = QComboBox()
        self._glide_combo.addItems(["none", "zigzag", "curve"])
        self._glide_combo.currentTextChanged.connect(self._on_glide_changed)
        cent_lay.addRow("Typ:", self._glide_combo)
        layout.addWidget(cent_group)

        dur_group = QGroupBox("Dauer-Abweichung")
        dur_lay = QFormLayout(dur_group)
        self._dur_spin = QDoubleSpinBox()
        self._dur_spin.setRange(0.10, 10.0)
        self._dur_spin.setValue(1.0)
        self._dur_spin.setSingleStep(0.10)  # Pfeiltasten: ±0.10
        self._dur_spin.setDecimals(2)
        self._dur_spin.setKeyboardTracking(False)
        self._dur_spin.setToolTip(
            "Dauer-Faktor: 1.0 = Standard\n"
            "Pfeiltasten: ±0.10 pro Schritt"
        )
        self._dur_spin.valueChanged.connect(self._on_duration_changed)
        dur_lay.addRow("Faktor:", self._dur_spin)
        layout.addWidget(dur_group)
        return page

    def _build_time_sig_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        ts_group = QGroupBox("Taktart")
        ts_lay = QFormLayout(ts_group)
        self._ts_num = QSpinBox()
        self._ts_num.setRange(1, 16)
        self._ts_num.setValue(4)
        self._ts_num.valueChanged.connect(self._on_ts_changed)
        ts_lay.addRow("Zähler:", self._ts_num)
        self._ts_den = QSpinBox()
        self._ts_den.setRange(1, 16)
        self._ts_den.setValue(4)
        self._ts_den.valueChanged.connect(self._on_ts_changed)
        ts_lay.addRow("Nenner:", self._ts_den)
        self._ts_beats_label = QLabel("= 4.0 Beats pro Takt")
        ts_lay.addRow(self._ts_beats_label)
        layout.addWidget(ts_group)

        tempo_group = QGroupBox("Tempo")
        tempo_lay = QFormLayout(tempo_group)
        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(20, 300)
        self._tempo_spin.setValue(120)
        self._tempo_spin.setSuffix(" BPM")
        self._tempo_spin.valueChanged.connect(self._on_tempo_changed)
        tempo_lay.addRow("BPM:", self._tempo_spin)
        self._tempo_name = QLabel("Allegro")
        self._tempo_name.setStyleSheet("color: #2a7a2a; font-weight: bold;")
        tempo_lay.addRow("Bezeichnung:", self._tempo_name)
        layout.addWidget(tempo_group)

        return page

    def _build_clef_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        group = QGroupBox("Notenschlüssel")
        g_lay = QFormLayout(group)
        self._clef_combo = QComboBox()
        self._clef_combo.addItems(["Violinschlüssel (G)", "Bassschlüssel (F)", "Altschlüssel (C)"])
        g_lay.addRow("Schlüssel:", self._clef_combo)
        layout.addWidget(group)
        return page

    def _build_part_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Stimm-Name
        name_group = QGroupBox("Stimme")
        name_lay = QFormLayout(name_group)
        self._part_name_edit = QComboBox()
        self._part_name_edit.setEditable(True)
        self._part_name_edit.addItems([
            "Klavier", "Violine", "Viola", "Cello", "Kontrabass",
            "Flöte", "Oboe", "Klarinette", "Fagott",
            "Trompete", "Posaune", "Horn", "Tuba",
            "Akustik-Gitarre", "E-Gitarre", "E-Bass", "Harfe",
        ])
        self._part_name_edit.currentTextChanged.connect(self._on_part_name_changed)
        name_lay.addRow("Name:", self._part_name_edit)
        layout.addWidget(name_group)

        # Instrument (MIDI Program)
        instr_group = QGroupBox("Instrument (MIDI)")
        instr_lay = QFormLayout(instr_group)
        self._part_instrument = QComboBox()
        self._load_instruments()
        self._part_instrument.currentIndexChanged.connect(
            self._on_part_instrument_changed
        )
        instr_lay.addRow("Sound:", self._part_instrument)
        layout.addWidget(instr_group)

        # SoundFont
        sf_group = QGroupBox("SoundFont (.sf2)")
        sf_lay = QFormLayout(sf_group)
        from PySide6.QtWidgets import QPushButton
        self._sf_label = QLabel("Standard (Windows GM)")
        self._sf_label.setStyleSheet("color: #555; font-size: 9px;")
        sf_lay.addRow(self._sf_label)
        self._sf_button = QPushButton("SoundFont laden...")
        self._sf_button.clicked.connect(self._on_sf_button)
        sf_lay.addRow(self._sf_button)
        layout.addWidget(sf_group)

        # Mute
        from PySide6.QtWidgets import QCheckBox
        self._part_mute = QCheckBox("Stumm (Mute)")
        self._part_mute.toggled.connect(self._on_part_mute_changed)
        layout.addWidget(self._part_mute)

        # Noten erkennen (nur bei Audio-Stimmen)
        from PySide6.QtWidgets import QPushButton
        self._detect_button = QPushButton("Noten erkennen...")
        self._detect_button.setStyleSheet(
            "background: #2060b0; color: white; font-weight: bold; "
            "padding: 4px; border-radius: 3px;"
        )
        self._detect_button.clicked.connect(self._on_detect)
        self._detect_button.setVisible(False)
        layout.addWidget(self._detect_button)

        # Info
        self._part_info = QLabel("")
        self._part_info.setStyleSheet("color: #888; font-size: 9px;")
        layout.addWidget(self._part_info)

        # Stimme löschen
        self._delete_part_btn = QPushButton("Stimme löschen")
        self._delete_part_btn.setStyleSheet(
            "background: #c03030; color: white; padding: 4px; "
            "border-radius: 3px; margin-top: 8px;"
        )
        self._delete_part_btn.clicked.connect(self._on_delete_part)
        layout.addWidget(self._delete_part_btn)

        return page

    def _load_instruments(self) -> None:
        """Instrumente aus JSON laden."""
        import json, os
        # Pfad relativ zum Projektverzeichnis (neben main.py)
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "media", "Stimmen", "instruments.json")
        self._instrument_programs: list[int] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for cat in data["categories"]:
                for instr in cat["instruments"]:
                    self._part_instrument.addItem(
                        f"{instr['name']}  ({cat['name']})"
                    )
                    self._instrument_programs.append(instr["program"])
        except Exception as e:
            logger.warning(f"instruments.json nicht geladen: {e}")
            # Fallback: nur Klavier
            self._part_instrument.addItem("Klavier")
            self._instrument_programs.append(0)

    # ---- Show ----

    def show_note(self, note: Note) -> None:
        self._updating = True
        self._current_note = note
        self._type_label.setText(f"Note: {note.name} (MIDI {note.pitch})")
        self._note_label.setText(f"{note.name} — Beat {note.start_beat:.1f}")
        self._vel_slider.setValue(note.expression.velocity)
        self._update_vel_label(note.expression.velocity)
        self._cent_slider.setValue(int(note.expression.cent_offset))
        self._cent_label.setText(f"{note.expression.cent_offset:.0f} ct")
        self._dur_spin.setValue(note.expression.duration_deviation)
        idx = self._glide_combo.findText(note.expression.glide_type)
        if idx >= 0:
            self._glide_combo.setCurrentIndex(idx)
        self._stack.setCurrentIndex(1)
        self._updating = False

    def show_time_signature(self, ts: TimeSignature, tempo: float = 120) -> None:
        self._updating = True
        self._type_label.setText(f"Takt: {ts}")
        self._ts_num.setValue(ts.numerator)
        self._ts_den.setValue(ts.denominator)
        self._ts_beats_label.setText(f"= {ts.beats_per_measure():.1f} Beats pro Takt")
        self._tempo_spin.setValue(int(tempo))
        from musiai.notation.TempoMarking import TempoMarking
        self._tempo_name.setText(TempoMarking.from_bpm(tempo))
        self._stack.setCurrentIndex(2)
        self._updating = False

    def show_clef(self) -> None:
        self._type_label.setText("Notenschlüssel")
        self._stack.setCurrentIndex(3)

    def show_part(self, part, part_index: int) -> None:
        """Stimm-Eigenschaften anzeigen."""
        self._updating = True
        self._current_part_index = part_index
        self._type_label.setText(f"Stimme: {part.name}")
        # Name
        idx = self._part_name_edit.findText(part.name)
        if idx >= 0:
            self._part_name_edit.setCurrentIndex(idx)
        else:
            self._part_name_edit.setEditText(part.name)
        # Instrument
        if part.instrument in self._instrument_programs:
            self._part_instrument.setCurrentIndex(
                self._instrument_programs.index(part.instrument)
            )
        # Mute
        self._part_mute.setChecked(part.muted)
        # Detect-Button nur bei Audio-Stimmen
        has_audio = part.audio_track is not None
        self._detect_button.setVisible(has_audio)
        if has_audio:
            dur = part.audio_track.duration_seconds
            self._sf_label.setText(
                f"Audio: {part.audio_track.file_path.split('/')[-1]} "
                f"({dur:.1f}s)"
            )
        # Info
        n_notes = sum(len(m.notes) for m in part.measures)
        self._part_info.setText(
            f"Kanal: {part.channel} | Takte: {len(part.measures)} | "
            f"Noten: {n_notes}"
        )
        self._stack.setCurrentIndex(4)
        self._updating = False

    def clear(self) -> None:
        self._current_note = None
        self._show_empty()

    def _show_empty(self) -> None:
        self._type_label.setText("Nichts ausgewählt")
        self._stack.setCurrentIndex(0)

    # ---- Callbacks ----

    def _update_vel_label(self, value: int) -> None:
        from musiai.notation.TempoMarking import DynamicMarking
        self._vel_label.setText(f"{value} — {DynamicMarking.format_dynamic(value)}")

    def _on_velocity_changed(self, value: int) -> None:
        if self._updating:
            return
        self._update_vel_label(value)
        self.velocity_changed.emit(value)

    def _on_cent_changed(self, value: int) -> None:
        if self._updating:
            return
        self._cent_label.setText(f"{value} ct")
        self.cent_offset_changed.emit(float(value))

    def _on_duration_changed(self, value: float) -> None:
        if self._updating:
            return
        self.duration_changed.emit(value)

    def _on_glide_changed(self, text: str) -> None:
        if self._updating:
            return
        self.glide_type_changed.emit(text)

    def _on_ts_changed(self) -> None:
        if self._updating:
            return
        n, d = self._ts_num.value(), self._ts_den.value()
        self._ts_beats_label.setText(f"= {TimeSignature(n, d).beats_per_measure():.1f} Beats pro Takt")
        self.time_sig_changed.emit(n, d)

    def _on_tempo_changed(self, value: int) -> None:
        if self._updating:
            return
        from musiai.notation.TempoMarking import TempoMarking
        self._tempo_name.setText(TempoMarking.from_bpm(float(value)))
        self.tempo_changed.emit(float(value))

    def _on_part_name_changed(self, text: str) -> None:
        if self._updating:
            return
        self.part_name_changed.emit(self._current_part_index, text)

    def _on_part_instrument_changed(self, idx: int) -> None:
        if self._updating or idx < 0:
            return
        program = self._instrument_programs[idx]
        self.part_instrument_changed.emit(self._current_part_index, program)

    def _on_part_mute_changed(self, checked: bool) -> None:
        if self._updating:
            return
        self.part_muted_changed.emit(self._current_part_index, checked)

    def _on_sf_button(self) -> None:
        if self._updating:
            return
        self.part_soundfont_requested.emit(self._current_part_index)

    def _on_delete_part(self) -> None:
        self.part_delete_requested.emit(self._current_part_index)

    def _on_detect(self) -> None:
        self.part_detect_requested.emit(self._current_part_index)

