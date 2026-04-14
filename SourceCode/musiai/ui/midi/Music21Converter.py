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

        logger.info(f"Konvertiere: {file_path}")
        score = m21_parse(file_path)
        results = []

        # Extract tempo from score level
        tempo_bpm = self._detect_tempo(score)

        for part in score.parts:
            part_data = self._convert_part(part)
            if part_data is not None:
                part_data['tempo_bpm'] = tempo_bpm
                results.append(part_data)

        # Synchronize clef changes: if one part changes clef,
        # other parts get a reminder clef symbol at the same tick
        self._sync_clef_changes(results)

        logger.info(f"Konvertierung abgeschlossen: {len(results)} Parts, "
                    f"Tempo={tempo_bpm}")
        for i, pd in enumerate(results):
            logger.debug(f"  Part {i}: {pd.get('part_name', '?')}, "
                         f"{len(pd['symbols'])} Symbole, "
                         f"Taktart={pd.get('time_num')}/{pd.get('time_den')}")
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
        current_clef = clef
        for m_idx, m21_measure in enumerate(measures):
            abs_offset = m21_measure.offset  # in quarter-note beats
            # Check for mid-piece clef changes
            clef_changed = False
            measure_clefs = list(m21_measure.getElementsByClass('Clef'))
            if measure_clefs:
                from musiai.music21 import clef as m21_clef
                new_clef = BASS if isinstance(
                    measure_clefs[-1], m21_clef.BassClef) else TREBLE
                if new_clef != current_clef:
                    from musiai.ui.midi.ClefSymbol import ClefSymbol
                    tick = int(abs_offset * TPB)
                    chords.append(ClefSymbol(new_clef, tick, small=True))
                    # Add key signature after clef change
                    accids = self._create_key_accid_symbols(
                        key_sharps, new_clef)
                    for ac in accids:
                        ac._start_time = tick
                        chords.append(ac)
                    current_clef = new_clef
                    clef_changed = True
            m_chords = self._convert_measure(
                m21_measure, abs_offset, current_clef, key_sharps)
            chords.extend(m_chords)

        if not chords:
            return None

        # Find last measure with actual notes (skip trailing empty measures)
        last_measure = measures[-1]
        for m in reversed(measures):
            elems = list(m.recurse().notesAndRests)
            has_notes = any(not self._is_rest(e) for e in elems)
            if has_notes:
                last_measure = m
                break
        last_tick = int(last_measure.offset * TPB) + measure_len
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
    def _convert_measure(self, m21_measure, abs_offset, clef,
                         key_sharps=0) -> list:
        """Extract ChordSymbols from a single music21 Measure."""
        chords = []
        # Collect all notes and chords (recurse handles Voices)
        elements = list(m21_measure.recurse().notesAndRests)

        # Separate grace notes from regular notes, then group by tick
        regular_elements = []
        grace_groups: dict[int, list] = {}  # main_tick → [grace elements]
        for el in elements:
            if self._is_rest(el):
                continue
            is_grace = (float(el.duration.quarterLength) == 0)
            if is_grace:
                main_tick = int((abs_offset + el.offset) * TPB)
                if main_tick not in grace_groups:
                    grace_groups[main_tick] = []
                grace_groups[main_tick].append(el)
            else:
                regular_elements.append(el)

        # Group regular notes by tick
        time_groups: dict[int, list] = {}
        for el in regular_elements:
            tick = int((abs_offset + el.offset) * TPB)
            if tick not in time_groups:
                time_groups[tick] = []
            time_groups[tick].append(el)

        # Insert grace notes just before their main tick (within same measure)
        measure_start_tick = int(abs_offset * TPB)
        for main_tick, graces in grace_groups.items():
            n_graces = len(graces)
            # Make room: shift main note forward if grace lands on same tick
            if main_tick in time_groups and main_tick == measure_start_tick:
                main_els = time_groups.pop(main_tick)
                time_groups[main_tick + n_graces] = main_els
            for i, gel in enumerate(graces):
                g_tick = max(measure_start_tick, main_tick - n_graces) + i
                while g_tick in time_groups:
                    g_tick += 1
                time_groups[g_tick] = [gel]

        for tick in sorted(time_groups):
            group = time_groups[tick]

            # Collect pitches and total beat duration from all elements
            pitches = []  # list of (pitch, velocity)
            dur_beats = 0.0
            for el in group:
                el_dur = float(el.duration.quarterLength)
                if el_dur == 0:
                    # Grace note: render as 32nd note (0.125 beats)
                    el_dur = 0.125
                dur_beats = max(dur_beats, el_dur)
                vel_obj = getattr(el, 'volume', None)
                vel = int(vel_obj.velocity) if vel_obj and vel_obj.velocity else 80
                if self._is_chord(el):
                    for p in el.pitches:
                        pitches.append((p, vel))
                elif self._is_note(el):
                    pitches.append((el.pitch, vel))

            # Deduplicate same MIDI pitch (multi-voice same notes)
            seen = {}
            unique_pitches = []
            for p, vel in pitches:
                midi = p.midi
                if midi not in seen:
                    seen[midi] = len(unique_pitches)
                    unique_pitches.append((p, vel))
            pitches = unique_pitches

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
                for p, vel in pitches:
                    nd = self._pitch_to_notedata(
                        p, part_beats, vel, key_sharps)
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
    def _pitch_to_notedata(m21_pitch, dur_beats: float,
                           velocity: int = 80,
                           key_sharps: int = 0) -> NoteData | None:
        """Convert a music21 Pitch to a NoteData."""
        midi = m21_pitch.midi
        if midi < 0 or midi > 127:
            return None

        wn = WhiteNote.from_midi_in_key(midi, key_sharps)
        dur = ND.from_beats(dur_beats)

        # Key signature: which notes are already sharp/flat
        # Sharps order: F C G D A E B, Flats order: B E A D G C F
        sharp_letters = ['F', 'C', 'G', 'D', 'A', 'E', 'B']
        flat_letters = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
        key_accids_set = set()
        if key_sharps > 0:
            for i in range(min(key_sharps, 7)):
                key_accids_set.add((sharp_letters[i], 'sharp'))
        elif key_sharps < 0:
            for i in range(min(-key_sharps, 7)):
                key_accids_set.add((flat_letters[i], 'flat'))

        # Determine accidental — only show if NOT implied by key sig
        accid = ACCID_NONE
        if m21_pitch.accidental is not None:
            alter = m21_pitch.accidental.alter
            step = m21_pitch.step  # 'C', 'D', etc.
            if alter > 0:
                if (step, 'sharp') not in key_accids_set:
                    accid = SHARP
            elif alter < 0:
                if (step, 'flat') not in key_accids_set:
                    accid = FLAT

        return NoteData(midi, wn, dur, True, accid, velocity)

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
        # Letters: C=0, D=1, E=2, F=3, G=4, A=5, B=6
        # Standard octaves: C4=60, A4=69
        # Treble clef sharp order: F5 C5 G5 D5 A4 E5 B4
        # Treble clef flat order:  B4 E5 A4 D5 G4 C5 F4
        # Bass clef: same letters, 2 octaves lower
        from musiai.ui.midi.WhiteNote import C, D, E, F, G, A, B
        if clef == TREBLE:
            sharp_notes = [
                WhiteNote(F, 5),  # F5
                WhiteNote(C, 5),  # C5
                WhiteNote(G, 5),  # G5
                WhiteNote(D, 5),  # D5
                WhiteNote(A, 4),  # A4
                WhiteNote(E, 5),  # E5
                WhiteNote(B, 4),  # B4
            ]
            flat_notes = [
                WhiteNote(B, 4),  # B4
                WhiteNote(E, 5),  # E5
                WhiteNote(A, 4),  # A4
                WhiteNote(D, 5),  # D5
                WhiteNote(G, 4),  # G4
                WhiteNote(C, 5),  # C5
                WhiteNote(F, 4),  # F4
            ]
        else:
            sharp_notes = [
                WhiteNote(F, 3),  # F3
                WhiteNote(C, 3),  # C3
                WhiteNote(G, 3),  # G3
                WhiteNote(D, 3),  # D3
                WhiteNote(A, 2),  # A2
                WhiteNote(E, 3),  # E3
                WhiteNote(B, 2),  # B2
            ]
            flat_notes = [
                WhiteNote(B, 2),  # B2
                WhiteNote(E, 3),  # E3
                WhiteNote(A, 2),  # A2
                WhiteNote(D, 3),  # D3
                WhiteNote(G, 2),  # G2
                WhiteNote(C, 3),  # C3
                WhiteNote(F, 2),  # F2
            ]

        accids = []
        if key_sharps > 0:
            for i in range(min(key_sharps, 7)):
                accids.append(AccidSymbol(SHARP, sharp_notes[i], clef))
        elif key_sharps < 0:
            for i in range(min(-key_sharps, 7)):
                accids.append(AccidSymbol(FLAT, flat_notes[i], clef))
        return accids

    def _sync_clef_changes(self, results: list[dict]) -> None:
        """When one part has a clef change, add reminder clefs to other parts.

        E.g. if Part 0 changes from Bass back to Treble at tick X,
        Part 1 gets a Bass ClefSymbol + key signature at tick X.
        """
        if len(results) < 2:
            return
        from musiai.ui.midi.ClefSymbol import ClefSymbol

        # Collect all clef change ticks from all parts
        clef_ticks = set()
        for pd in results:
            for sym in pd['symbols']:
                if isinstance(sym, ClefSymbol) and sym.small:
                    clef_ticks.add(sym.start_time)

        if not clef_ticks:
            return

        # For each part, add reminder clefs + key sig at missing ticks
        for pd in results:
            existing_ticks = {
                sym.start_time for sym in pd['symbols']
                if isinstance(sym, ClefSymbol) and sym.small
            }
            part_clef = pd['clef']
            key_sharps = pd.get('key_sharps', 0)
            for tick in sorted(clef_ticks):
                if tick not in existing_ticks:
                    pd['symbols'].append(
                        ClefSymbol(part_clef, tick, small=True))
                    # Add key signature accidentals
                    accids = self._create_key_accid_symbols(
                        key_sharps, part_clef)
                    for ac in accids:
                        ac._start_time = tick
                        pd['symbols'].append(ac)
            # Re-sort symbols by start_time
            pd['symbols'].sort(key=lambda s: s.start_time)

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
