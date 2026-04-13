"""Taktart-Datenklasse."""

from __future__ import annotations


class TimeSignature:
    """Taktart (z.B. 4/4, 3/4, 6/8).

    Attributes:
        numerator: Zähler (z.B. 4)
        denominator: Nenner (z.B. 4)
    """

    def __init__(self, numerator: int = 4, denominator: int = 4):
        self.numerator = numerator
        self.denominator = denominator

    def beats_per_measure(self) -> float:
        """Anzahl Viertelnoten-Beats pro Takt."""
        return self.numerator * (4.0 / self.denominator)

    def __repr__(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    def to_dict(self) -> dict:
        return {"numerator": self.numerator, "denominator": self.denominator}

    @classmethod
    def from_dict(cls, data: dict) -> TimeSignature:
        return cls(data.get("numerator", 4), data.get("denominator", 4))
