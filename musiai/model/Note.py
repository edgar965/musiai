"""Noten-Datenklasse - Kerneinheit des Modells."""

from __future__ import annotations
from musiai.model.Expression import Expression
from musiai.util.PitchUtils import note_name, midi_to_frequency


class Note:
    """Eine einzelne Note mit Expression-Daten.

    Attributes:
        pitch: MIDI-Notennummer (0-127, 60=C4)
        start_beat: Position innerhalb des Takts (0.0 = Taktanfang)
        duration_beats: Dauer in Viertelnoten-Beats
        expression: Expression-Daten (Velocity, Cents, Dauer-Abweichung)
    """

    def __init__(
        self,
        pitch: int = 60,
        start_beat: float = 0.0,
        duration_beats: float = 1.0,
        expression: Expression | None = None,
    ):
        self.pitch = pitch
        self.start_beat = start_beat
        self.duration_beats = duration_beats
        self.expression = expression or Expression()

    @property
    def name(self) -> str:
        return note_name(self.pitch)

    @property
    def frequency(self) -> float:
        return midi_to_frequency(self.pitch, self.expression.cent_offset)

    @property
    def end_beat(self) -> float:
        return self.start_beat + self.duration_beats

    def to_dict(self) -> dict:
        return {
            "pitch": self.pitch,
            "start_beat": self.start_beat,
            "duration_beats": self.duration_beats,
            "expression": self.expression.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Note:
        return cls(
            pitch=data["pitch"],
            start_beat=data["start_beat"],
            duration_beats=data["duration_beats"],
            expression=Expression.from_dict(data.get("expression", {})),
        )
