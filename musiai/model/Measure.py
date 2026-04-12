"""Takt-Datenklasse."""

from __future__ import annotations
from musiai.model.Note import Note
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo


class Measure:
    """Ein einzelner Takt mit Noten.

    Attributes:
        number: Taktnummer (1-basiert)
        time_signature: Taktart
        tempo: Tempo (falls Tempowechsel in diesem Takt)
        notes: Liste der Noten im Takt
        duration_deviation: Dauer-Abweichung (1.0=Standard, <1=kürzer, >1=länger)
    """

    def __init__(
        self,
        number: int = 1,
        time_signature: TimeSignature | None = None,
        tempo: Tempo | None = None,
    ):
        self.number = number
        self.time_signature = time_signature or TimeSignature()
        self.tempo = tempo
        self.notes: list[Note] = []
        self.duration_deviation: float = 1.0

    @property
    def duration_beats(self) -> float:
        return self.time_signature.beats_per_measure()

    @property
    def effective_duration_beats(self) -> float:
        """Tatsächliche Dauer inkl. Abweichung."""
        return self.duration_beats * self.duration_deviation

    def duration_seconds(self, tempo_bpm: float) -> float:
        return self.effective_duration_beats * (60.0 / tempo_bpm)

    def add_note(self, note: Note) -> None:
        self.notes.append(note)
        self.notes.sort(key=lambda n: n.start_beat)

    def remove_note(self, note: Note) -> None:
        self.notes.remove(note)

    def get_note_at(self, beat: float, tolerance: float = 0.1) -> Note | None:
        for note in self.notes:
            if abs(note.start_beat - beat) < tolerance:
                return note
        return None

    def to_dict(self) -> dict:
        result = {
            "number": self.number,
            "time_signature": self.time_signature.to_dict(),
            "notes": [n.to_dict() for n in self.notes],
            "duration_deviation": self.duration_deviation,
        }
        if self.tempo:
            result["tempo"] = self.tempo.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> Measure:
        measure = cls(
            number=data["number"],
            time_signature=TimeSignature.from_dict(data.get("time_signature", {})),
            tempo=Tempo.from_dict(data["tempo"]) if "tempo" in data else None,
        )
        measure.duration_deviation = data.get("duration_deviation", 1.0)
        for note_data in data.get("notes", []):
            measure.notes.append(Note.from_dict(note_data))
        return measure
