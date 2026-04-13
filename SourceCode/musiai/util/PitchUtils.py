"""Tonhöhen-Umrechnungen: MIDI, Frequenz, Cent, Notennamen."""

import math

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_frequency(midi_note: int, cent_offset: float = 0.0) -> float:
    """MIDI-Notennummer → Frequenz in Hz (mit optionalem Cent-Offset)."""
    return 440.0 * math.pow(2, (midi_note - 69 + cent_offset / 100.0) / 12.0)


def frequency_to_midi(frequency: float) -> tuple[int, float]:
    """Frequenz in Hz → (MIDI-Note, Cent-Abweichung)."""
    if frequency <= 0:
        return 0, 0.0
    midi_float = 69 + 12 * math.log2(frequency / 440.0)
    midi_note = round(midi_float)
    cents = (midi_float - midi_note) * 100
    return midi_note, cents


def note_name(midi_note: int) -> str:
    """MIDI-Notennummer → Notenname (z.B. 60 → 'C4')."""
    octave = (midi_note // 12) - 1
    name = NOTE_NAMES[midi_note % 12]
    return f"{name}{octave}"


def name_to_midi(name: str) -> int:
    """Notenname → MIDI-Notennummer (z.B. 'C4' → 60)."""
    for i, n in enumerate(NOTE_NAMES):
        if name.startswith(n):
            rest = name[len(n):]
            try:
                octave = int(rest)
                return (octave + 1) * 12 + i
            except ValueError:
                break
    raise ValueError(f"Ungültiger Notenname: {name}")


def cents_to_pitch_bend(cents: float, bend_range: int = 2) -> int:
    """Cent-Offset → MIDI Pitch Bend Wert (0-16383, 8192=Mitte)."""
    semitones = cents / 100.0
    ratio = semitones / bend_range
    return int(8192 + ratio * 8192)
