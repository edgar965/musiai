"""Farbschema: Velocity → Farbe, Dauer-Abweichung → Farbe."""

import logging
from PySide6.QtGui import QColor
from musiai.util.Constants import DEFAULT_VELOCITY

logger = logging.getLogger("musiai.notation.ColorScheme")


class ColorScheme:
    """Berechnet Farben aus Expression-Werten.

    Velocity: Gelb(0) → Rot(80/Standard) → Blau(127)
    Dauer: Rot-Gelb(kürzer) → Grau(exakt) → Blau(länger)
    """

    @staticmethod
    def velocity_to_color(velocity: int) -> QColor:
        """Velocity (0-127) → QColor.

        0=Gelb, 80=Rot (Standard), 127=Blau
        """
        velocity = max(0, min(127, velocity))

        if velocity <= DEFAULT_VELOCITY:
            # Gelb(0) → Rot(80)
            t = velocity / DEFAULT_VELOCITY
            r = 255
            g = int(255 * (1 - t))
            b = 0
        else:
            # Rot(80) → Blau(127)
            t = (velocity - DEFAULT_VELOCITY) / (127 - DEFAULT_VELOCITY)
            r = int(255 * (1 - t))
            g = 0
            b = int(255 * t)

        return QColor(r, g, b)

    @staticmethod
    def duration_to_color(deviation: float) -> QColor:
        """Dauer-Abweichung (0.8-1.2) → QColor.

        <1.0: Rot-Gelb (kürzer)
        =1.0: Grau (Standard)
        >1.0: Blau (länger)
        """
        if abs(deviation - 1.0) < 0.01:
            return QColor(100, 100, 100)  # Grau = Standard

        if deviation < 1.0:
            t = min((1.0 - deviation) / 0.2, 1.0)
            r = 255
            g = int(200 * (1 - t))
            b = 0
            return QColor(r, g, b)
        else:
            t = min((deviation - 1.0) / 0.2, 1.0)
            r = 0
            g = 0
            b = int(255 * t)
            return QColor(r, g, b)

    @staticmethod
    def cent_marker_color() -> QColor:
        """Farbe für Cent-Offset Marker (Zacken/Bögen)."""
        return QColor(255, 180, 50)
