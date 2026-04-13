"""PitchParser - Parst <pitch> Elemente inkl. Mikrotöne."""

import logging
import xml.etree.ElementTree as ET
from musiai.musicXML.MusicXmlConstants import STEP_TO_SEMITONE

logger = logging.getLogger("musiai.musicXML.pitch_parser")


class PitchResult:
    """Ergebnis eines Pitch-Parsings."""

    def __init__(self, midi_note: int, cent_offset: float):
        self.midi_note = midi_note
        self.cent_offset = cent_offset


class PitchParser:
    """Parst MusicXML <pitch> Elemente mit voller Mikrotöne-Unterstützung.

    Unterstützt dezimale <alter> Werte:
    - <alter>1</alter>     → 1 Halbton hoch (C#)
    - <alter>0.5</alter>   → Viertelton hoch (50 Cent)
    - <alter>0.04</alter>  → 4 Cent hoch (Mikrotöne)
    - <alter>-0.10</alter> → 10 Cent tief
    """

    @staticmethod
    def parse(pitch_elem: ET.Element, ns: str = "") -> PitchResult | None:
        """<pitch> Element → PitchResult mit MIDI-Note und Cent-Offset."""
        step_elem = pitch_elem.find(f"{ns}step")
        octave_elem = pitch_elem.find(f"{ns}octave")

        if step_elem is None or octave_elem is None:
            return None

        step = step_elem.text
        octave = int(octave_elem.text)

        # Alter: kann dezimal sein (Mikrotöne!)
        alter = 0.0
        alter_elem = pitch_elem.find(f"{ns}alter")
        if alter_elem is not None and alter_elem.text:
            alter = float(alter_elem.text)

        # MIDI-Note berechnen
        semitone = STEP_TO_SEMITONE.get(step, 0)
        midi_note = (octave + 1) * 12 + semitone

        # Ganzzahliger Alter-Anteil → Halbtöne
        alter_semitones = int(round(alter))
        midi_note += alter_semitones

        # Dezimaler Rest → Cent-Offset
        cent_offset = (alter - alter_semitones) * 100.0

        return PitchResult(midi_note, cent_offset)
