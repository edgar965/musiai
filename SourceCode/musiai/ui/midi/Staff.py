"""Staff - Eine Zeile im Notenblatt mit Schlüssel und Noten."""

import logging
from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.ClefSymbol import ClefSymbol, TREBLE, BASS
from musiai.ui.midi.WhiteNote import WhiteNote, TOP_TREBLE, TOP_BASS

logger = logging.getLogger("musiai.ui.midi.Staff")


class Staff:
    """Rendert eine Zeile: Schlüssel + Symbole + 5 Notenlinien."""

    def __init__(self, symbols: list[MusicSymbol], clef: int = TREBLE,
                 track_num: int = 0, total_tracks: int = 1):
        self.symbols = symbols
        self.clef = clef
        self.track_num = track_num
        self.total_tracks = total_tracks
        self.ytop = 0
        self.height = 0
        self.width = 0

    @property
    def top_note(self) -> WhiteNote:
        return TOP_TREBLE if self.clef == TREBLE else TOP_BASS

    def calculate_layout(self, config: dict) -> None:
        """Höhe und Abstände berechnen."""
        ls = config.get('line_space', 12)
        nh = config.get('note_height', 12)
        staff_h = 4 * ls  # 5 Linien, 4 Zwischenräume

        # Platz über/unter dem System für Noten mit Hilfslinien
        max_above = 0
        max_below = 0
        for sym in self.symbols:
            max_above = max(max_above, sym.above_staff)
            max_below = max(max_below, sym.below_staff)

        # Minimum Platz über System für Taktnummern
        max_above = max(max_above, nh * 2)

        self.ytop = max_above + nh
        self.height = staff_h + self.ytop + max_below + nh * 2
        if self.track_num == self.total_tracks - 1:
            self.height += nh * 2  # Extra Platz nach letztem Track

    def draw(self, painter, y_offset: int, config: dict) -> None:
        """Komplette Zeile zeichnen."""
        from PySide6.QtGui import QPen, QColor, QFont
        ls = config.get('line_space', 12)
        nh = config.get('note_height', 12)
        nw = config.get('note_width', 15)
        lw = config.get('line_width', 1)

        if self.height == 0:
            self.calculate_layout(config)

        ytop = y_offset + self.ytop
        staff_h = 4 * ls

        # Schlüssel zeichnen
        clef_sym = ClefSymbol(self.clef)
        clef_sym.draw(painter, 4, ytop, config)
        clef_width = clef_sym.min_width + 4

        # Symbole zeichnen
        x = clef_width + 8
        for sym in self.symbols:
            sym.draw(painter, x, ytop, config)
            w = sym.width if sym.width > 0 else sym.min_width
            x += w

        self.width = max(x, 200)

        # 5 Notenlinien
        pen = QPen(QColor(80, 80, 100), lw)
        painter.setPen(pen)
        for i in range(5):
            line_y = ytop + i * ls
            painter.drawLine(clef_width, line_y, self.width, line_y)

        # Rand-Striche links und rechts
        pen2 = QPen(QColor(60, 60, 80), 1.5)
        painter.setPen(pen2)
        painter.drawLine(clef_width, ytop, clef_width, ytop + staff_h)
        painter.drawLine(self.width, ytop, self.width, ytop + staff_h)
