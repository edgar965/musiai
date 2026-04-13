"""Music21Converter - Converts music21 Score objects to MidiSheet symbols."""

import logging
from musiai.ui.midi.WhiteNote import WhiteNote
from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
from musiai.ui.midi.BarSymbol import BarSymbol
from musiai.ui.midi.RestSymbol import RestSymbol
from musiai.ui.midi.ClefSymbol import TREBLE, BASS
from musiai.ui.midi import NoteDuration as ND
from musiai.ui.midi.AccidSymbol import SHARP, FLAT, NONE as ACCID_NONE

logger = logging.getLogger("musiai.ui.midi.Music21Converter")

# Ticks per beat used internally for symbol timing
TPB = 480


class Music21Converter:
    """Converts a music21 Score into lists of MidiSheet symbols per part."""

    def convert(self, file_path: str) -> list[dict]:
        """Parse a MIDI file and return per-part symbol data.

        Returns a list of dicts, one per part:
            {
                'symbols': [MusicSymbol, ...],
                'clef': TREBLE | BASS,
                'time_num': int,
                'time_den': int,
                'measure_len': int,   # in ticks
                'part_name': str,
            }
        """
        from musiai.music21.converter import parse as m21_parse

        score = m21_parse(file_path)
        results = []

        for part in score.parts:
            part_data = self._convert_part(part)
            if part_data is not None:
                results.append(part_data)

        return results

    # ------------------------------------------------------------------
    # Part conversion
    # ------------------------------------------------------------------
    def _convert_part(self, part) -> dict | None:
        """Convert one music21 Part to symbol data."""
        measures = list(part.getElementsByClass('Measure'))
        if not measures:
            return None

        clef = self._detect_clef(part)
        time_num, time_den = self._detect_time_sig(part)
        measure_len = int(time_num * (4 / time_den) * TPB)
        part_name = part.partName or "Track"

        chords = []
        for m_idx, m21_measure in enumerate(measures):
            abs_offset = m21_measure.offset  # in quarter-note beats
            m_chords = self._convert_measure(m21_measure, abs_offset, clef)
            chords.extend(m_chords)

        if not chords:
            return None

        last_tick = int(measures[-1].offset * TPB) + measure_len
        symbols = self._add_bars(chords, measure_len, last_tick)
        symbols = self._add_rests(symbols, time_num, time_den)

        return {
            'symbols': symbols,
            'clef': clef,
            'time_num': time_num,
            'time_den': time_den,
            'measure_len': measure_len,
            'part_name': part_name,
        }

    # ------------------------------------------------------------------
    # Measure conversion
    # ------------------------------------------------------------------
    def _convert_measure(self, m21_measure, abs_offset, clef) -> list:
        """Extract ChordSymbols from a single music21 Measure."""
        chords = []
        # Collect all notes and chords (recurse handles Voices)
        elements = list(m21_measure.recurse().notesAndRests)

        # Group notes/chords by their absolute tick offset
        time_groups: dict[int, list] = {}
        for el in elements:
            if self._is_rest(el):
                continue  # rests handled later by _add_rests
            offset_beats = abs_offset + el.offset
            tick = int(offset_beats * TPB)
            if tick not in time_groups:
                time_groups[tick] = []
            time_groups[tick].append(el)

        for tick in sorted(time_groups):
            group = time_groups[tick]
            note_data_list = []
            max_end = tick

            for el in group:
                dur_beats = float(el.duration.quarterLength)
                end_tick = tick + int(dur_beats * TPB)
                max_end = max(max_end, end_tick)

                if self._is_chord(el):
                    for p in el.pitches:
                        nd = self._pitch_to_notedata(p, dur_beats)
                        if nd is not None:
                            note_data_list.append(nd)
                elif self._is_note(el):
                    nd = self._pitch_to_notedata(el.pitch, dur_beats)
                    if nd is not None:
                        note_data_list.append(nd)

            if note_data_list:
                # Sort by pitch, fix left_side for adjacent notes
                note_data_list.sort(key=lambda nd: nd.number)
                self._fix_left_sides(note_data_list)
                chord = ChordSymbol(note_data_list, clef, tick, max_end)
                chords.append(chord)

        return chords

    # ------------------------------------------------------------------
    # Pitch / NoteData conversion
    # ------------------------------------------------------------------
    @staticmethod
    def _pitch_to_notedata(m21_pitch, dur_beats: float) -> NoteData | None:
        """Convert a music21 Pitch to a NoteData."""
        midi = m21_pitch.midi
        if midi < 0 or midi > 127:
            return None

        wn = WhiteNote.from_midi(midi)
        dur = ND.from_beats(dur_beats)

        # Determine accidental from music21
        accid = ACCID_NONE
        if m21_pitch.accidental is not None:
            alter = m21_pitch.accidental.alter
            if alter > 0:
                accid = SHARP
            elif alter < 0:
                accid = FLAT

        return NoteData(midi, wn, dur, True, accid)

    @staticmethod
    def _fix_left_sides(note_data_list: list[NoteData]):
        """Alternate left_side for notes a second apart."""
        for i in range(1, len(note_data_list)):
            prev_wn = note_data_list[i - 1].whitenote
            cur_wn = note_data_list[i].whitenote
            if abs(cur_wn.dist(prev_wn)) == 1:
                note_data_list[i].left_side = not note_data_list[i - 1].left_side

    # ------------------------------------------------------------------
    # Detect clef / time signature
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_clef(part) -> int:
        """Detect clef from music21 Part."""
        from musiai.music21 import clef as m21_clef
        clefs = list(part.recurse().getElementsByClass('Clef'))
        if clefs:
            if isinstance(clefs[0], m21_clef.BassClef):
                return BASS
        return TREBLE

    @staticmethod
    def _detect_time_sig(part) -> tuple[int, int]:
        """Extract time signature from music21 Part."""
        ts_list = list(part.recurse().getElementsByClass('TimeSignature'))
        if ts_list:
            ts = ts_list[0]
            return ts.numerator, ts.denominator
        return 4, 4

    # ------------------------------------------------------------------
    # Type checks (avoid isinstance with music21 classes at module level)
    # ------------------------------------------------------------------
    @staticmethod
    def _is_note(el) -> bool:
        return type(el).__name__ == 'Note'

    @staticmethod
    def _is_chord(el) -> bool:
        return type(el).__name__ == 'Chord'

    @staticmethod
    def _is_rest(el) -> bool:
        return type(el).__name__ == 'Rest'

    # ------------------------------------------------------------------
    # AddBars - insert BarSymbols at measure boundaries
    # ------------------------------------------------------------------
    @staticmethod
    def _add_bars(chords, measure_len, last_tick) -> list:
        """Add bar symbols at each measure boundary."""
        symbols = []
        measure_time = 0
        i = 0
        while i < len(chords):
            if measure_len > 0 and measure_time <= chords[i].start_time:
                symbols.append(BarSymbol(measure_time))
                measure_time += measure_len
            else:
                symbols.append(chords[i])
                i += 1

        if measure_len > 0:
            while measure_time < last_tick:
                symbols.append(BarSymbol(measure_time))
                measure_time += measure_len
            symbols.append(BarSymbol(measure_time))

        return symbols

    # ------------------------------------------------------------------
    # AddRests - fill gaps between notes
    # ------------------------------------------------------------------
    def _add_rests(self, symbols, time_num, time_den) -> list:
        """Add rest symbols between notes."""
        quarter = TPB
        prev_time = 0
        result = []
        for sym in symbols:
            start = sym.start_time
            rests = self._get_rests(prev_time, start, quarter)
            if rests:
                result.extend(rests)
            result.append(sym)
            if isinstance(sym, ChordSymbol):
                prev_time = max(sym.end_time, prev_time)
            else:
                prev_time = max(start, prev_time)
        return result

    @staticmethod
    def _get_rests(start, end, quarter) -> list:
        """Return rest symbols to fill the gap between start and end."""
        diff = end - start
        if diff <= 0:
            return []

        dur = ND.from_beats(diff / quarter)
        if dur is None:
            return []

        if dur in (ND.WHOLE, ND.HALF, ND.QUARTER, ND.EIGHTH):
            return [RestSymbol(start, dur)]
        elif dur == ND.DOTTED_HALF:
            return [RestSymbol(start, ND.HALF),
                    RestSymbol(start + quarter * 2, ND.QUARTER)]
        elif dur == ND.DOTTED_QUARTER:
            return [RestSymbol(start, ND.QUARTER),
                    RestSymbol(start + quarter, ND.EIGHTH)]
        elif dur == ND.DOTTED_EIGHTH:
            return [RestSymbol(start, ND.EIGHTH),
                    RestSymbol(start + quarter // 2, ND.SIXTEENTH)]
        return []
