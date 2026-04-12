"""Tempo-Datenklasse."""

from __future__ import annotations


class Tempo:
    """Tempo an einer bestimmten Position.

    Attributes:
        bpm: Beats pro Minute
        beat_position: Absolute Beat-Position im Stück (0.0 = Anfang)
    """

    def __init__(self, bpm: float = 120.0, beat_position: float = 0.0):
        self.bpm = bpm
        self.beat_position = beat_position

    def seconds_per_beat(self) -> float:
        """Sekunden pro Viertelnote."""
        return 60.0 / self.bpm

    def to_dict(self) -> dict:
        return {"bpm": self.bpm, "beat_position": self.beat_position}

    @classmethod
    def from_dict(cls, data: dict) -> Tempo:
        return cls(data.get("bpm", 120.0), data.get("beat_position", 0.0))
