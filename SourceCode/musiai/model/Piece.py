"""Piece-Datenklasse (ein Musikstück)."""

from __future__ import annotations
from musiai.model.Part import Part
from musiai.model.Tempo import Tempo


class Piece:
    """Ein vollständiges Musikstück.

    Attributes:
        title: Titel des Stücks
        parts: Liste der Stimmen/Tracks
        tempos: Tempo-Änderungen über das Stück
    """

    def __init__(self, title: str = "Unbenannt"):
        self.title = title
        self.parts: list[Part] = []
        self.tempos: list[Tempo] = [Tempo(120.0, 0.0)]
        self.source_file: str | None = None  # Original file path

    def add_part(self, part: Part) -> None:
        self.parts.append(part)

    @property
    def initial_tempo(self) -> float:
        return self.tempos[0].bpm if self.tempos else 120.0

    def tempo_at_beat(self, beat: float) -> float:
        """Tempo an einer bestimmten Beat-Position."""
        current_bpm = 120.0
        for tempo in self.tempos:
            if tempo.beat_position <= beat:
                current_bpm = tempo.bpm
            else:
                break
        return current_bpm

    @property
    def total_measures(self) -> int:
        if not self.parts:
            return 0
        return max(len(p.measures) for p in self.parts)

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "parts": [p.to_dict() for p in self.parts],
            "tempos": [t.to_dict() for t in self.tempos],
        }
        if self.source_file:
            d["source_file"] = self.source_file
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Piece:
        piece = cls(title=data.get("title", "Unbenannt"))
        piece.tempos = [Tempo.from_dict(t) for t in data.get("tempos", [])]
        piece.source_file = data.get("source_file")
        for part_data in data.get("parts", []):
            piece.parts.append(Part.from_dict(part_data))
        return piece
