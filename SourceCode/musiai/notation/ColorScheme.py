"""Farbschema: Velocity → Farbe, Dauer-Abweichung → Farbe."""

import logging
from PySide6.QtGui import QColor
from PySide6.QtCore import QSettings
from musiai.util.Constants import DEFAULT_VELOCITY

logger = logging.getLogger("musiai.notation.ColorScheme")


class ColorScheme:
    """Berechnet Farben aus Expression-Werten.

    Velocity: Leise(0) → Standard(80) → Laut(127)
    Farben konfigurierbar über Einstellungen > MusicXML.
    Dauer: Rot-Gelb(kürzer) → Grau(exakt) → Blau(länger)
    """

    # Cached colors (loaded once, refreshed on settings change)
    _color_std: QColor | None = None
    _color_soft: QColor | None = None
    _color_loud: QColor | None = None

    @classmethod
    def _load_colors(cls) -> None:
        """Load velocity colors from QSettings."""
        settings = QSettings("MusiAI", "MusiAI")
        cls._color_std = QColor(
            settings.value("musicxml/vel_color_std", "#FF0000"))
        cls._color_soft = QColor(
            settings.value("musicxml/vel_color_soft", "#FFFF00"))
        cls._color_loud = QColor(
            settings.value("musicxml/vel_color_loud", "#0000FF"))

    @classmethod
    def reload_colors(cls) -> None:
        """Force reload from settings (call after settings change)."""
        cls._load_colors()

    @classmethod
    def velocity_to_color(cls, velocity: int) -> QColor:
        """Velocity (0-127) → QColor.

        Interpoliert zwischen soft(0), standard(80), loud(127).
        """
        if cls._color_std is None:
            cls._load_colors()

        velocity = max(0, min(127, velocity))

        if velocity <= DEFAULT_VELOCITY:
            t = velocity / DEFAULT_VELOCITY
            return _lerp_color(cls._color_soft, cls._color_std, t)
        else:
            t = (velocity - DEFAULT_VELOCITY) / (127 - DEFAULT_VELOCITY)
            return _lerp_color(cls._color_std, cls._color_loud, t)

    @staticmethod
    def duration_to_color(deviation: float) -> QColor:
        """Tempo-Abweichung (0.8-1.2) → QColor.

        <1.0: Rot-Gelb (langsamer / rit.)
        =1.0: Grau (Standard-Tempo)
        >1.0: Blau (schneller / accel.)
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


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolation between two colors."""
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    return QColor(r, g, b)
