"""NoteParser - Parst einzelne <note> Elemente."""

import logging
import xml.etree.ElementTree as ET
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.musicXML.PitchParser import PitchParser
from musiai.musicXML.MusicXmlConstants import DYNAMICS_TO_VELOCITY

logger = logging.getLogger("musiai.musicXML.note_parser")


class NoteParser:
    """Parst ein MusicXML <note> Element mit allen Expression-Daten.

    Unterstützt:
    - Mikrotöne (dezimale <alter>)
    - Dynamik (<dynamics>, <sound dynamics="X"/>)
    - Glissando/Slide
    - Triolen (time-modification)
    - Akkorde (<chord/>)
    - Pausen (<rest/>)
    """

    @staticmethod
    def parse(note_elem: ET.Element, ns: str, divisions: int,
              current_velocity: int, current_beat: float) -> Note | None:
        """<note> Element → Note oder None (bei Pause)."""
        # Pause?
        if note_elem.find(f"{ns}rest") is not None:
            return None

        # Pitch parsen
        pitch_elem = note_elem.find(f"{ns}pitch")
        if pitch_elem is None:
            return None

        pitch_result = PitchParser.parse(pitch_elem, ns)
        if pitch_result is None:
            return None

        # Grace note? Use short duration (32nd = 0.125 beats)
        is_grace = note_elem.find(f"{ns}grace") is not None

        # Duration
        if is_grace:
            duration_beats = 0.125
        else:
            duration_beats = NoteParser._parse_duration(
                note_elem, ns, divisions)

        # Velocity
        velocity = NoteParser._parse_velocity(note_elem, ns, current_velocity)

        # Cent-Offset und Glide-Typ
        cent_offset = pitch_result.cent_offset
        glide_type = NoteParser._parse_glide_type(note_elem, ns, cent_offset)

        # Duration Deviation (Triolen etc.)
        duration_deviation = NoteParser._parse_duration_deviation(note_elem, ns)

        expression = Expression(
            velocity=max(0, min(127, velocity)),
            cent_offset=cent_offset,
            duration_deviation=duration_deviation,
            glide_type=glide_type,
        )

        return Note(
            pitch=pitch_result.midi_note,
            start_beat=current_beat,
            duration_beats=duration_beats,
            expression=expression,
        )

    @staticmethod
    def is_chord(note_elem: ET.Element, ns: str) -> bool:
        """Prüft ob die Note Teil eines Akkords ist."""
        return note_elem.find(f"{ns}chord") is not None

    @staticmethod
    def get_duration_ticks(note_elem: ET.Element, ns: str) -> int | None:
        """Duration in Ticks aus dem Element lesen."""
        dur_elem = note_elem.find(f"{ns}duration")
        if dur_elem is not None and dur_elem.text:
            return int(dur_elem.text)
        return None

    @staticmethod
    def _parse_duration(note_elem: ET.Element, ns: str, divisions: int) -> float:
        dur_elem = note_elem.find(f"{ns}duration")
        if dur_elem is not None and dur_elem.text:
            return int(dur_elem.text) / divisions
        return 1.0

    @staticmethod
    def _parse_velocity(note_elem: ET.Element, ns: str, current_velocity: int) -> int:
        velocity = current_velocity

        # Dynamik-Bezeichnungen (<dynamics><f/></dynamics>)
        note_dynamics = note_elem.find(f".//{ns}dynamics")
        if note_dynamics is not None:
            for dyn_name, dyn_vel in DYNAMICS_TO_VELOCITY.items():
                if note_dynamics.find(f"{ns}{dyn_name}") is not None:
                    velocity = dyn_vel
                    break

        # Exakter Wert aus <sound dynamics="X"/>
        sound = note_elem.find(f".//{ns}sound")
        if sound is not None:
            dyn_attr = sound.get("dynamics")
            if dyn_attr:
                velocity = int(float(dyn_attr))

        return velocity

    @staticmethod
    def _parse_glide_type(note_elem: ET.Element, ns: str, cent_offset: float) -> str:
        if note_elem.find(f".//{ns}glissando") is not None:
            return "curve"
        if note_elem.find(f".//{ns}slide") is not None:
            return "curve"
        if abs(cent_offset) > 0.5:
            return "zigzag"
        return "none"

    @staticmethod
    def _parse_duration_deviation(note_elem: ET.Element, ns: str) -> float:
        time_mod = note_elem.find(f"{ns}time-modification")
        if time_mod is not None:
            actual = time_mod.find(f"{ns}actual-notes")
            normal = time_mod.find(f"{ns}normal-notes")
            if actual is not None and normal is not None:
                return int(normal.text) / int(actual.text)
        return 1.0
