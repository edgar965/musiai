"""Expression-Daten einer einzelnen Note."""

from __future__ import annotations
from musiai.util.Constants import DEFAULT_VELOCITY, DEFAULT_DURATION_DEVIATION


class Expression:
    """Speichert die expressiven Parameter einer Note.

    Attributes:
        velocity: Lautstärke 0-127 (80=Standard, <80=leiser/gelb, >80=lauter/blau)
        cent_offset: Tonhöhen-Abweichung in Cent (-50 bis +50)
        duration_deviation: Tempo-Faktor ab dieser Note (1.0=Standard, 0.8=20% langsamer, 1.2=20% schneller)
        glide_type: Art der Cent-Visualisierung ('none', 'zigzag', 'curve')
    """

    def __init__(
        self,
        velocity: int = DEFAULT_VELOCITY,
        cent_offset: float = 0.0,
        duration_deviation: float = DEFAULT_DURATION_DEVIATION,
        glide_type: str = "none",
    ):
        self.velocity = velocity
        self.cent_offset = cent_offset
        self.duration_deviation = duration_deviation
        self.glide_type = glide_type

    def to_dict(self) -> dict:
        return {
            "velocity": self.velocity,
            "cent_offset": self.cent_offset,
            "duration_deviation": self.duration_deviation,
            "glide_type": self.glide_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Expression:
        return cls(
            velocity=data.get("velocity", DEFAULT_VELOCITY),
            cent_offset=data.get("cent_offset", 0.0),
            duration_deviation=data.get("duration_deviation", DEFAULT_DURATION_DEVIATION),
            glide_type=data.get("glide_type", "none"),
        )
