"""Part-Datenklasse (eine Instrumentenstimme)."""

from __future__ import annotations
from musiai.model.Measure import Measure
from musiai.model.Note import Note


class Part:
    """Eine Instrumentenstimme/Track.

    Attributes:
        name: Name des Instruments/Parts
        channel: MIDI-Kanal (0-15)
        measures: Liste der Takte
    """

    def __init__(self, name: str = "Klavier", channel: int = 0):
        self.name = name
        self.channel = channel
        self.measures: list[Measure] = []

    def add_measure(self, measure: Measure) -> None:
        self.measures.append(measure)

    def get_all_notes(self) -> list[Note]:
        """Alle Noten über alle Takte hinweg."""
        notes = []
        for measure in self.measures:
            notes.extend(measure.notes)
        return notes

    def get_measure(self, number: int) -> Measure | None:
        """Takt nach Nummer finden (1-basiert)."""
        for measure in self.measures:
            if measure.number == number:
                return measure
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "channel": self.channel,
            "measures": [m.to_dict() for m in self.measures],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Part:
        part = cls(name=data.get("name", "Klavier"), channel=data.get("channel", 0))
        for measure_data in data.get("measures", []):
            part.measures.append(Measure.from_dict(measure_data))
        return part
