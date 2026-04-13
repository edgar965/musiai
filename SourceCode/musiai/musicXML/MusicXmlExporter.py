"""MusicXML Exporter - Exportiert das interne Model als MusicXML mit allen Expression-Daten."""

import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from musiai.model.Piece import Piece
from musiai.model.Note import Note

logger = logging.getLogger("musiai.musicXML.exporter")

SEMITONE_TO_STEP = {0: "C", 1: "C", 2: "D", 3: "D", 4: "E", 5: "F",
                    6: "F", 7: "G", 8: "G", 9: "A", 10: "A", 11: "B"}
SEMITONE_ALTER = {0: 0, 1: 1, 2: 0, 3: 1, 4: 0, 5: 0,
                  6: 1, 7: 0, 8: 1, 9: 0, 10: 1, 11: 0}

# Beats → MusicXML <type>
DURATION_TO_TYPE = [
    (4.0, "whole"), (3.0, "half"), (2.0, "half"), (1.5, "quarter"),
    (1.0, "quarter"), (0.75, "eighth"), (0.5, "eighth"),
    (0.375, "16th"), (0.25, "16th"), (0.125, "32nd"),
]


class MusicXmlExporter:
    """Exportiert ein Piece als MusicXML mit allen Mikrotönen und Expression-Daten."""

    DIVISIONS = 480

    def export_file(self, piece: Piece, path: str) -> None:
        """Piece als MusicXML-Datei schreiben."""
        logger.info(f"Exportiere MusicXML: {path}")

        root = ET.Element("score-partwise", version="4.0")

        # Titel
        work = ET.SubElement(root, "work")
        ET.SubElement(work, "work-title").text = piece.title

        # Part-List
        part_list = ET.SubElement(root, "part-list")
        for i, part in enumerate(piece.parts):
            sp = ET.SubElement(part_list, "score-part", id=f"P{i+1}")
            ET.SubElement(sp, "part-name").text = part.name

        # Parts
        for i, part in enumerate(piece.parts):
            part_elem = ET.SubElement(root, "part", id=f"P{i+1}")

            # Auto-detect clef
            clef_sign, clef_line = self._detect_clef(part)

            for m_idx, measure in enumerate(part.measures):
                measure_elem = ET.SubElement(part_elem, "measure", number=str(measure.number))

                # Attributes im ersten Takt
                if m_idx == 0:
                    attrs = ET.SubElement(measure_elem, "attributes")
                    ET.SubElement(attrs, "divisions").text = str(self.DIVISIONS)
                    key = ET.SubElement(attrs, "key")
                    ET.SubElement(key, "fifths").text = "0"
                    time = ET.SubElement(attrs, "time")
                    ET.SubElement(time, "beats").text = str(measure.time_signature.numerator)
                    ET.SubElement(time, "beat-type").text = str(measure.time_signature.denominator)
                    clef = ET.SubElement(attrs, "clef")
                    ET.SubElement(clef, "sign").text = clef_sign
                    ET.SubElement(clef, "line").text = str(clef_line)

                # Tempo
                if measure.tempo or (m_idx == 0 and piece.tempos):
                    tempo_bpm = measure.tempo.bpm if measure.tempo else piece.initial_tempo
                    direction = ET.SubElement(measure_elem, "direction")
                    sound = ET.SubElement(direction, "sound", tempo=str(tempo_bpm))

                # Noten
                for note in measure.notes:
                    self._write_note(measure_elem, note)

        # Formatiert schreiben
        xml_str = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="UTF-8")

        with open(path, "wb") as f:
            f.write(pretty)

        logger.info(f"MusicXML exportiert: {path}")

    def export_string(self, piece: Piece) -> str:
        """Piece als MusicXML-String zurückgeben (für Verovio)."""
        logger.info("Exportiere MusicXML als String")

        root = ET.Element("score-partwise", version="4.0")
        work = ET.SubElement(root, "work")
        ET.SubElement(work, "work-title").text = piece.title

        part_list = ET.SubElement(root, "part-list")
        for i, part in enumerate(piece.parts):
            sp = ET.SubElement(part_list, "score-part", id=f"P{i+1}")
            ET.SubElement(sp, "part-name").text = part.name

        for i, part in enumerate(piece.parts):
            part_elem = ET.SubElement(root, "part", id=f"P{i+1}")
            clef_sign, clef_line = self._detect_clef(part)
            for m_idx, measure in enumerate(part.measures):
                measure_elem = ET.SubElement(
                    part_elem, "measure", number=str(measure.number)
                )
                if m_idx == 0:
                    attrs = ET.SubElement(measure_elem, "attributes")
                    ET.SubElement(attrs, "divisions").text = str(self.DIVISIONS)
                    key = ET.SubElement(attrs, "key")
                    ET.SubElement(key, "fifths").text = "0"
                    time = ET.SubElement(attrs, "time")
                    ET.SubElement(time, "beats").text = str(
                        measure.time_signature.numerator
                    )
                    ET.SubElement(time, "beat-type").text = str(
                        measure.time_signature.denominator
                    )
                    clef = ET.SubElement(attrs, "clef")
                    ET.SubElement(clef, "sign").text = clef_sign
                    ET.SubElement(clef, "line").text = str(clef_line)
                if measure.tempo or (m_idx == 0 and piece.tempos):
                    tempo_bpm = (
                        measure.tempo.bpm if measure.tempo else piece.initial_tempo
                    )
                    direction = ET.SubElement(measure_elem, "direction")
                    ET.SubElement(direction, "sound", tempo=str(tempo_bpm))
                for note in measure.notes:
                    self._write_note(measure_elem, note)

        xml_str = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(xml_str).toprettyxml(
            indent="  ", encoding="UTF-8"
        )
        return pretty.decode("UTF-8")

    def _write_note(self, measure_elem: ET.Element, note: Note) -> None:
        """Eine Note als MusicXML schreiben."""
        note_elem = ET.SubElement(measure_elem, "note")

        # Pitch mit Mikrotönen
        pitch = ET.SubElement(note_elem, "pitch")
        semitone = note.pitch % 12
        octave = (note.pitch // 12) - 1
        ET.SubElement(pitch, "step").text = SEMITONE_TO_STEP[semitone]
        ET.SubElement(pitch, "octave").text = str(octave)

        # Alter: Halbton + Cent-Offset
        base_alter = SEMITONE_ALTER[semitone]
        cent_as_alter = note.expression.cent_offset / 100.0
        total_alter = base_alter + cent_as_alter
        if abs(total_alter) > 0.001:
            ET.SubElement(pitch, "alter").text = f"{total_alter:.4f}".rstrip("0").rstrip(".")

        # Duration
        duration_ticks = int(note.duration_beats * self.DIVISIONS)
        ET.SubElement(note_elem, "duration").text = str(duration_ticks)

        # Type (required by Verovio for correct note head rendering)
        note_type = self._beats_to_type(note.duration_beats)
        if note_type:
            ET.SubElement(note_elem, "type").text = note_type
            # Dot for dotted notes
            if self._is_dotted(note.duration_beats):
                ET.SubElement(note_elem, "dot")

        # Velocity als <sound dynamics="X"/>
        if note.expression.velocity != 80:
            sound = ET.SubElement(note_elem, "sound",
                                 dynamics=str(note.expression.velocity))

        # Glissando/Slide
        if note.expression.glide_type == "curve":
            notations = ET.SubElement(note_elem, "notations")
            ET.SubElement(notations, "glissando", type="start")

    @staticmethod
    def _detect_clef(part) -> tuple[str, int]:
        """Schlüssel für einen Part erkennen (G/2 oder F/4)."""
        pitches = [n.pitch for m in part.measures for n in m.notes]
        if not pitches:
            return "G", 2
        median = sorted(pitches)[len(pitches) // 2]
        if median < 55:  # Unter G3 → Bass
            return "F", 4
        return "G", 2

    @staticmethod
    def _beats_to_type(beats: float) -> str | None:
        """Beat-Dauer → MusicXML <type> String."""
        for threshold, name in DURATION_TO_TYPE:
            if beats >= threshold - 0.01:
                return name
        return "32nd"

    @staticmethod
    def _is_dotted(beats: float) -> bool:
        """Prüft ob eine Notendauer punktiert ist."""
        dotted = {3.0, 1.5, 0.75, 0.375}
        return any(abs(beats - d) < 0.01 for d in dotted)
