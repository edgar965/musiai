"""MidiSheetRenderer - Hauptklasse fuer MIDI-Notenblatt-Rendering.

Portiert von SheetControl.cs: CreateAllMusicalSymbols, AddBars, AddRests,
AlignSymbols, CreateStaffs, CreateAllBeamedChords.
"""

import logging
from PySide6.QtWidgets import QGraphicsScene
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

    def __init__(self, config: SheetConfig = None, use_bravura: bool = False):
        self.config = config or SheetConfig.large()
        self.use_bravura = use_bravura
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
        y_offset = 60

        converter = Music21Converter()
        try:
            parts_data = converter.convert(file_path)
        except Exception as e:
            logger.error(f"music21 parse failed: {e}", exc_info=True)
            return

        if not parts_data:
            return

        track_symbols = [pd['symbols'] for pd in parts_data]

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
                track_idx, len(track_symbols))
            for s in staffs:
                s.calculate_height()
            all_staffs.append((track_idx, staffs))

        if interleave and len(all_staffs) > 1:
            y_offset = self._render_interleaved(
                scene, all_staffs, parts_data, cfg, y_offset, system_width)
        else:
            y_offset = self._render_sequential(
                scene, all_staffs, parts_data, cfg, y_offset, system_width)

        scene.setSceneRect(0, 0, system_width + 60, y_offset + 40)
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

        for row in range(max_rows):
            system_top = y_offset

            # Alle Tracks dieser Zeile direkt untereinander
            for i, (track_idx, staffs) in enumerate(all_staffs):
                if row >= len(staffs):
                    continue
                staff = staffs[row]

                # Part-Label links neben dem Staff (jede Zeile)
                if row == 0 or True:
                    pd = parts_data[track_idx]
                    lbl = scene.addText(pd['part_name'])
                    lbl.setFont(QFont("Arial", 8))
                    lbl.setDefaultTextColor(QColor(50, 50, 100))
                    lbl.setPos(4, y_offset + 15)

                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                y_offset += staff.height - 8  # Eng zusammen

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
        for track_idx, staffs in all_staffs:
            pd = parts_data[track_idx]

            label = scene.addText(pd['part_name'])
            label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label.setDefaultTextColor(QColor(30, 30, 80))
            label.setPos(4, y_offset)

            for staff in staffs:
                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                y_offset += staff.height + 15
            y_offset += 20

        return y_offset

    def render(self, piece: Piece, scene: QGraphicsScene,
               system_width: float = 1100) -> None:
        if not piece or not piece.parts:
            return

        self.config.page_width = int(system_width) - 120
        SheetConfig.PageWidth = self.config.page_width
        cfg = self.config.to_dict()
        cfg["use_bravura"] = self.use_bravura
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
        # Create staffs and render
        for track_idx, symbols in enumerate(track_symbols):
            clef = track_clefs[track_idx]
            part = self._get_part(piece, track_idx)

            staffs = self._create_staffs_for_track(
                symbols, measure_len, track_idx, len(track_symbols))

            # Recalculate heights after beaming
            for s in staffs:
                s.calculate_height()

            # Part label
            label = scene.addText(part.name if part else f"Track {track_idx}")
            label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label.setDefaultTextColor(QColor(30, 30, 80))
            label.setPos(4, y_offset)

            for staff in staffs:
                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                y_offset += staff.height + 15
            y_offset += 20

        scene.setSceneRect(0, 0, system_width + 60, y_offset + 40)

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
            nd = NoteData(n.pitch, wn, dur, left_side, accid)
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
                                 track_num, total_tracks) -> list[Staff]:
        """Break symbols into page-width rows without splitting measures."""
        keysig_width = SheetConfig.key_signature_width([])
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
            staff = Staff(rng, [], measure_len, track_num, total_tracks)
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
            all_symbols, 3, True, time_num, time_den, quarter, measure_len)
        self._create_beamed_chords(
            all_symbols, 4, True, time_num, time_den, quarter, measure_len)
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
                horiz_dist += symbols[i].width

            if found:
                return True, chord_indexes, horiz_dist
            # Start searching from next position
            i = chord_indexes[0] + 1
            continue

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
        abs_tick = 0
        for m in part.measures:
            abs_tick += int(m.duration_beats * tpb)
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

    def _render_staff(self, staff: Staff, cfg: dict) -> QPixmap:
        """Render a staff onto a QPixmap."""
        width = SheetConfig.PageWidth
        # Extra Platz für Noten über/unter dem System + Taktnummern
        height = max(staff.height + 20, 120)
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        staff.draw(painter, 0, cfg)
        painter.end()
        return pixmap
