"""MidiSheetRenderer - Hauptklasse fuer MIDI-Notenblatt-Rendering.

Portiert von SheetControl.cs: CreateAllMusicalSymbols, AddBars, AddRests,
AlignSymbols, CreateStaffs, CreateAllBeamedChords.
"""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem
from PySide6.QtGui import QColor, QPen, QFont, QBrush, QPixmap, QPainter
from PySide6.QtCore import Qt
from musiai.model.Piece import Piece
from musiai.ui.midi.WhiteNote import WhiteNote
from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
from musiai.ui.midi.BarSymbol import BarSymbol
from musiai.ui.midi.BlankSymbol import BlankSymbol
from musiai.ui.midi.RestSymbol import RestSymbol
from musiai.ui.midi.ClefSymbol import ClefSymbol, TREBLE, BASS
from musiai.ui.midi.Staff import Staff
from musiai.ui.midi.SymbolWidths import SymbolWidths
from musiai.ui.midi.SheetConfig import SheetConfig
from musiai.ui.midi import NoteDuration as ND
from musiai.ui.midi.AccidSymbol import SHARP, FLAT, NONE as ACCID_NONE
from musiai.notation.ClefHelper import ClefHelper

logger = logging.getLogger("musiai.ui.midi.MidiSheetRenderer")


class MidiSheetRenderer:
    """Rendert ein Piece als klassisches Notenblatt."""

    def __init__(self, config: SheetConfig = None, use_bravura: bool = False,
                 color_mode: bool = False):
        self.config = config or SheetConfig.large()
        self.use_bravura = use_bravura
        self.color_mode = color_mode
        if use_bravura:
            from musiai.ui.midi.BravuraGlyphs import ensure_font
            ensure_font()

    def render_from_file(self, file_path: str, scene: QGraphicsScene,
                         system_width: float = 1100,
                         interleave: bool = True) -> None:
        """Render a MIDI file using music21 as parser.

        Args:
            interleave: If True, Treble+Bass staves are shown together
                       per system row (like a piano score). If False,
                       each track is rendered separately.
        """
        from musiai.ui.midi.Music21Converter import Music21Converter

        self.config.page_width = int(system_width) - 120
        SheetConfig.PageWidth = self.config.page_width
        cfg = self.config.to_dict()
        cfg["use_bravura"] = self.use_bravura
        cfg["color_mode"] = self.color_mode
        y_offset = 60

        logger.info(f"render_from_file gestartet: {file_path}")
        converter = Music21Converter()
        try:
            parts_data = converter.convert(file_path)
        except Exception as e:
            logger.error(f"music21 parse failed: {e}", exc_info=True)
            return

        if not parts_data:
            return

        # Sync model expression data into converter symbols
        piece = getattr(scene, 'piece', None)
        if piece:
            self._sync_model_velocity(parts_data, piece)

        track_symbols = [pd['symbols'] for pd in parts_data]
        total_symbols = sum(len(s) for s in track_symbols)
        logger.debug(f"render_from_file: {len(parts_data)} Parts, "
                     f"{total_symbols} Symbole gesamt")

        # Align symbols across tracks
        widths = SymbolWidths(track_symbols)
        self._align_symbols(track_symbols, widths)

        # Create beams before creating staffs
        if parts_data:
            pd0 = parts_data[0]
            time_num = pd0.get('time_num', 4)
            time_den = pd0.get('time_den', 4)
            quarter = 480  # TPB from Music21Converter
            measure_len = pd0.get('measure_len', quarter * 4)
            self._create_all_beamed_chords(
                track_symbols, time_num, time_den, quarter, measure_len)

        # Create staffs per track
        all_staffs = []  # list of (track_idx, list[Staff])
        for track_idx, symbols in enumerate(track_symbols):
            pd = parts_data[track_idx]
            staffs = self._create_staffs_for_track(
                symbols, pd['measure_len'],
                track_idx, len(track_symbols),
                key_accids=pd.get('key_accids', []),
                time_num=pd.get('time_num', 0),
                time_den=pd.get('time_den', 0))
            for s in staffs:
                s.calculate_height()
            all_staffs.append((track_idx, staffs))

        # Draw tempo marking above first system
        tempo_bpm = parts_data[0].get('tempo_bpm')
        if tempo_bpm is not None:
            self._draw_tempo_marking(scene, tempo_bpm, y_offset)

        if interleave and len(all_staffs) > 1:
            y_offset = self._render_interleaved(
                scene, all_staffs, parts_data, cfg, y_offset, system_width)
        else:
            y_offset = self._render_sequential(
                scene, all_staffs, parts_data, cfg, y_offset, system_width)

        # Draw audio waveforms if piece has audio parts
        piece = getattr(scene, 'piece', None)
        if piece:
            for part in piece.parts:
                if part.audio_track and part.audio_track.blocks:
                    self._draw_part_label(
                        scene, part.name, piece.parts.index(part),
                        4, y_offset, font_size=10)
                    self._draw_waveform(
                        scene, part, y_offset, system_width,
                        piece.initial_tempo)
                    y_offset += 80

        scene.setSceneRect(0, 0, system_width + 60, y_offset + 40)

        # Pass staff layout to scene for playhead positioning
        self._store_staff_layout(scene)

        # Draw tempo change and deviation markers
        y_offsets = getattr(self, '_first_track_y_offsets', [])
        self._draw_tempo_markers(scene, all_staffs, parts_data, y_offsets)

        logger.info(f"Rendered {len(parts_data)} parts from file via music21")

    def _render_interleaved(self, scene, all_staffs, parts_data, cfg,
                            y_offset, system_width):
        """Treble+Bass zusammen pro Zeile (Partitur-Ansicht)."""
        from PySide6.QtGui import QPen
        max_rows = max(len(staffs) for _, staffs in all_staffs)
        n_tracks = len(all_staffs)

        # Taktnummern nur beim ersten Track pro System anzeigen
        for track_idx, staffs in all_staffs:
            for s in staffs:
                s.show_measures = (track_idx == all_staffs[0][0])

        # Track staff y-positions for playhead map
        self._staff_y_positions = []
        self._first_track_y_offsets = []  # y per staff row (first track)

        for row in range(max_rows):
            system_top = y_offset
            first_track_staff = None

            # Alle Tracks dieser Zeile direkt untereinander
            for i, (track_idx, staffs) in enumerate(all_staffs):
                if row >= len(staffs):
                    continue
                staff = staffs[row]

                # Part-Label links neben dem Staff (jede Zeile)
                pd = parts_data[track_idx]
                self._draw_part_label(
                    scene, pd['part_name'], track_idx,
                    4, y_offset + 15, font_size=8)

                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                item.setData(0, "staff_pixmap")
                item.setData(1, staff)
                item.setData(2, track_idx)

                # Remember first track's staff for x-lookup
                if track_idx == all_staffs[0][0]:
                    first_track_staff = staff

                y_offset += staff.height - 8  # Eng zusammen

            # Store full system row extent (all voices)
            if first_track_staff is not None:
                self._staff_y_positions.append(
                    (first_track_staff, system_top, y_offset))
                self._first_track_y_offsets.append(system_top)

            # Klammer links (verbindet die Staves im System)
            if n_tracks > 1:
                pen = QPen(QColor(30, 30, 50), 2.5)
                bracket = scene.addLine(
                    96, system_top + 25, 96, y_offset - 5, pen)
                bracket.setZValue(5)
                # Oberer/unterer Haken
                scene.addLine(96, system_top + 25, 100, system_top + 25, pen)
                scene.addLine(96, y_offset - 5, 100, y_offset - 5, pen)

            y_offset += 35  # Abstand zum nächsten System

        return y_offset

    def _render_sequential(self, scene, all_staffs, parts_data, cfg,
                           y_offset, system_width):
        """Jeder Track separat (klassische Ansicht)."""
        self._staff_y_positions = []
        first_track = True
        for track_idx, staffs in all_staffs:
            pd = parts_data[track_idx]

            self._draw_part_label(
                scene, pd['part_name'], track_idx,
                4, y_offset, font_size=10)

            for staff in staffs:
                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                item.setData(0, "staff_pixmap")
                item.setData(1, staff)
                item.setData(2, track_idx)
                if first_track:
                    self._staff_y_positions.append(
                        (staff, y_offset, y_offset + staff.height))
                y_offset += staff.height + 15
            y_offset += 20
            first_track = False

        return y_offset

    def render(self, piece: Piece, scene: QGraphicsScene,
               system_width: float = 1100,
               interleave: bool = False) -> None:
        if not piece or not piece.parts:
            return
        logger.info(f"render gestartet: '{piece.title}', "
                    f"{len(piece.parts)} Parts")

        self.config.page_width = int(system_width) - 120
        SheetConfig.PageWidth = self.config.page_width
        cfg = self.config.to_dict()
        cfg["use_bravura"] = self.use_bravura
        cfg["color_mode"] = self.color_mode
        y_offset = 60

        # Collect tracks
        track_symbols = []
        track_clefs = []
        tpb = 480  # ticks per beat

        for part in piece.parts:
            if part.audio_track and part.audio_track.blocks:
                continue

            all_notes = [n for m in part.measures for n in m.notes]
            clef_str = ClefHelper.detect_clef(all_notes)
            clef = TREBLE if clef_str == "treble" else BASS

            symbols = self._create_symbols_for_part(part, clef, tpb)
            track_symbols.append(symbols)
            track_clefs.append(clef)

        if not track_symbols:
            return

        # Align symbols across tracks
        widths = SymbolWidths(track_symbols)
        self._align_symbols(track_symbols, widths)

        # Determine time signature info
        measure_len = self._get_measure_length(piece, tpb)
        time_num, time_den = self._get_time_sig(piece)
        quarter = tpb  # quarter note = tpb ticks

        # Create beams
        self._create_all_beamed_chords(
            track_symbols, time_num, time_den, quarter, measure_len)
        # Create staffs per track
        all_staffs_list = []
        for track_idx, symbols in enumerate(track_symbols):
            staffs = self._create_staffs_for_track(
                symbols, measure_len, track_idx, len(track_symbols))
            all_staffs_list.append((track_idx, staffs))
            for s in staffs:
                s.calculate_height()

        # Build parts_data for interleaved renderer
        parts_data = []
        for track_idx, symbols in enumerate(track_symbols):
            part = self._get_part(piece, track_idx)
            parts_data.append({
                'part_name': part.name if part else f"Track {track_idx}",
            })

        if interleave and len(all_staffs_list) > 1:
            y_offset = self._render_interleaved(
                scene, all_staffs_list, parts_data, cfg, y_offset,
                system_width)
        else:
            y_offset = self._render_sequential(
                scene, all_staffs_list, parts_data, cfg, y_offset,
                system_width)

        # Draw audio waveforms for audio parts
        for part in piece.parts:
            if part.audio_track and part.audio_track.blocks:
                self._draw_part_label(
                    scene, part.name, piece.parts.index(part),
                    4, y_offset, font_size=10)
                self._draw_waveform(
                    scene, part, y_offset, system_width,
                    piece.initial_tempo)
                y_offset += 80

        scene.setSceneRect(0, 0, system_width + 60, y_offset + 40)
        self._store_staff_layout(scene)

        # Draw tempo markers
        y_offsets = getattr(self, '_first_track_y_offsets', [])
        self._draw_tempo_markers(
            scene, all_staffs_list, [], y_offsets)

    # ------------------------------------------------------------------
    # Symbol creation
    # ------------------------------------------------------------------
    def _create_symbols_for_part(self, part, clef, tpb) -> list:
        """Create chords + bars + rests for one part."""
        chords = self._create_chords(part, clef, tpb)
        measure_len = self._get_measure_length_from_part(part, tpb)
        time_num, time_den = self._get_time_sig_from_part(part)
        last_start = self._get_last_start(part, tpb)

        symbols = self._add_bars(chords, measure_len, last_start)
        symbols = self._add_rests(symbols, tpb, time_num, time_den)
        return symbols

    def _create_chords(self, part, clef, tpb) -> list[ChordSymbol]:
        """Create ChordSymbols from part measures."""
        chords = []
        abs_tick = 0
        for measure in part.measures:
            measure_ticks = int(measure.duration_beats * tpb)
            time_groups: dict[int, list] = {}
            for note in measure.notes:
                tick = abs_tick + int(note.start_beat * tpb)
                if tick not in time_groups:
                    time_groups[tick] = []
                time_groups[tick].append(note)

            for tick in sorted(time_groups):
                notes = time_groups[tick]
                note_data = self._create_note_data(notes, tick, tpb)
                if note_data:
                    end_time = max(
                        tick + int(n.duration_beats * tpb) for n in notes)
                    chord = ChordSymbol(note_data, clef, tick, end_time)
                    chords.append(chord)

            abs_tick += measure_ticks
        return chords

    def _create_note_data(self, notes, tick, tpb) -> list[NoteData]:
        """Create NoteData list from model notes, sorted by pitch."""
        notes_sorted = sorted(notes, key=lambda n: n.pitch)
        result = []
        for i, n in enumerate(notes_sorted):
            wn = WhiteNote.from_midi(n.pitch)
            dur = ND.from_beats(n.duration_beats)
            pc = n.pitch % 12
            accid = SHARP if pc in (1, 3, 6, 8, 10) else ACCID_NONE
            left_side = True
            # Adjacent notes alternate sides
            if i > 0 and result:
                prev_wn = result[-1].whitenote
                if abs(wn.dist(prev_wn)) == 1:
                    left_side = not result[-1].left_side
            vel = getattr(n, 'expression', None)
            velocity = vel.velocity if vel and hasattr(vel, 'velocity') else 80
            nd = NoteData(n.pitch, wn, dur, left_side, accid, velocity)
            result.append(nd)
        return result

    # ------------------------------------------------------------------
    # AddBars
    # ------------------------------------------------------------------
    def _add_bars(self, chords, measure_len, last_start) -> list:
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

        # Keep adding bars until end
        if measure_len > 0:
            while measure_time < last_start:
                symbols.append(BarSymbol(measure_time))
                measure_time += measure_len
            symbols.append(BarSymbol(measure_time))

        return symbols

    # ------------------------------------------------------------------
    # AddRests
    # ------------------------------------------------------------------
    def _add_rests(self, symbols, tpb, time_num, time_den) -> list:
        """Add rest symbols between notes."""
        quarter = tpb
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

    def _get_rests(self, start, end, quarter) -> list:
        """Return rest symbols to fill the gap between start and end."""
        diff = end - start
        if diff <= 0:
            return []

        # Determine duration
        dur = self._duration_from_ticks(diff, quarter)
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

    @staticmethod
    def _duration_from_ticks(ticks, quarter) -> int | None:
        """Convert tick duration to NoteDuration."""
        whole = quarter * 4
        beats = ticks / quarter
        return ND.from_beats(beats)

    # ------------------------------------------------------------------
    # AlignSymbols
    # ------------------------------------------------------------------
    def _align_symbols(self, all_symbols, widths: SymbolWidths):
        """Vertically align symbols across tracks."""
        for track in range(len(all_symbols)):
            symbols = all_symbols[track]
            result = []
            i = 0

            for start in widths.start_times:
                # Pass through BarSymbols
                while (i < len(symbols)
                       and isinstance(symbols[i], BarSymbol)
                       and symbols[i].start_time <= start):
                    result.append(symbols[i])
                    i += 1

                if i < len(symbols) and symbols[i].start_time == start:
                    while (i < len(symbols)
                           and symbols[i].start_time == start):
                        result.append(symbols[i])
                        i += 1
                else:
                    result.append(BlankSymbol(start, 0))

            # Apply extra widths
            j = 0
            while j < len(result):
                if isinstance(result[j], BarSymbol):
                    j += 1
                    continue
                start = result[j].start_time
                extra = widths.get_extra_width(track, start)
                result[j].width = result[j].width + extra
                while j < len(result) and result[j].start_time == start:
                    j += 1

            all_symbols[track] = result

    # ------------------------------------------------------------------
    # CreateStaffs
    # ------------------------------------------------------------------
    def _create_staffs_for_track(self, symbols, measure_len,
                                 track_num, total_tracks,
                                 key_accids=None,
                                 time_num=0, time_den=0) -> list[Staff]:
        """Break symbols into page-width rows without splitting measures."""
        key_accids = key_accids or []
        keysig_width = SheetConfig.key_signature_width(key_accids)
        # Account for time signature width
        if time_num > 0 and time_den > 0:
            keysig_width += SheetConfig.NoteWidth * 2
        start_idx = 0
        staffs = []

        while start_idx < len(symbols):
            end_idx = start_idx
            width = keysig_width

            while (end_idx < len(symbols)
                   and width + symbols[end_idx].width < SheetConfig.PageWidth):
                width += symbols[end_idx].width
                end_idx += 1
            end_idx -= 1

            if end_idx < start_idx:
                end_idx = start_idx

            # Don't split measures
            if (end_idx < len(symbols) - 1 and measure_len > 0):
                if (symbols[start_idx].start_time // max(measure_len, 1)
                        != symbols[end_idx].start_time // max(measure_len, 1)):
                    end_measure = (symbols[min(end_idx + 1, len(symbols) - 1)]
                                   .start_time // max(measure_len, 1))
                    while (end_idx > start_idx
                           and symbols[end_idx].start_time // max(measure_len, 1)
                           == end_measure):
                        end_idx -= 1

            rng = symbols[start_idx:end_idx + 1]
            staff = Staff(rng, key_accids, measure_len,
                          track_num, total_tracks, time_num, time_den)
            staffs.append(staff)
            start_idx = end_idx + 1

        # Update end times
        for i in range(len(staffs) - 1):
            staffs[i].end_time = staffs[i + 1].start_time

        return staffs

    # ------------------------------------------------------------------
    # CreateAllBeamedChords
    # ------------------------------------------------------------------
    def _create_all_beamed_chords(self, all_symbols, time_num, time_den,
                                  quarter, measure_len):
        """Connect chords with horizontal beams."""
        if ((time_num == 3 and time_den == 4) or
                (time_num == 6 and time_den == 8) or
                (time_num == 6 and time_den == 4)):
            self._create_beamed_chords(
                all_symbols, 6, True, time_num, time_den,
                quarter, measure_len)

        self._create_beamed_chords(
            all_symbols, 4, True, time_num, time_den, quarter, measure_len)
        self._create_beamed_chords(
            all_symbols, 3, True, time_num, time_den, quarter, measure_len)
        self._create_beamed_chords(
            all_symbols, 2, True, time_num, time_den, quarter, measure_len)
        self._create_beamed_chords(
            all_symbols, 2, False, time_num, time_den, quarter, measure_len)

    def _create_beamed_chords(self, all_symbols, num_chords, start_beat,
                              time_num, time_den, quarter, measure_len):
        for symbols in all_symbols:
            start_index = 0
            while True:
                found, chord_indexes, horiz_dist = \
                    self._find_consecutive_chords(
                        symbols, start_index, num_chords)
                if not found:
                    break

                chords = [symbols[idx] for idx in chord_indexes]
                if ChordSymbol.can_create_beam(
                        chords, time_num, time_den, quarter,
                        measure_len, start_beat):
                    ChordSymbol.create_beam(chords, horiz_dist)
                    start_index = chord_indexes[-1] + 1
                else:
                    start_index = chord_indexes[0] + 1

    @staticmethod
    def _find_consecutive_chords(symbols, start_index, num_chords):
        """Find num_chords consecutive ChordSymbols (may skip BlankSymbols)."""
        i = start_index
        while True:
            horiz_dist = 0
            # Find starting chord
            while i < len(symbols) - num_chords:
                if isinstance(symbols[i], ChordSymbol):
                    c = symbols[i]
                    if c.stem is not None:
                        break
                i += 1
            if i >= len(symbols) - num_chords:
                return False, [], 0

            chord_indexes = [i]
            horiz_dist = symbols[i].width  # Start with first chord width
            found = True
            for ci in range(1, num_chords):
                i += 1
                remaining = num_chords - 1 - ci
                while (i < len(symbols) - remaining
                       and isinstance(symbols[i], BlankSymbol)):
                    horiz_dist += symbols[i].width
                    i += 1
                if i >= len(symbols) - remaining:
                    return False, [], 0
                if not isinstance(symbols[i], ChordSymbol):
                    found = False
                    break
                chord_indexes.append(i)
                if ci < num_chords - 1:
                    horiz_dist += symbols[i].width  # Middle chords

            if found:
                return True, chord_indexes, horiz_dist
            # Start searching from next position
            i = chord_indexes[0] + 1
            continue

    def _draw_tempo_markers(self, scene, all_staffs, parts_data, y_offsets):
        """Draw tempo change and deviation markers above notes.

        Shows:
        - Measure tempo changes (♩= 45) in green
        - Per-note tempo deviations (×0.80) in orange/blue
        """
        from PySide6.QtWidgets import QGraphicsSimpleTextItem

        if not all_staffs:
            return
        first_track_idx, first_staffs = all_staffs[0]

        piece = getattr(scene, 'piece', None)
        note_parts = []
        if piece:
            note_parts = [p for p in piece.parts
                          if not (p.audio_track and p.audio_track.blocks)]

        tpb = 480

        # 1) Measure tempo changes from model
        #    Show at the first note where the tempo applies.
        #    If there's no note in the tempo's measure, show at next measure.
        if note_parts:
            part = note_parts[0]
            abs_beat = 0.0
            prev_tempo = piece.initial_tempo
            for mi, m in enumerate(part.measures):
                if m.tempo and abs(m.tempo.bpm - prev_tempo) >= 0.5:
                    # Find first note tick in this measure or next
                    tick = int(abs_beat * tpb)
                    if m.notes:
                        tick = int((abs_beat + m.notes[0].start_beat) * tpb)
                    elif mi + 1 < len(part.measures):
                        next_beat = abs_beat + m.duration_beats
                        tick = int(next_beat * tpb)

                    bpm = int(round(m.tempo.bpm))
                    # Search through staff layout.
                    # If tick is at/near end of a staff (line break),
                    # show tempo at beginning of NEXT staff.
                    layout = getattr(self, '_staff_y_positions', [])
                    for si, (staff, y_top, y_bot) in enumerate(layout):
                        x = staff.find_x_for_pulse(tick)
                        if x is not None:
                            # Check if tick is near end of staff
                            if (tick >= staff.end_time - 1
                                    and si + 1 < len(layout)):
                                # Use next staff beginning
                                next_staff, ny_top, ny_bot = layout[si + 1]
                                scene_x = 100 + next_staff.keysig_width
                                scene_y = ny_top - 5
                            else:
                                scene_x = 100 + x
                                scene_y = y_top - 5
                            self._add_tempo_label(
                                scene, bpm, scene_x, scene_y)
                            break
                    prev_tempo = m.tempo.bpm
                abs_beat += m.duration_beats

        # 2) Per-note expression overlays (cent offset + tempo dev)
        if note_parts:
            for part in note_parts:
                abs_beat = 0.0
                for m in part.measures:
                    for n in m.notes:
                        cents = n.expression.cent_offset
                        dev = n.expression.duration_deviation
                        has_cents = abs(cents) >= 1.0
                        has_dev = abs(dev - 1.0) >= 0.01
                        if not has_cents and not has_dev:
                            continue
                        tick = int((abs_beat + n.start_beat) * tpb)
                        layout = getattr(self, '_staff_y_positions', [])
                        for staff, y_top, y_bot in layout:
                            x = staff.find_x_for_pulse(tick)
                            if x is not None:
                                scene_x = 100 + x
                                y_base = y_top + staff.ytop - 14
                                if has_cents:
                                    sign = "+" if cents > 0 else ""
                                    item = QGraphicsSimpleTextItem(
                                        f"{sign}{cents:.0f}ct")
                                    item.setFont(QFont(
                                        "Arial", 7, QFont.Weight.Bold))
                                    from PySide6.QtCore import QSettings as _QS
                                    _s = _QS("MusiAI", "MusiAI")
                                    if cents > 0:
                                        _pc = _s.value("musicxml/pitch_color_high", "#FF4400")
                                    else:
                                        _pc = _s.value("musicxml/pitch_color_low", "#0088FF")
                                    item.setBrush(QBrush(QColor(_pc)))
                                    item.setPos(scene_x - 8, y_base)
                                    item.setZValue(20)
                                    scene.addItem(item)
                                    # Visual marker (zigzag or curve) before note
                                    glide = n.expression.glide_type
                                    self._draw_cent_marker(
                                        scene, scene_x - 22, y_base + 12,
                                        cents, glide)
                                if has_dev:
                                    y_dev = y_base - 10 if has_cents else y_base
                                    item = QGraphicsSimpleTextItem(
                                        f"\u00d7{dev:.2f}")
                                    item.setFont(QFont(
                                        "Arial", 7, QFont.Weight.Bold))
                                    color = (QColor(200, 100, 0) if dev < 1.0
                                             else QColor(0, 80, 200))
                                    item.setBrush(QBrush(color))
                                    item.setPos(scene_x - 10, y_dev)
                                    item.setZValue(20)
                                    scene.addItem(item)
                                break
                    abs_beat += m.duration_beats

        # 4) Tempo from parts_data (music21 file-based rendering)
        if not note_parts and parts_data:
            tempo = parts_data[0].get('tempo_bpm')
            if tempo and tempo > 0:
                y = y_offsets[0] - 5 if y_offsets else 40
                self._add_tempo_label(scene, int(round(tempo)), 105, y)

    @staticmethod
    def _sync_model_velocity(parts_data, piece):
        """Copy velocity from model Notes into converter NoteData.

        The converter parses from file and doesn't know about model edits.
        This syncs velocity so pixmap colors reflect user changes.
        Matches by MIDI pitch with tick tolerance (±5 ticks).
        """
        tpb = 480
        note_parts = [p for p in piece.parts
                      if not (p.audio_track and p.audio_track.blocks)]
        for pi, pd in enumerate(parts_data):
            if pi >= len(note_parts):
                break
            # Build sorted list of (tick, midi, velocity) from model
            model_notes = []
            abs_beat = 0.0
            for m in note_parts[pi].measures:
                for n in m.notes:
                    tick = int((abs_beat + n.start_beat) * tpb)
                    model_notes.append((tick, n.pitch, n.expression.velocity))
                abs_beat += m.duration_beats
            # Update NoteData velocity in symbols — match by pitch + nearest tick
            for sym in pd['symbols']:
                if isinstance(sym, ChordSymbol):
                    for nd in sym.notedata:
                        best_vel = None
                        best_dist = 999
                        for mt, mp, mv in model_notes:
                            if mp == nd.number and abs(mt - sym.start_time) < best_dist:
                                best_dist = abs(mt - sym.start_time)
                                best_vel = mv
                        if best_vel is not None and best_dist <= 60:
                            nd.velocity = best_vel

    @staticmethod
    def _draw_cent_marker(scene, x, y, cents, glide_type):
        """Draw zigzag or curve marker for cent offset."""
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath
        from PySide6.QtCore import QSettings
        settings = QSettings("MusiAI", "MusiAI")
        if cents > 0:
            color = QColor(settings.value("musicxml/pitch_color_high", "#FF4400"))
        elif cents < 0:
            color = QColor(settings.value("musicxml/pitch_color_low", "#0088FF"))
        else:
            color = QColor(settings.value("musicxml/pitch_color_std", "#FF8C1E"))
        pen = QPen(color, 1.5)
        w = min(20, max(8, abs(cents) / 5))
        h = min(6, max(3, abs(cents) / 15))

        path = QPainterPath()
        if glide_type == "zigzag":
            # Zigzag pattern
            path.moveTo(x, y)
            steps = 4
            dx = w / steps
            for i in range(steps):
                dy = h if i % 2 == 0 else -h
                path.lineTo(x + dx * (i + 1), y + dy)
        elif glide_type == "curve":
            # Smooth curve
            path.moveTo(x, y)
            path.cubicTo(x + w * 0.3, y - h,
                         x + w * 0.7, y + h,
                         x + w, y)
        else:
            # Default: small circle
            path.addEllipse(x, y - 2, 5, 5)

        item = QGraphicsPathItem(path)
        item.setPen(pen)
        item.setZValue(20)
        scene.addItem(item)

    @staticmethod
    def _draw_waveform(scene, part, y_offset, system_width, tempo):
        """Draw audio waveform for an audio part."""
        from musiai.notation.WaveformItem import WaveformItem
        ppb = 40  # pixels per beat for waveform
        for i, block in enumerate(part.audio_track.blocks):
            dur_beats = block.duration_beats(tempo)
            width = min(dur_beats * ppb, system_width - 120)
            x = 100 + block.start_beat * ppb
            item = WaveformItem(block.samples, block.sr, width, x,
                                y_offset + 10, i)
            item.setData(0, "waveform")
            # Store part index for context menu
            piece = getattr(scene, 'piece', None)
            part_idx = piece.parts.index(part) if piece and part in piece.parts else 0
            item.setData(1, part_idx)
            scene.addItem(item)

    @staticmethod
    def _find_bar_x(staff, tick: int) -> int | None:
        """Find x position of the barline at the given tick."""
        from musiai.ui.midi.BarSymbol import BarSymbol
        xpos = staff.keysig_width
        for sym in staff.symbols:
            if isinstance(sym, BarSymbol) and sym.start_time == tick:
                return xpos
            xpos += sym.width
        # Fallback: use find_x_for_pulse
        return staff.find_x_for_pulse(tick)

    def _store_staff_layout(self, scene):
        """Store staff layout on the scene for playhead positioning.

        Each entry: (staff, y_top, y_bottom) — same as MidiSheetMusic's
        ShadeNotes approach: iterate staffs, call find_x_for_pulse().
        Pixmaps are at x=100 in scene coordinates.
        """
        layout = getattr(self, '_staff_y_positions', [])
        if hasattr(scene, '_staff_layout'):
            scene._staff_layout = layout
            scene._staff_x_offset = 100  # pixmaps placed at x=100

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_measure_length(self, piece, tpb) -> int:
        if piece.parts and piece.parts[0].measures:
            m = piece.parts[0].measures[0]
            return int(m.duration_beats * tpb)
        return tpb * 4

    def _get_measure_length_from_part(self, part, tpb) -> int:
        if part.measures:
            return int(part.measures[0].duration_beats * tpb)
        return tpb * 4

    def _get_time_sig(self, piece) -> tuple[int, int]:
        if piece.parts and piece.parts[0].measures:
            m = piece.parts[0].measures[0]
            return getattr(m, 'time_num', 4), getattr(m, 'time_den', 4)
        return 4, 4

    def _get_time_sig_from_part(self, part) -> tuple[int, int]:
        if part.measures:
            m = part.measures[0]
            return getattr(m, 'time_num', 4), getattr(m, 'time_den', 4)
        return 4, 4

    def _get_last_start(self, part, tpb) -> int:
        """Tick nach dem letzten Takt mit Noten + 1 Takt für Endstrich."""
        last_tick = 0
        abs_tick = 0
        measure_len = int(part.measures[0].duration_beats * tpb) if part.measures else tpb * 4
        for m in part.measures:
            abs_tick += int(m.duration_beats * tpb)
            if m.notes:
                last_tick = abs_tick
        # Add one measure for the final barline
        if last_tick > 0:
            return last_tick + measure_len
        return abs_tick

    def _get_part(self, piece, track_idx):
        midi_idx = 0
        for p in piece.parts:
            if p.audio_track and p.audio_track.blocks:
                continue
            if midi_idx == track_idx:
                return p
            midi_idx += 1
        return None

    @staticmethod
    def _draw_part_label(scene, name: str, track_idx: int,
                         x: float, y: float, font_size: int = 8):
        """Draw part label + mute icon with data tags for click handling."""
        lbl = QGraphicsSimpleTextItem(name)
        lbl.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        lbl.setBrush(QBrush(QColor(30, 30, 80)))
        lbl.setPos(x, y)
        lbl.setZValue(5)
        lbl.setData(0, "part_label")
        lbl.setData(1, track_idx)
        scene.addItem(lbl)

        mute = QGraphicsSimpleTextItem("\U0001F50A")
        mute.setFont(QFont("Segoe UI Emoji", 12))
        mute.setPos(x, y + 18)
        mute.setZValue(5)
        mute.setData(0, "part_mute")
        mute.setData(1, track_idx)
        scene.addItem(mute)

    def _draw_tempo_marking(self, scene, tempo_bpm, y_offset):
        """Draw tempo marking (quarter note = BPM) above first system."""
        self._add_tempo_label(scene, int(round(tempo_bpm)), 105, y_offset - 28)

    @staticmethod
    def _add_tempo_label(scene, bpm: int, x: float, y: float):
        """Draw ♩= BPM above the staff. Large note, normal text."""
        note = scene.addText("\u2669")
        note.setFont(QFont("Arial", 18))
        note.setDefaultTextColor(QColor(0, 0, 0))
        note.setPos(x, y - 4)
        note.setZValue(20)

        text = scene.addText(f"= {bpm}")
        text.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        text.setDefaultTextColor(QColor(0, 0, 0))
        text.setPos(x + 14, y)
        text.setZValue(20)

    def _render_staff(self, staff: Staff, cfg: dict) -> QPixmap:
        """Render a staff onto a QPixmap at 2x resolution for sharpness.

        Uses devicePixelRatio so Qt handles the scaling transparently:
        the pixmap is 2x pixels but reports as 1x logical size, giving
        crisp rendering on both standard and HiDPI displays without
        a lossy downscale step.
        """
        scale = 2  # Retina-like rendering
        width = SheetConfig.PageWidth
        height = max(staff.height + 40, 140)  # Extra space for flags/ledger lines

        # Create pixmap at 2x pixel resolution
        pixmap = QPixmap(width * scale, height * scale)
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(QColor(255, 255, 255))

        painter = QPainter(pixmap)
        # Enable antialiasing for smooth curves (ties, slurs) at 2x resolution
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # devicePixelRatio handles the 2x mapping; painter uses logical coords
        staff.draw(painter, 0, cfg)
        painter.end()

        return pixmap
