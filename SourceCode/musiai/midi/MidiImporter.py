"""MIDI-Datei Import via music21."""

import logging
from pathlib import Path
from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Measure import Measure
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo

logger = logging.getLogger("musiai.midi.importer")


class MidiImporter:
    """Importiert MIDI-Dateien und konvertiert sie ins interne Model."""

    def import_file(self, path: str) -> Piece:
        """MIDI-Datei laden und als Piece zurückgeben."""
        import os
        path = os.path.abspath(path)
        logger.info(f"Importiere MIDI: {path}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")

        import music21
        score = music21.converter.parse(path)
        title = Path(path).stem
        piece = Piece(title=title)

        # Tempos extrahieren
        piece.tempos = self._extract_tempos(score)

        # Parts extrahieren
        parts = score.parts if hasattr(score, 'parts') else [score]
        for i, m21_part in enumerate(parts):
            part = self._convert_part(m21_part, i)
            piece.add_part(part)
            logger.info(f"  Part '{part.name}': {len(part.measures)} Takte, "
                       f"{len(part.get_all_notes())} Noten")

        logger.info(f"Import fertig: '{piece.title}', {piece.total_measures} Takte")
        return piece

    def _extract_tempos(self, score) -> list[Tempo]:
        import music21
        tempos = []
        for mm in score.flatten().getElementsByClass(music21.tempo.MetronomeMark):
            tempos.append(Tempo(bpm=mm.number, beat_position=mm.offset))
        if not tempos:
            tempos.append(Tempo(120.0, 0.0))
        return tempos

    def _convert_part(self, m21_part, index: int) -> Part:
        import music21
        name = m21_part.partName or f"Part {index + 1}"
        part = Part(name=name, channel=index)

        for m21_measure in m21_part.getElementsByClass(music21.stream.Measure):
            measure = self._convert_measure(m21_measure)
            part.add_measure(measure)

        if not part.measures:
            part.add_measure(self._flat_to_measure(m21_part))

        return part

    def _convert_measure(self, m21_measure) -> Measure:
        import music21
        measure = Measure(number=m21_measure.number)

        ts = m21_measure.getTimeSignatures()
        if ts:
            measure.time_signature = TimeSignature(ts[0].numerator, ts[0].denominator)

        tempos = m21_measure.getElementsByClass(music21.tempo.MetronomeMark)
        if tempos:
            measure.tempo = Tempo(tempos[0].number, tempos[0].offset)

        for element in m21_measure.flatten().notesAndRests:
            if isinstance(element, music21.note.Note):
                note = self._convert_note(element)
                measure.add_note(note)
            elif isinstance(element, music21.chord.Chord):
                for pitch in element.pitches:
                    note = Note(
                        pitch=pitch.midi,
                        start_beat=element.offset,
                        duration_beats=element.quarterLength,
                        expression=Expression(velocity=element.volume.velocity or 80),
                    )
                    measure.add_note(note)

        return measure

    def _convert_note(self, m21_note) -> Note:
        velocity = m21_note.volume.velocity if m21_note.volume.velocity else 80
        cents = 0.0
        if m21_note.pitch.microtone and m21_note.pitch.microtone.cents:
            cents = m21_note.pitch.microtone.cents

        return Note(
            pitch=m21_note.pitch.midi,
            start_beat=m21_note.offset,
            duration_beats=m21_note.quarterLength,
            expression=Expression(velocity=int(velocity), cent_offset=cents),
        )

    def _flat_to_measure(self, m21_part) -> Measure:
        import music21
        measure = Measure(number=1)
        for element in m21_part.flatten().notesAndRests:
            if isinstance(element, music21.note.Note):
                measure.add_note(self._convert_note(element))
        return measure
