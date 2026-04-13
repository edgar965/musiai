"""Staff - Eine Zeile im Notenblatt mit Schlüssel und Noten."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.ClefSymbol import ClefSymbol, TREBLE, BASS
from musiai.ui.midi.WhiteNote import WhiteNote, TOP_TREBLE, TOP_BASS


class Staff:
    """Rendert eine Zeile: Schlüssel + Symbole + Notenlinien."""

    def __init__(self, symbols: list[MusicSymbol], clef: int = TREBLE,
                 measure_length: int = 0, track_num: int = 0,
                 total_tracks: int = 1):
        self.symbols = symbols
        self.clef = clef
        self.measure_length = measure_length
        self.track_num = track_num
        self.total_tracks = total_tracks
        self.ytop = 0
        self.height = 0
        self.width = 0
        self._calculate_height()

    def _calculate_height(self) -> None:
        """Höhe basierend auf Symbolen berechnen."""
        max_above = 0
        max_below = 0
        for sym in self.symbols:
            max_above = max(max_above, sym.above_staff)
            max_below = max(max_below, sym.below_staff)

        nh = 8  # NoteHeight default
        self.ytop = max(max_above, nh * 3) + nh
        self.height = 5 * nh + self.ytop + max_below
        if self.track_num == self.total_tracks - 1:
            self.height += 3 * nh

    @property
    def top_note(self) -> WhiteNote:
        return TOP_TREBLE if self.clef == TREBLE else TOP_BASS

    def draw(self, painter, y_offset: int, config: dict) -> None:
        """Komplette Zeile zeichnen."""
        from PySide6.QtGui import QPen, QColor
        nh = config.get('note_height', 8)
        ls = config.get('line_space', 7)
        lw = config.get('line_width', 1)

        ytop = y_offset + self.ytop

        # Schlüssel
        clef_sym = ClefSymbol(self.clef)
        clef_sym.draw(painter, 4, ytop, config)
        clef_width = clef_sym.min_width

        # Symbole zeichnen
        x = clef_width + 8
        for sym in self.symbols:
            sym.draw(painter, x, ytop, config)
            x += sym.width

        self.width = x

        # 5 Notenlinien
        pen = QPen(QColor(80, 80, 100), lw)
        painter.setPen(pen)
        for i in range(5):
            line_y = ytop + i * (ls + lw)
            painter.drawLine(0, line_y, self.width, line_y)

        # Endstrich
        painter.drawLine(0, ytop, 0, ytop + 4 * ls + 4 * lw)
        painter.drawLine(self.width, ytop, self.width, ytop + 4 * ls + 4 * lw)
