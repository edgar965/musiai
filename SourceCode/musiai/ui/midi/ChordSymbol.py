"""ChordSymbol - Notengruppe am gleichen Zeitpunkt (portiert von ChordSymbol.cs)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.WhiteNote import WhiteNote, TOP_TREBLE, TOP_BASS
from musiai.ui.midi.WhiteNote import BOTTOM_TREBLE, BOTTOM_BASS, B, D
from musiai.ui.midi.Stem import Stem, UP, DOWN
from musiai.ui.midi.AccidSymbol import AccidSymbol, NONE as ACCID_NONE
from musiai.ui.midi.ClefSymbol import TREBLE
from musiai.ui.midi import NoteDuration as ND


class NoteData:
    """Daten einer einzelnen Note im Akkord."""
    __slots__ = ('number', 'whitenote', 'duration', 'left_side', 'accid',
                 'velocity')

    def __init__(self, number: int, whitenote: WhiteNote,
                 duration: int, left_side: bool = True, accid: int = 0,
                 velocity: int = 80):
        self.number = number
        self.whitenote = whitenote
        self.duration = duration
        self.left_side = left_side
        self.accid = accid
        self.velocity = velocity


class ChordSymbol(MusicSymbol):
    """Gruppe von Noten die gleichzeitig erklingen."""

    def __init__(self, notedata: list[NoteData], clef: int = TREBLE,
                 start_time: int = 0, end_time: int = 0):
        super().__init__(start_time)
        self.clef = clef
        self.notedata = notedata  # sorted low to high
        self._end_time = end_time
        self.accidsymbols: list[AccidSymbol] = []
        self.stem1: Stem | None = None
        self.stem2: Stem | None = None
        self.hastwostems = False
        self.tied_to_next = False
        self.drawn_notes: list[tuple] = []  # [(x, y, w, h, NoteData), ...]

        if not notedata:
            return

        # Create accidentals
        self.accidsymbols = self._create_accid_symbols(notedata, clef)

        # Determine stems
        dur1 = notedata[0].duration
        dur2 = dur1
        change = -1
        for i, nd in enumerate(notedata):
            if nd.duration != dur1:
                dur2 = nd.duration
                change = i
                break

        if change >= 0 and dur1 != dur2:
            self.hastwostems = True
            self.stem1 = Stem(
                notedata[0].whitenote, notedata[change - 1].whitenote,
                dur1, DOWN,
                self._notes_overlap(notedata, 0, change))
            self.stem2 = Stem(
                notedata[change].whitenote, notedata[-1].whitenote,
                dur2, UP,
                self._notes_overlap(notedata, change, len(notedata)))
        else:
            direction = self._stem_direction(
                notedata[0].whitenote, notedata[-1].whitenote, clef)
            self.stem1 = Stem(
                notedata[0].whitenote, notedata[-1].whitenote,
                dur1, direction,
                self._notes_overlap(notedata, 0, len(notedata)))
            self.stem2 = None

        if dur1 == ND.WHOLE:
            self.stem1 = None
        if dur2 == ND.WHOLE:
            self.stem2 = None

        self._width = self.min_width

    @property
    def end_time(self) -> int:
        return self._end_time

    @end_time.setter
    def end_time(self, val: int):
        self._end_time = val

    @property
    def stem(self) -> Stem | None:
        """Return the stem with smallest duration (best for beaming)."""
        if self.stem1 is None:
            return self.stem2
        if self.stem2 is None:
            return self.stem1
        if self.stem1.duration < self.stem2.duration:
            return self.stem1
        return self.stem2

    @property
    def min_width(self) -> int:
        return self._get_min_width()

    def _get_min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC._nh
        result = 2 * nh + nh * 3 // 4
        if self.accidsymbols:
            result += self.accidsymbols[0].min_width
            for i in range(1, len(self.accidsymbols)):
                if self.accidsymbols[i].note.dist(
                        self.accidsymbols[i - 1].note) < 6:
                    result += self.accidsymbols[i].min_width
        return result

    @property
    def above_staff(self) -> int:
        if not self.notedata:
            return 0
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC._nh
        topnote = self.notedata[-1].whitenote
        if self.stem1:
            topnote = WhiteNote.max(topnote, self.stem1.end)
        if self.stem2:
            topnote = WhiteNote.max(topnote, self.stem2.end)
        dist = topnote.dist(WhiteNote.top(self.clef)) * nh // 2
        result = dist if dist > 0 else 0
        for sym in self.accidsymbols:
            result = max(result, sym.above_staff)
        return result

    @property
    def below_staff(self) -> int:
        if not self.notedata:
            return 0
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nh = SC._nh
        bottomnote = self.notedata[0].whitenote
        if self.stem1:
            bottomnote = WhiteNote.min(bottomnote, self.stem1.end)
        if self.stem2:
            bottomnote = WhiteNote.min(bottomnote, self.stem2.end)
        dist = WhiteNote.bottom(self.clef).dist(bottomnote) * nh // 2
        result = dist if dist > 0 else 0
        for sym in self.accidsymbols:
            result = max(result, sym.below_staff)
        return result

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _create_accid_symbols(notedata, clef) -> list:
        result = []
        for nd in notedata:
            if nd.accid != ACCID_NONE:
                result.append(AccidSymbol(nd.accid, nd.whitenote, clef))
        return result

    @staticmethod
    def _stem_direction(bottom: WhiteNote, top: WhiteNote,
                        clef: int) -> int:
        if clef == TREBLE:
            middle = WhiteNote(B, 5)
        else:
            middle = WhiteNote(D, 3)
        dist = middle.dist(bottom) + middle.dist(top)
        return UP if dist >= 0 else DOWN

    @staticmethod
    def _notes_overlap(notedata, start: int, end: int) -> bool:
        for i in range(start, end):
            if not notedata[i].left_side:
                return True
        return False

    # ------------------------------------------------------------------
    # Beaming
    # ------------------------------------------------------------------
    @staticmethod
    def can_create_beam(chords: list['ChordSymbol'], time_num: int,
                        time_den: int, quarter: int, measure: int,
                        start_beat: bool) -> bool:
        """Check if these chords can be connected by a beam."""
        num_chords = len(chords)
        first_stem = chords[0].stem
        last_stem = chords[-1].stem
        if not first_stem or not last_stem:
            return False

        meas = chords[0].start_time // measure if measure > 0 else 0
        dur = first_stem.duration
        dur2 = last_stem.duration

        dotted8_to_16 = (num_chords == 2
                         and dur == ND.DOTTED_EIGHTH
                         and dur2 == ND.SIXTEENTH)

        if dur in (ND.WHOLE, ND.HALF, ND.DOTTED_HALF, ND.QUARTER,
                   ND.DOTTED_QUARTER):
            return False
        if dur == ND.DOTTED_EIGHTH and not dotted8_to_16:
            return False

        if num_chords == 6:
            if dur != ND.EIGHTH:
                return False
            ok = ((time_num == 3 and time_den == 4) or
                  (time_num == 6 and time_den == 8) or
                  (time_num == 6 and time_den == 4))
            if not ok:
                return False
            if time_num == 6 and time_den == 4:
                beat = quarter * 3
                if (chords[0].start_time % beat) > quarter // 6:
                    return False
        elif num_chords == 4:
            if time_num == 3 and time_den == 8:
                return False
            ok = time_num in (2, 4, 8)
            if not ok and dur != ND.SIXTEENTH:
                return False
            beat = quarter
            if dur == ND.EIGHTH:
                beat = quarter * 2
            elif dur == ND.THIRTYSECOND:
                beat = quarter // 2
            if (chords[0].start_time % beat) > quarter // 6:
                return False
        elif num_chords == 3:
            valid = (dur == ND.TRIPLET or
                     (dur == ND.EIGHTH and time_num == 12 and time_den == 8))
            if not valid:
                return False
            beat = quarter
            if time_num == 12 and time_den == 8:
                beat = quarter // 2 * 3
            if (chords[0].start_time % beat) > quarter // 6:
                return False
        elif num_chords == 2:
            if start_beat:
                beat = quarter
                if (chords[0].start_time % beat) > quarter // 6:
                    return False

        for chord in chords:
            if measure > 0 and (chord.start_time // measure) != meas:
                return False
            if chord.stem is None:
                return False
            if chord.stem.duration != dur and not dotted8_to_16:
                return False
            if chord.stem.is_beam:
                return False

        # Check all stems can point same direction
        has_two = False
        direction = UP
        for chord in chords:
            if chord.hastwostems:
                if has_two and chord.stem.direction != direction:
                    return False
                has_two = True
                direction = chord.stem.direction

        if not has_two:
            n1 = (first_stem.top if first_stem.direction == UP
                  else first_stem.bottom)
            n2 = (last_stem.top if last_stem.direction == UP
                  else last_stem.bottom)
            direction = ChordSymbol._stem_direction(n1, n2, chords[0].clef)

        # Notes too far apart?
        if direction == UP:
            if abs(first_stem.top.dist(last_stem.top)) >= 11:
                return False
        else:
            if abs(first_stem.bottom.dist(last_stem.bottom)) >= 11:
                return False
        return True

    @staticmethod
    def create_beam(chords: list['ChordSymbol'], spacing: int):
        """Connect chords with a horizontal beam."""
        first_stem = chords[0].stem
        last_stem = chords[-1].stem

        # Calculate new direction
        new_dir = -1
        for chord in chords:
            if chord.hastwostems:
                new_dir = chord.stem.direction
                break
        if new_dir == -1:
            n1 = (first_stem.top if first_stem.direction == UP
                  else first_stem.bottom)
            n2 = (last_stem.top if last_stem.direction == UP
                  else last_stem.bottom)
            new_dir = ChordSymbol._stem_direction(n1, n2, chords[0].clef)

        for chord in chords:
            chord.stem.change_direction(new_dir)

        if len(chords) == 2:
            ChordSymbol._bring_stems_closer(chords)
        else:
            ChordSymbol._line_up_stem_ends(chords)

        first_stem.set_pair(last_stem, spacing)
        for i in range(1, len(chords)):
            chords[i].stem.receiver = True

    @staticmethod
    def _bring_stems_closer(chords):
        fs = chords[0].stem
        ls = chords[1].stem
        if (fs.duration == ND.DOTTED_EIGHTH
                and ls.duration == ND.SIXTEENTH):
            if fs.direction == UP:
                fs.end = fs.end.add(2)
            else:
                fs.end = fs.end.add(-2)
        distance = abs(fs.end.dist(ls.end))
        if fs.direction == UP:
            if WhiteNote.max(fs.end, ls.end) == fs.end:
                ls.end = ls.end.add(distance // 2)
            else:
                fs.end = fs.end.add(distance // 2)
        else:
            if WhiteNote.min(fs.end, ls.end) == fs.end:
                ls.end = ls.end.add(-distance // 2)
            else:
                fs.end = fs.end.add(-distance // 2)

    @staticmethod
    def _line_up_stem_ends(chords):
        fs = chords[0].stem
        ls = chords[-1].stem
        ms = chords[1].stem
        if fs.direction == UP:
            top = fs.end
            for c in chords:
                top = WhiteNote.max(top, c.stem.end)
            if top == fs.end and top.dist(ls.end) >= 2:
                ms.end = top.add(-1)
                ls.end = top.add(-2)
            elif top == ls.end and top.dist(fs.end) >= 2:
                fs.end = top.add(-2)
                ms.end = top.add(-1)
            else:
                fs.end = top
                ms.end = top
                ls.end = top
        else:
            bottom = fs.end
            for c in chords:
                bottom = WhiteNote.min(bottom, c.stem.end)
            if bottom == fs.end and ls.end.dist(bottom) >= 2:
                ms.end = bottom.add(1)
                ls.end = bottom.add(2)
            elif bottom == ls.end and fs.end.dist(bottom) >= 2:
                ms.end = bottom.add(1)
                fs.end = bottom.add(2)
            else:
                fs.end = bottom
                ms.end = bottom
                ls.end = bottom
        for i in range(1, len(chords) - 1):
            chords[i].stem.end = ms.end

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor, QBrush, QPainterPath
        from PySide6.QtCore import Qt, QRectF
        from musiai.ui.midi.SheetConfig import SheetConfig as SC

        nh = SC._nh
        nw = SC._nw
        ls = SC._ls
        lw = SC._lw

        topstaff = WhiteNote.top(self.clef)

        # Align chord to the right
        offset = self.width - self.min_width

        # Draw accidentals
        ax = x + offset
        accid_width = self._draw_accid(painter, ax, ytop, config)

        # Draw notes
        nx_base = ax + accid_width
        use_bravura = config.get('use_bravura', False) if isinstance(config, dict) else False
        color_mode = config.get('color_mode', False) if isinstance(config, dict) else False
        self._draw_notes(painter, nx_base, ytop, topstaff, nh, nw, ls, lw,
                         use_bravura=use_bravura, color_mode=color_mode)

        # Draw stems
        stem_cfg = config.copy() if isinstance(config, dict) else {}
        stem_cfg['line_space'] = ls
        stem_cfg['note_width'] = nw
        stem_cfg['note_height'] = nh
        if self.stem1:
            self.stem1.draw(painter, nx_base, ytop, stem_cfg, topstaff)
        if self.stem2:
            self.stem2.draw(painter, nx_base, ytop, stem_cfg, topstaff)

    def _draw_accid(self, painter, x, ytop, config=None) -> int:
        """Draw accidentals, return total x width used."""
        xpos = 0
        prev = None
        cfg = config if isinstance(config, dict) else {}
        for sym in self.accidsymbols:
            if prev is not None and sym.note.dist(prev.note) < 6:
                xpos += sym.width
            sym.draw(painter, x + xpos, ytop, cfg)
            prev = sym
        if prev is not None:
            xpos += prev.width
        return xpos

    def _draw_notes(self, painter, x, ytop, topstaff, nh, nw, ls, lw,
                    use_bravura=False, color_mode=False):
        from PySide6.QtGui import QPen, QColor, QBrush, QFont
        from PySide6.QtCore import Qt

        pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(pen)
        self.drawn_notes = []

        for note in self.notedata:
            ynote = ytop + topstaff.dist(note.whitenote) * nh // 2
            xnote = x + ls // 4
            if not note.left_side:
                xnote += nw

            # Store hit rect for click detection
            self.drawn_notes.append((xnote, ynote - nh // 2, nw, nh, note))

            if use_bravura:
                self._draw_note_bravura(
                    painter, note, xnote, ynote, nh, nw, ls,
                    color_mode=color_mode, lw=lw)
            else:
                self._draw_note_ellipse(
                    painter, note, xnote, ynote, nh, nw, ls, lw,
                    color_mode=color_mode)

            # Dotted notes -- SMuFL-aware positioning
            if note.duration in (ND.DOTTED_HALF, ND.DOTTED_QUARTER,
                                 ND.DOTTED_EIGHTH):
                if use_bravura:
                    from musiai.ui.midi.BravuraGlyphs import DOT, FONT_NAME
                    from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
                    dot_size = SMuFLMetadata.notehead_font_size(ls)
                    dot_sc = SMuFLMetadata.font_scale(dot_size)
                    painter.setFont(QFont(FONT_NAME, dot_size))
                    if color_mode:
                        from musiai.notation.ColorScheme import ColorScheme
                        dc = ColorScheme.velocity_to_color(note.velocity)
                        painter.setPen(QPen(dc))
                    else:
                        painter.setPen(QPen(QColor(0, 0, 0)))

                    # Dot x: notehead width + small gap
                    ne_bbox = SMuFLMetadata.get_bbox('noteheadBlack')
                    ne = ne_bbox.get('bBoxNE', [1.18, 0.5])
                    notehead_width = ne[0] * dot_sc
                    dot_gap = SMuFLMetadata.get_engraving_default(
                        'augmentationDotNoteHeadXOffset', 0.3)
                    dot_x = int(xnote + notehead_width + dot_gap * dot_sc)

                    # Dot y: if note is ON a staff line, shift up to space
                    staff_pos = topstaff.dist(note.whitenote)
                    on_line = (staff_pos % 2 == 0)
                    if on_line:
                        dot_y = ynote  # shift up half a space
                    else:
                        dot_y = ynote + nh // 2  # center in space

                    painter.drawText(dot_x, dot_y, DOT)
                else:
                    painter.setBrush(QBrush(QColor(0, 0, 0)))
                    # Same on-line check for ellipse dots
                    staff_pos = topstaff.dist(note.whitenote)
                    on_line = (staff_pos % 2 == 0)
                    dot_ey = ynote + (ls // 6 if on_line else ls // 3)
                    painter.drawEllipse(
                        xnote + nw + ls // 2, dot_ey,
                        max(3, ls // 2), max(3, ls // 2))

            # Ledger lines
            self._draw_ledger_lines(painter, note.whitenote, xnote, nw,
                                    ytop, topstaff, nh, ls, lw,
                                    use_bravura=use_bravura)

    @staticmethod
    def _draw_note_bravura(painter, note, xnote, ynote, nh, nw, ls,
                           color_mode=False, lw=1):
        """Notenkopf mit Bravura SMuFL Glyph, positioned via metadata."""
        from PySide6.QtGui import QFont, QPen, QColor
        from musiai.ui.midi import BravuraGlyphs as BG
        from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata

        size = SMuFLMetadata.notehead_font_size(ls)
        sc = SMuFLMetadata.font_scale(size)
        painter.setFont(QFont(BG.FONT_NAME, size))
        if color_mode:
            from musiai.notation.ColorScheme import ColorScheme
            color = ColorScheme.velocity_to_color(note.velocity)
        else:
            color = QColor(0, 0, 0)
        painter.setPen(QPen(color))
        if note.duration in (ND.WHOLE,):
            glyph = BG.NOTEHEAD_WHOLE
            glyph_name = 'noteheadWhole'
        elif note.duration in (ND.HALF, ND.DOTTED_HALF):
            glyph = BG.NOTEHEAD_HALF
            glyph_name = 'noteheadHalf'
        else:
            glyph = BG.NOTEHEAD_FILLED
            glyph_name = 'noteheadBlack'

        # Use SMuFL bounding box for precise vertical centering.
        # Staff line y = ytop - lw + line * (lw + ls).
        # ynote = ytop + dist * nh // 2.
        # Glyph baseline must place center on staff line/space.
        # Adjust by -lw to align with staff line grid.
        bbox = SMuFLMetadata.get_bbox(glyph_name)
        ne = bbox.get('bBoxNE', [0, 0])
        sw = bbox.get('bBoxSW', [0, 0])
        glyph_center_y = (ne[1] + sw[1]) / 2.0
        y_draw = ynote - lw + nh // 2 + int(glyph_center_y * sc)

        painter.drawText(xnote, y_draw, glyph)

    @staticmethod
    def _draw_note_ellipse(painter, note, xnote, ynote, nh, nw, ls, lw,
                           color_mode=False):
        """Notenkopf mit rotierter Ellipse (Original-Methode)."""
        from PySide6.QtGui import QPen, QColor, QBrush
        from PySide6.QtCore import Qt
        if color_mode:
            from musiai.notation.ColorScheme import ColorScheme
            color = ColorScheme.velocity_to_color(note.velocity)
        else:
            color = QColor(0, 0, 0)
        cx = xnote + nw // 2 + 1
        cy = ynote - lw + nh // 2
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-45)
        if note.duration in (ND.WHOLE, ND.HALF, ND.DOTTED_HALF):
            painter.setBrush(QBrush(Qt.GlobalColor.transparent))
            painter.setPen(QPen(color, 1))
            painter.drawEllipse(-nw // 2, -nh // 2, nw, nh - 1)
            painter.drawEllipse(-nw // 2, -nh // 2 + 1, nw, nh - 2)
            painter.drawEllipse(-nw // 2, -nh // 2 + 1, nw, nh - 3)
        else:
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
            painter.drawEllipse(-nw // 2, -nh // 2, nw, nh - 1)
            painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.setPen(QPen(color, 1))
        painter.restore()

    def _draw_ledger_lines(self, painter, whitenote, xnote, nw,
                           ytop, topstaff, nh, ls, lw,
                           use_bravura=False):
        from PySide6.QtGui import QPen, QColor
        from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata

        # Ledger line extension from SMuFL
        if use_bravura:
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)
            ext = SMuFLMetadata.get_engraving_default(
                'legerLineExtension', 0.4)
            ledger_ext = int(ext * sc)
            nh_w = SMuFLMetadata.get_bbox('noteheadBlack').get(
                'bBoxNE', [1.18, 0.5])[0]
            head_w = int(nh_w * sc)
        else:
            ledger_ext = ls // 4
            head_w = nw

        ledger_thick = max(1, int(SMuFLMetadata.get_engraving_default(
            'legerLineThickness', 0.16) * sc)) if use_bravura else 1
        pen = QPen(QColor(0, 0, 0), ledger_thick)
        painter.setPen(pen)

        # Above staff
        top = topstaff.add(1)
        dist = whitenote.dist(top)
        y = ytop - lw
        if dist >= 2:
            for i in range(2, dist + 1, 2):
                y -= nh
                painter.drawLine(xnote - ledger_ext, int(y),
                                 xnote + head_w + ledger_ext, int(y))

        # Below staff
        bottom = top.add(-8)
        y = ytop + (ls + lw) * 4 - 1
        dist = bottom.dist(whitenote)
        if dist >= 2:
            for i in range(2, dist + 1, 2):
                y += nh
                painter.drawLine(xnote - ledger_ext, int(y),
                                 xnote + head_w + ledger_ext, int(y))
