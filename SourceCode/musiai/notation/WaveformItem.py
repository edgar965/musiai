"""WaveformItem - QGraphicsItem das eine Audio-Wellenform zeichnet."""

import logging
import numpy as np
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import QRectF

logger = logging.getLogger("musiai.notation.WaveformItem")


class WaveformItem(QGraphicsItem):
    """Zeichnet eine Audio-Wellenform als farbige Fläche."""

    WAVE_HEIGHT = 40  # Pixel Höhe der Waveform

    def __init__(self, samples: np.ndarray, sr: int,
                 width: float, x: float, y: float, block_idx: int = 0):
        super().__init__()
        self.setPos(x, y)
        self._width = width
        self._block_idx = block_idx
        self.setZValue(3)
        self.setAcceptHoverEvents(True)

        # Waveform berechnen (downsampled)
        pixel_w = max(1, int(width))
        if len(samples) > 0:
            spp = max(1, len(samples) // pixel_w)
            n = pixel_w * spp
            trimmed = samples[:n]
            if len(trimmed) >= pixel_w:
                self._envelope = np.max(
                    np.abs(trimmed.reshape(pixel_w, -1)), axis=1
                )
            else:
                self._envelope = np.abs(trimmed)
        else:
            self._envelope = np.zeros(pixel_w)

        # Normalisieren
        mx = self._envelope.max()
        if mx > 0:
            self._envelope = self._envelope / mx

        # Tag für Klick-Erkennung
        self.setData(0, "waveform")
        self.setData(1, block_idx)

    def boundingRect(self) -> QRectF:
        h = self.WAVE_HEIGHT
        return QRectF(0, -h, self._width, h * 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        h = self.WAVE_HEIGHT

        # Hintergrund
        painter.setBrush(QBrush(QColor(220, 235, 255, 60)))
        painter.setPen(QPen(QColor(100, 150, 220, 100), 0.5))
        painter.drawRect(0, -h, self._width, h * 2)

        # Waveform
        pen = QPen(QColor(40, 100, 200, 180), 1)
        painter.setPen(pen)
        for i, amp in enumerate(self._envelope):
            y_amp = amp * h
            painter.drawLine(int(i), int(-y_amp), int(i), int(y_amp))

        # Mittellinie
        painter.setPen(QPen(QColor(40, 100, 200, 80), 0.5))
        painter.drawLine(0, 0, int(self._width), 0)

    def hoverEnterEvent(self, event):
        from PySide6.QtCore import Qt
        self.setCursor(Qt.CursorShape.IBeamCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)
