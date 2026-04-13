"""MusicXML Exporter - Vollständiger Export mit Akkorden, Pausen, Vorzeichen."""

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
ACCIDENTAL_NAME = {1: "sharp", -1: "flat"}

# Beats → (type, dotted)
DURATION_MAP = [
    (4.0, "whole", False), (3.0, "half", True), (2.0, "half", False),
    (1.5, "quarter", True), (1.0, "quarter", False),
    (0.75, "eighth", True), (0.5, "eighth", False),
    (0.375, "16th", True), (0.25, "16th", False),
    (0.1875, "32nd", True), (0.125, "32nd", False),
]


class MusicXmlExporter:
    """Exportiert ein Piece als vollständiges MusicXML."""

    DIVISIONS = 480

    def export_file(self, piece: Piece, path: str) -> None:
        root = self._build_xml(piece)
        pretty = self._prettify(root)
        with open(path, "wb") as f:
            f.write(pretty)
        logger.info(f"MusicXML exportiert: {path}")

    def export_string(self, piece: Piece) -> str:
        root = self._build_xml(piece)
        return self._prettify(root).decode("UTF-8")

    def _build_xml(self, piece: Piece) -> ET.Element:
        root = ET.Element("score-partwise", version="4.0")

        # Identification
        work = ET.SubElement(root, "work")
        ET.SubElement(work, "work-title").text = piece.title
        ident = ET.SubElement(root, "identification")
        encoding = ET.SubElement(ident, "encoding")
        ET.SubElement(encoding, "software").text = "MusiAI"

        # Defaults (sizing for renderers)
        defaults = ET.SubElement(root, "defaults")
        scaling = ET.SubElement(defaults, "scaling")
        ET.SubElement(scaling, "millimeters").text = "7.05"
        ET.SubElement(scaling, "tenths").text = "40"

        # Part-List mit MIDI-Instrument
        part_list = ET.SubElement(root, "part-list")
        for i, part in enumerate(piece.parts):
            sp = ET.SubElement(part_list, "score-part", id=f"P{i+1}")
            ET.SubElement(sp, "part-name").text = part.name
            midi_inst = ET.SubElement(sp, "midi-instrument",
                                     id=f"P{i+1}-I1")
            ET.SubElement(midi_inst, "midi-channel").text = str(
                part.channel + 1)
            ET.SubElement(midi_inst, "midi-program").text = str(
                part.instrument + 1)

        # Parts
        for i, part in enumerate(piece.parts):
            self._write_part(root, piece, part, i)

        return root

    def _write_part(self, root, piece, part, part_idx):
        part_elem = ET.SubElement(root, "part", id=f"P{part_idx+1}")
        clef_sign, clef_line = self._detect_clef(part)

        for m_idx, measure in enumerate(part.measures):
            m_elem = ET.SubElement(
                part_elem, "measure", number=str(measure.number))

            # Attributes (erster Takt)
            if m_idx == 0:
                self._write_attributes(
                    m_elem, measure, clef_sign, clef_line)

            # Tempo als Direction mit Metronome
            if measure.tempo or (m_idx == 0 and piece.tempos):
                bpm = measure.tempo.bpm if measure.tempo else piece.initial_tempo
                self._write_tempo(m_elem, bpm)

            # Noten und Pausen
            self._write_measure_notes(m_elem, measure)

    def _write_attributes(self, m_elem, measure, clef_sign, clef_line):
        attrs = ET.SubElement(m_elem, "attributes")
        ET.SubElement(attrs, "divisions").text = str(self.DIVISIONS)
        key = ET.SubElement(attrs, "key")
        ET.SubElement(key, "fifths").text = "0"
        time = ET.SubElement(attrs, "time")
        ET.SubElement(time, "beats").text = str(
            measure.time_signature.numerator)
        ET.SubElement(time, "beat-type").text = str(
            measure.time_signature.denominator)
        clef = ET.SubElement(attrs, "clef")
        ET.SubElement(clef, "sign").text = clef_sign
        ET.SubElement(clef, "line").text = str(clef_line)

    def _write_tempo(self, m_elem, bpm):
        direction = ET.SubElement(m_elem, "direction",
                                  placement="above")
        dt = ET.SubElement(direction, "direction-type")
        metronome = ET.SubElement(dt, "metronome")
        ET.SubElement(metronome, "beat-unit").text = "quarter"
        ET.SubElement(metronome, "per-minute").text = str(int(bpm))
        ET.SubElement(direction, "sound", tempo=str(bpm))

    def _write_measure_notes(self, m_elem, measure):
        """Noten mit Akkord-Erkennung und Pausen schreiben."""
        dur_beats = measure.duration_beats
        notes = sorted(measure.notes, key=lambda n: n.start_beat)

        # Gruppiere Noten nach Startzeit
        current_beat = 0.0
        i = 0
        while i < len(notes):
            note = notes[i]

            # Pause vor dieser Note?
            gap = note.start_beat - current_beat
            if gap > 0.05:
                self._write_rest(m_elem, gap)

            # Sammle Akkord-Noten (gleicher start_beat)
            chord_notes = [note]
            while (i + 1 < len(notes) and
                   abs(notes[i + 1].start_beat - note.start_beat) < 0.01):
                i += 1
                chord_notes.append(notes[i])

            # Schreibe Noten (erste normal, Rest als <chord/>)
            for j, cn in enumerate(chord_notes):
                is_chord = j > 0
                self._write_note(m_elem, cn, is_chord)

            current_beat = note.start_beat + note.duration_beats
            i += 1

        # Pause am Ende des Taktes?
        gap = dur_beats - current_beat
        if gap > 0.05:
            self._write_rest(m_elem, gap)

    def _write_note(self, m_elem, note: Note, is_chord: bool = False):
        note_elem = ET.SubElement(m_elem, "note")

        # Chord-Markierung
        if is_chord:
            ET.SubElement(note_elem, "chord")

        # Pitch
        pitch = ET.SubElement(note_elem, "pitch")
        semitone = note.pitch % 12
        octave = (note.pitch // 12) - 1
        ET.SubElement(pitch, "step").text = SEMITONE_TO_STEP[semitone]
        ET.SubElement(pitch, "octave").text = str(octave)

        # Alter (Halbton + Cent-Offset für Mikrotöne)
        base_alter = SEMITONE_ALTER[semitone]
        cent_alter = note.expression.cent_offset / 100.0
        total_alter = base_alter + cent_alter
        if abs(total_alter) > 0.001:
            ET.SubElement(pitch, "alter").text = (
                f"{total_alter:.4f}".rstrip("0").rstrip("."))

        # Duration
        dur_ticks = int(note.duration_beats * self.DIVISIONS)
        ET.SubElement(note_elem, "duration").text = str(dur_ticks)

        # Type + Dot
        note_type, dotted = self._classify_duration(note.duration_beats)
        if note_type:
            ET.SubElement(note_elem, "type").text = note_type
            if dotted:
                ET.SubElement(note_elem, "dot")

        # Stem-Richtung
        if note_type not in ("whole", None):
            stem_dir = "up" if note.pitch >= 71 else "down"
            ET.SubElement(note_elem, "stem").text = stem_dir

        # Accidental (visuell)
        if base_alter != 0:
            acc_name = ACCIDENTAL_NAME.get(base_alter)
            if acc_name:
                ET.SubElement(note_elem, "accidental").text = acc_name

        # Notations (Glissando, Dynamics)
        notations = None
        if note.expression.glide_type == "curve":
            notations = notations or ET.SubElement(note_elem, "notations")
            ET.SubElement(notations, "glissando", type="start")

        # Velocity als Dynamics
        if note.expression.velocity != 80:
            ET.SubElement(note_elem, "sound",
                          dynamics=str(note.expression.velocity))

    def _write_rest(self, m_elem, beats: float):
        """Pause schreiben."""
        note_elem = ET.SubElement(m_elem, "note")
        ET.SubElement(note_elem, "rest")
        dur_ticks = int(beats * self.DIVISIONS)
        ET.SubElement(note_elem, "duration").text = str(dur_ticks)
        note_type, dotted = self._classify_duration(beats)
        if note_type:
            ET.SubElement(note_elem, "type").text = note_type
            if dotted:
                ET.SubElement(note_elem, "dot")

    @staticmethod
    def _classify_duration(beats: float) -> tuple[str | None, bool]:
        """Beats → (type_name, is_dotted)."""
        for threshold, name, dotted in DURATION_MAP:
            if beats >= threshold - 0.02:
                return name, dotted
        return "32nd", False

    @staticmethod
    def _detect_clef(part) -> tuple[str, int]:
        pitches = [n.pitch for m in part.measures for n in m.notes]
        if not pitches:
            return "G", 2
        median = sorted(pitches)[len(pitches) // 2]
        return ("F", 4) if median < 55 else ("G", 2)

    @staticmethod
    def _prettify(root: ET.Element) -> bytes:
        xml_str = ET.tostring(root, encoding="unicode")
        return minidom.parseString(xml_str).toprettyxml(
            indent="  ", encoding="UTF-8")
