"""ZoomWidget - Zoom-Steuerung unten rechts (Word-Stil)."""

import logging
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QSlider, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger("musiai.ui.ZoomWidget")


class ZoomWidget(QWidget):
    """Zoom-Leiste mit -/+ Buttons und Slider, wie in Microsoft Word."""

    zoom_changed = Signal(float)  # Faktor 0.25 - 4.0

    # Slider 0..100, Mitte (50) = 100%.
    # Links (0) = 25%, Rechts (100) = 400%.
    # Logarithmische Skalierung damit 100% exakt in der Mitte sitzt.
    _SLIDER_MAX = 100
    _SLIDER_MID = 50

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()
        self.setFixedHeight(28)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        btn_style = (
            "QPushButton { border: 1px solid #aaa; border-radius: 3px; "
            "padding: 1px 6px; background: #f0f0f5; font-weight: bold; }"
            "QPushButton:hover { background: #dde; }"
        )

        self._minus_btn = QPushButton("\u2212")  # minus sign
        self._minus_btn.setFixedSize(24, 22)
        self._minus_btn.setStyleSheet(btn_style)
        self._minus_btn.clicked.connect(self._zoom_out_step)
        layout.addWidget(self._minus_btn)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, self._SLIDER_MAX)
        self._slider.setValue(self._SLIDER_MID)  # 100% in der Mitte
        self._slider.setFixedWidth(120)
        self._slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._slider)

        self._plus_btn = QPushButton("+")
        self._plus_btn.setFixedSize(24, 22)
        self._plus_btn.setStyleSheet(btn_style)
        self._plus_btn.clicked.connect(self._zoom_in_step)
        layout.addWidget(self._plus_btn)

        self._label = QLabel("100%")
        self._label.setFixedWidth(40)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(self._label)

    def _slider_to_percent(self, val: int) -> int:
        """Slider-Wert (0-100) → Zoom-Prozent. Mitte(50)=100%."""
        import math
        if val <= self._SLIDER_MID:
            # 0→25%, 50→100%  (log scale)
            t = val / self._SLIDER_MID  # 0..1
            return max(25, int(25 * (100 / 25) ** t))
        else:
            # 50→100%, 100→400%  (log scale)
            t = (val - self._SLIDER_MID) / self._SLIDER_MID  # 0..1
            return min(400, int(100 * (400 / 100) ** t))

    def _percent_to_slider(self, pct: int) -> int:
        """Zoom-Prozent → Slider-Wert (0-100). 100%→50."""
        import math
        pct = max(25, min(400, pct))
        if pct <= 100:
            # 25%→0, 100%→50
            t = math.log(pct / 25) / math.log(100 / 25)
            return int(t * self._SLIDER_MID)
        else:
            # 100%→50, 400%→100
            t = math.log(pct / 100) / math.log(400 / 100)
            return int(self._SLIDER_MID + t * self._SLIDER_MID)

    def _on_slider(self, value: int) -> None:
        pct = self._slider_to_percent(value)
        self._label.setText(f"{pct}%")
        self.zoom_changed.emit(pct / 100.0)

    def _zoom_in_step(self) -> None:
        self._slider.setValue(min(self._slider.value() + 5, self._SLIDER_MAX))

    def _zoom_out_step(self) -> None:
        self._slider.setValue(max(self._slider.value() - 5, 0))

    def set_zoom_percent(self, percent: int) -> None:
        """Zoom von aussen setzen (ohne Signal-Loop)."""
        self._slider.blockSignals(True)
        sv = self._percent_to_slider(percent)
        self._slider.setValue(sv)
        self._label.setText(f"{percent}%")
        self._slider.blockSignals(False)
