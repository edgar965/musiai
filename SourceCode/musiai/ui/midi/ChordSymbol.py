"""ChordSymbol - Notengruppe am gleichen Zeitpunkt."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.WhiteNote import WhiteNote, TOP_TREBLE, TOP_BASS
from musiai.ui.midi.Stem import Stem, UP, DOWN
from musiai.ui.midi.ClefSymbol import TREBLE
from musiai.ui.midi import NoteDuration as ND


class NoteData:
    """Daten einer einzelnen Note im Akkord."""
    __slots__ = ('midi_note', 'whitenote', 'duration', 'left_side', 'accid')

    def __init__(self, midi_note: int, whitenote: WhiteNote,
                 duration: int, left_side: bool = True, accid: int = 0):
        self.midi_note = midi_note
        self.whitenote = whitenote
        self.duration = duration
        self.left_side = left_side
        self.accid = accid


class ChordSymbol(MusicSymbol):
    """Gruppe von Noten die gleichzeitig erklingen."""

    def __init__(self, notes: list[NoteData], clef: int = TREBLE,
                 start_time: int = 0):
        super().__init__(start_time)
        self.notes = sorted(notes, key=lambda n: n.whitenote.to_midi())
        self.clef = clef
        self._resolve_overlaps()
        self.stem = self._create_stem() if notes else None

    @property
    def min_width(self) -> int:
        nh = 8
        base = 2 * nh + nh * 3 // 4
        return base

    @property
    def above_staff(self) -> int:
        if not self.notes:
            return 0
        top = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        nh = 8
        dist = top.dist(self.notes[-1].whitenote)
        if dist < 0:
            return abs(dist) * nh // 2
        return 0

    @property
    def below_staff(self) -> int:
        if not self.notes:
            return 0
        from musiai.ui.midi.WhiteNote import BOTTOM_TREBLE, BOTTOM_BASS
        bottom = BOTTOM_TREBLE if self.clef == TREBLE else BOTTOM_BASS
        nh = 8
        dist = self.notes[0].whitenote.dist(bottom)
        if dist < 0:
            return abs(dist) * nh // 2
        return 0

    def _resolve_overlaps(self) -> None:
        """Benachbarte Noten abwechselnd links/rechts positionieren."""
        for i in range(1, len(self.notes)):
            prev = self.notes[i - 1]
            curr = self.notes[i]
            if abs(curr.whitenote.dist(prev.whitenote)) == 1:
                curr.left_side = not prev.left_side
            else:
                curr.left_side = True

    def _create_stem(self) -> Stem | None:
        if not self.notes:
            return None
        bottom = self.notes[0].whitenote
        top = self.notes[-1].whitenote
        duration = self.notes[0].duration
        direction = self._stem_direction(bottom, top)
        overlap = any(not n.left_side for n in self.notes)
        return Stem(bottom, top, duration, direction, overlap)

    def _stem_direction(self, bottom: WhiteNote, top: WhiteNote) -> int:
        """Stem-Richtung: Durchschnitt vom Mittelpunkt."""
        from musiai.ui.midi.WhiteNote import WhiteNote as WN, B
        if self.clef == TREBLE:
            middle = WN(B, 5)
        else:
            from musiai.ui.midi.WhiteNote import D
            middle = WN(D, 3)
        dist = middle.dist(bottom) + middle.dist(top)
        return UP if dist >= 0 else DOWN

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor, QBrush
        from PySide6.QtCore import Qt
        nh = config.get('note_height', 8)
        nw = config.get('note_width', 10)

        top = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        color = config.get('note_color', QColor(200, 60, 30))

        for nd in self.notes:
            ny = ytop + top.dist(nd.whitenote) * nh // 2
            nx = x + (0 if nd.left_side else nw)

            # Notenkopf (ausgefüllte Ellipse)
            painter.setPen(QPen(color.darker(120), 1))
            if nd.duration in (ND.WHOLE, ND.HALF, ND.DOTTED_HALF):
                painter.setBrush(QBrush(Qt.GlobalColor.transparent))
            else:
                painter.setBrush(QBrush(color))
            painter.drawEllipse(nx, ny - nh // 2, nw, nh)

            # Hilfslinien
            self._draw_ledger_lines(painter, nd.whitenote, nx, nw, ytop, config)

        # Stem
        if self.stem:
            self.stem.draw(painter, x, ytop, config, top)

    def _draw_ledger_lines(self, painter, note: WhiteNote,
                           nx: int, nw: int, ytop: int,
                           config: dict) -> None:
        from PySide6.QtGui import QPen, QColor
        nh = config.get('note_height', 8)
        top = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        from musiai.ui.midi.WhiteNote import BOTTOM_TREBLE, BOTTOM_BASS
        bottom = BOTTOM_TREBLE if self.clef == TREBLE else BOTTOM_BASS

        pen = QPen(QColor(60, 60, 80), 1)
        painter.setPen(pen)

        # Über dem System
        if note.dist(top) > 1:
            pos = top.add(2)
            while pos.dist(note) <= 0:
                ly = ytop + top.dist(pos) * nh // 2
                painter.drawLine(nx - 4, ly, nx + nw + 4, ly)
                pos = pos.add(2)

        # Unter dem System
        if bottom.dist(note) > 1:
            pos = bottom.add(-2)
            while note.dist(pos) <= 0:
                ly = ytop + top.dist(pos) * nh // 2
                painter.drawLine(nx - 4, ly, nx + nw + 4, ly)
                pos = pos.add(-2)
