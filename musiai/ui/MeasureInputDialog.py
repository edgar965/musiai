"""MeasureInputDialog - Dialog zur Eingabe von Taktlängen."""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QFormLayout,
)
from musiai.model.TimeSignature import TimeSignature

logger = logging.getLogger("musiai.ui.MeasureInputDialog")


class MeasureInputDialog(QDialog):
    """Dialog um Taktart und Anzahl Takte einzugeben."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Takte vorgeben")
        self.setMinimumWidth(300)

        self.result_time_signature: TimeSignature | None = None
        self.result_measure_count: int = 0
        self.result_tempo: float = 120.0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Taktart
        ts_layout = QHBoxLayout()
        self._numerator = QSpinBox()
        self._numerator.setRange(1, 16)
        self._numerator.setValue(4)
        ts_layout.addWidget(self._numerator)
        ts_layout.addWidget(QLabel("/"))
        self._denominator = QSpinBox()
        self._denominator.setRange(1, 16)
        self._denominator.setValue(4)
        ts_layout.addWidget(self._denominator)
        form.addRow("Taktart:", ts_layout)

        # Anzahl Takte
        self._measure_count = QSpinBox()
        self._measure_count.setRange(1, 999)
        self._measure_count.setValue(4)
        form.addRow("Anzahl Takte:", self._measure_count)

        # Tempo
        self._tempo = QSpinBox()
        self._tempo.setRange(20, 300)
        self._tempo.setValue(120)
        form.addRow("Tempo (BPM):", self._tempo)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _accept(self) -> None:
        self.result_time_signature = TimeSignature(
            self._numerator.value(), self._denominator.value()
        )
        self.result_measure_count = self._measure_count.value()
        self.result_tempo = float(self._tempo.value())
        self.accept()
