"""MeasureParser - Parst einzelne <measure> Elemente."""

import logging
import xml.etree.ElementTree as ET
from musiai.model.Measure import Measure
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo
from musiai.musicXML.NoteParser import NoteParser

logger = logging.getLogger("musiai.musicXML.measure_parser")


class MeasureParseState:
    """Zustand der während des Parsens eines Parts mitgeführt wird."""

    def __init__(self):
        self.divisions = 1
        self.velocity = 80
        self.tempo = 120.0
        self.abs_beat = 0.0
        self.time_signature = TimeSignature(4, 4)
        self.key_sharps = 0  # Key signature (+ = sharps, - = flats)


class MeasureParser:
    """Parst ein MusicXML <measure> Element."""

    @staticmethod
    def parse(measure_elem: ET.Element, ns: str, state: MeasureParseState,
              tempos_list: list[Tempo], staff_filter: int = 0) -> Measure:
        """<measure> Element → Measure mit allen Noten und Attributen.

        staff_filter: 0 = alle Noten, 1/2/... = nur Noten mit <staff>N</staff>.
        """
        measure_num = int(measure_elem.get("number", "1"))
        measure = Measure(number=measure_num, time_signature=TimeSignature(
            state.time_signature.numerator, state.time_signature.denominator
        ))

        MeasureParser._parse_attributes(measure_elem, ns, state, measure)

        current_beat = 0.0

        for elem in measure_elem:
            tag = elem.tag.replace(ns, "")

            if tag == "backup":
                dur_elem = elem.find(f"{ns}duration")
                if dur_elem is not None and dur_elem.text:
                    current_beat -= int(dur_elem.text) / state.divisions
                    current_beat = max(0.0, current_beat)
                continue

            if tag == "forward":
                dur_elem = elem.find(f"{ns}duration")
                if dur_elem is not None and dur_elem.text:
                    current_beat += int(dur_elem.text) / state.divisions
                continue

            if tag == "direction":
                MeasureParser._parse_direction(
                    elem, ns, state, measure, tempos_list, current_beat
                )

            elif tag == "note":
                # Staff-Filter: Note überspringen wenn falcher Staff
                if staff_filter > 0:
                    staff_elem = elem.find(f"{ns}staff")
                    note_staff = int(staff_elem.text) if (
                        staff_elem is not None and staff_elem.text
                    ) else 1
                    if note_staff != staff_filter:
                        # Beat trotzdem vorwärts bewegen (für Timing)
                        if not NoteParser.is_chord(elem, ns):
                            dur_ticks = NoteParser.get_duration_ticks(elem, ns)
                            if dur_ticks is not None:
                                current_beat += dur_ticks / state.divisions
                        continue

                current_beat = MeasureParser._handle_note(
                    elem, ns, state, measure, current_beat
                )

        return measure

    @staticmethod
    def _parse_attributes(measure_elem: ET.Element, ns: str,
                          state: MeasureParseState, measure: Measure) -> None:
        attrs = measure_elem.find(f"{ns}attributes")
        if attrs is None:
            return

        div_elem = attrs.find(f"{ns}divisions")
        if div_elem is not None and div_elem.text:
            state.divisions = int(div_elem.text)

        key_elem = attrs.find(f"{ns}key")
        if key_elem is not None:
            fifths_elem = key_elem.find(f"{ns}fifths")
            if fifths_elem is not None and fifths_elem.text:
                state.key_sharps = int(fifths_elem.text)

        time_elem = attrs.find(f"{ns}time")
        if time_elem is not None:
            beats_elem = time_elem.find(f"{ns}beats")
            beat_type_elem = time_elem.find(f"{ns}beat-type")
            if beats_elem is not None and beat_type_elem is not None:
                ts = TimeSignature(int(beats_elem.text), int(beat_type_elem.text))
                measure.time_signature = ts
                state.time_signature = ts  # Für nachfolgende Takte merken

    @staticmethod
    def _parse_direction(elem: ET.Element, ns: str, state: MeasureParseState,
                         measure: Measure, tempos_list: list[Tempo],
                         current_beat: float) -> None:
        sound = elem.find(f".//{ns}sound")
        if sound is None:
            return

        tempo_attr = sound.get("tempo")
        if tempo_attr:
            state.tempo = float(tempo_attr)
            tempos_list.append(Tempo(state.tempo, state.abs_beat + current_beat))
            measure.tempo = Tempo(state.tempo)

        dynamics_attr = sound.get("dynamics")
        if dynamics_attr:
            state.velocity = int(float(dynamics_attr))

    @staticmethod
    def _handle_note(note_elem: ET.Element, ns: str, state: MeasureParseState,
                     measure: Measure, current_beat: float) -> float:
        """Note parsen und zur Measure hinzufügen. Gibt neue Beat-Position zurück."""
        note = NoteParser.parse(
            note_elem, ns, state.divisions, state.velocity, current_beat
        )

        if note is not None:
            is_grace = note_elem.find(f"{ns}grace") is not None
            # Akkord: gleiche Position wie vorherige Note
            if NoteParser.is_chord(note_elem, ns):
                if measure.notes:
                    note.start_beat = measure.notes[-1].start_beat
            elif is_grace:
                # Grace note: place slightly before current_beat
                note.start_beat = current_beat
                # Don't advance current_beat
            else:
                note.start_beat = current_beat
                dur_ticks = NoteParser.get_duration_ticks(note_elem, ns)
                if dur_ticks is not None:
                    current_beat += dur_ticks / state.divisions
            measure.add_note(note)
        else:
            # Pause
            if not NoteParser.is_chord(note_elem, ns):
                dur_ticks = NoteParser.get_duration_ticks(note_elem, ns)
                if dur_ticks is not None:
                    current_beat += dur_ticks / state.divisions

        return current_beat
