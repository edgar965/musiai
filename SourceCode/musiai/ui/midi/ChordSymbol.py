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
        return 22  # Ausreichend Platz für Notenkopf + Stem

    @property
    def above_staff(self) -> int:
        if not self.notes:
            return 0
        top = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        dist = top.dist(self.notes[-1].whitenote)
        if dist < 0:
            return abs(dist) * 6  # Pixel pro halber Linie
        return 0

    @property
    def below_staff(self) -> int:
        if not self.notes:
            return 0
        from musiai.ui.midi.WhiteNote import BOTTOM_TREBLE, BOTTOM_BASS
        bottom = BOTTOM_TREBLE if self.clef == TREBLE else BOTTOM_BASS
        dist = self.notes[0].whitenote.dist(bottom)
        if dist < 0:
            return abs(dist) * 6
        return 0

    def _resolve_overlaps(self) -> None:
        """Benachbarte Noten abwechselnd links/rechts positionieren."""
        for i in range(1, len(self.notes)):
            prev = self.notes[i - 1]
            curr = self.notes[i]
            if abs(curr.whitenote.dist(prev.whitenote)) == 1:
                curr.left_side = not prev.left_side

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
        from musiai.ui.midi.WhiteNote import WhiteNote as WN, B, D
        if self.clef == TREBLE:
            middle = WN(B, 5)
        else:
            middle = WN(D, 3)
        dist = middle.dist(bottom) + middle.dist(top)
        return UP if dist >= 0 else DOWN

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        """Noten zeichnen mit korrekter Y-Position relativ zum Staff."""
        from PySide6.QtGui import QPen, QColor, QBrush
        from PySide6.QtCore import Qt
        ls = config.get('line_space', 12)
        nh = config.get('note_height', 12)
        nw = config.get('note_width', 15)

        top_ref = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        color = config.get('note_color', QColor(200, 60, 30))
        half_space = ls / 2.0  # Pixel pro weiße Note

        for nd in self.notes:
            # Y = ytop + distance_from_top * half_space
            dist = top_ref.dist(nd.whitenote)
            ny = ytop + dist * half_space
            nx = x + (0 if nd.left_side else nw)

            # Notenkopf (ausgefüllte/offene Ellipse)
            painter.setPen(QPen(color.darker(130), 1.2))
            if nd.duration in (ND.WHOLE, ND.HALF, ND.DOTTED_HALF):
                painter.setBrush(QBrush(Qt.GlobalColor.transparent))
            else:
                painter.setBrush(QBrush(color))

            # Ellipse etwas schräg (wie echter Notenkopf)
            painter.drawEllipse(
                int(nx), int(ny - nh * 0.4),
                nw, int(nh * 0.8)
            )

            # Vorzeichen (♯ / ♭)
            if nd.accid == 1:  # SHARP
                from PySide6.QtGui import QFont
                painter.setFont(QFont("Arial", int(nh * 0.9)))
                painter.setPen(QPen(color, 1))
                painter.drawText(int(nx - nh), int(ny - nh * 0.3), "♯")
            elif nd.accid == 2:  # FLAT
                from PySide6.QtGui import QFont
                painter.setFont(QFont("Arial", int(nh * 0.9)))
                painter.setPen(QPen(color, 1))
                painter.drawText(int(nx - nh), int(ny - nh * 0.3), "♭")

            # Hilfslinien
            self._draw_ledger_lines(
                painter, nd.whitenote, nx, nw, ytop, ls, half_space
            )

        # Stem zeichnen
        if self.stem:
            self.stem.draw(painter, x, ytop, config, top_ref)

    def _draw_ledger_lines(self, painter, note: WhiteNote,
                           nx: float, nw: int, ytop: float,
                           ls: float, half_space: float) -> None:
        """Hilfslinien über/unter dem System."""
        from PySide6.QtGui import QPen, QColor
        top_ref = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        from musiai.ui.midi.WhiteNote import BOTTOM_TREBLE, BOTTOM_BASS
        bottom_ref = BOTTOM_TREBLE if self.clef == TREBLE else BOTTOM_BASS

        pen = QPen(QColor(60, 60, 80), 1)
        painter.setPen(pen)
        hw = 5  # Halbbreite der Hilfslinie

        # Über dem System
        if note.dist(top_ref) > 0:
            pos = top_ref.add(2)
            while pos.dist(note) <= 0:
                ly = ytop + top_ref.dist(pos) * half_space
                painter.drawLine(int(nx - hw), int(ly),
                                 int(nx + nw + hw), int(ly))
                pos = pos.add(2)

        # Unter dem System (bottom_ref ist 8 halbe Schritte unter top)
        bottom_dist = top_ref.dist(bottom_ref)  # positiv
        if top_ref.dist(note) > bottom_dist + 1:
            pos = bottom_ref.add(-2)
            while top_ref.dist(pos) <= top_ref.dist(note):
                ly = ytop + top_ref.dist(pos) * half_space
                painter.drawLine(int(nx - hw), int(ly),
                                 int(nx + nw + hw), int(ly))
                pos = pos.add(-2)
