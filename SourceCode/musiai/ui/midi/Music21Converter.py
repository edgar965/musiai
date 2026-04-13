"""Music21Converter - Converts music21 Score objects to MidiSheet symbols."""

import logging
from musiai.ui.midi.WhiteNote import WhiteNote
from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
from musiai.ui.midi.BarSymbol import BarSymbol
from musiai.ui.midi.RestSymbol import RestSymbol
from musiai.ui.midi.ClefSymbol import TREBLE, BASS
from musiai.ui.midi import NoteDuration as ND
from musiai.ui.midi.AccidSymbol import AccidSymbol, SHARP, FLAT, NONE as ACCID_NONE

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
                'key_sharps': int,
                'key_accids': [AccidSymbol, ...],
                'tempo_bpm': float | None,
                'part_name': str,
            }
        """
        from musiai.music21.converter import parse as m21_parse

        score = m21_parse(file_path)
        results = []

        # Extract tempo from score level
        tempo_bpm = self._detect_tempo(score)

        for part in score.parts:
            part_data = self._convert_part(part)
            if part_data is not None:
                part_data['tempo_bpm'] = tempo_bpm
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
        key_sharps = self._detect_key_sig(part)
        key_accids = self._create_key_accid_symbols(key_sharps, clef)
        # Part-Name: music21 liefert manchmal None
        part_name = part.partName
        if not part_name or part_name.strip() == "":
            # Fallback basierend auf Schlüssel
            if clef == BASS:
                part_name = "Bass"
            else:
                part_name = "Treble"

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
            'key_sharps': key_sharps,
            'key_accids': key_accids,
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

            # Collect pitches and total beat duration from all elements
            pitches = []
            dur_beats = 0.0
            for el in group:
                el_dur = float(el.duration.quarterLength)
                dur_beats = max(dur_beats, el_dur)
                if self._is_chord(el):
                    pitches.extend(el.pitches)
                elif self._is_note(el):
                    pitches.append(el.pitch)

            if not pitches:
                continue

            # Split complex durations into tied standard parts
            beat_parts = ND.split_complex(dur_beats)

            current_tick = tick
            split_chords = []
            for part_beats in beat_parts:
                part_ticks = int(part_beats * TPB)
                end_tick = current_tick + part_ticks

                note_data_list = []
                for p in pitches:
                    nd = self._pitch_to_notedata(p, part_beats)
                    if nd is not None:
                        note_data_list.append(nd)

                if note_data_list:
                    note_data_list.sort(key=lambda nd: nd.number)
                    self._fix_left_sides(note_data_list)
                    chord = ChordSymbol(
                        note_data_list, clef, current_tick, end_tick)
                    split_chords.append(chord)

                current_tick = end_tick

            # Mark split parts as tied (except the last)
            for i in range(len(split_chords) - 1):
                split_chords[i].tied_to_next = True

            # Detect ties from music21 (original MIDI ties)
            for el in group:
                if hasattr(el, 'tie') and el.tie and el.tie.type in ('start', 'continue'):
                    if split_chords:
                        split_chords[-1].tied_to_next = True

            chords.extend(split_chords)

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

    @staticmethod
    def _detect_key_sig(part) -> int:
        """Extract key signature sharps count (negative = flats)."""
        ks_list = list(part.recurse().getElementsByClass('KeySignature'))
        if ks_list:
            return ks_list[0].sharps
        return 0

    @staticmethod
    def _detect_tempo(score) -> float | None:
        """Extract tempo (BPM) from the score."""
        tempos = list(score.recurse().getElementsByClass('MetronomeMark'))
        if tempos:
            return tempos[0].number
        return None

    @staticmethod
    def _create_key_accid_symbols(key_sharps: int, clef: int) -> list:
        """Create AccidSymbol objects for the key signature.

        key_sharps > 0: sharps in order F C G D A E B
        key_sharps < 0: flats  in order B E A D G C F
        """
        # WhiteNote letters: A=0, B=1, C=2, D=3, E=4, F=5, G=6
        # Treble clef sharp order: F5 C5 G5 D5 A4 E5 B4
        # Treble clef flat order:  B4 E5 A4 D5 G4 C5 F4
        # Bass clef: same letters, 2 octaves lower
        if clef == TREBLE:
            sharp_notes = [
                WhiteNote(5, 5),  # F5
                WhiteNote(2, 5),  # C5
                WhiteNote(6, 5),  # G5
                WhiteNote(3, 5),  # D5
                WhiteNote(0, 5),  # A5 (drawn on A4 line visually)
                WhiteNote(4, 5),  # E5
                WhiteNote(1, 5),  # B5 (drawn on B4 line visually)
            ]
            flat_notes = [
                WhiteNote(1, 4),  # B4
                WhiteNote(4, 5),  # E5
                WhiteNote(0, 4),  # A4
                WhiteNote(3, 5),  # D5
                WhiteNote(6, 4),  # G4
                WhiteNote(2, 5),  # C5
                WhiteNote(5, 4),  # F4
            ]
        else:
            sharp_notes = [
                WhiteNote(5, 3),  # F3
                WhiteNote(2, 3),  # C3
                WhiteNote(6, 3),  # G3
                WhiteNote(3, 3),  # D3
                WhiteNote(0, 3),  # A3
                WhiteNote(4, 3),  # E3
                WhiteNote(1, 3),  # B3
            ]
            flat_notes = [
                WhiteNote(1, 2),  # B2
                WhiteNote(4, 3),  # E3
                WhiteNote(0, 2),  # A2
                WhiteNote(3, 3),  # D3
                WhiteNote(6, 2),  # G2
                WhiteNote(2, 3),  # C3
                WhiteNote(5, 2),  # F2
            ]

        accids = []
        if key_sharps > 0:
            for i in range(min(key_sharps, 7)):
                accids.append(AccidSymbol(SHARP, sharp_notes[i], clef))
        elif key_sharps < 0:
            for i in range(min(-key_sharps, 7)):
                accids.append(AccidSymbol(FLAT, flat_notes[i], clef))
        return accids

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

        beats = diff / quarter
        beat_parts = ND.split_complex(beats)

        rests = []
        current = start
        for part_beats in beat_parts:
            dur = ND.from_beats(part_beats)
            rests.append(RestSymbol(current, dur))
            current += int(part_beats * quarter)
        return rests
