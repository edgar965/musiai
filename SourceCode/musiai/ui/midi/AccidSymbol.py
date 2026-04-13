"""AccidSymbol - Vorzeichen (Kreuz, Be, Auflösung)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi.WhiteNote import WhiteNote

NONE = 0
SHARP = 1
FLAT = 2
NATURAL = 3


class AccidSymbol(MusicSymbol):
    """Zeichnet ein Vorzeichen neben einer Note."""

    def __init__(self, accid: int, whitenote: WhiteNote, clef: int):
        super().__init__(0)
        self.accid = accid
        self.whitenote = whitenote
        self.clef = clef

    @property
    def min_width(self) -> int:
        return 9  # 3 * NoteHeight / 2

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor, QFont
        nh = config.get('note_height', 8)

        # Y-Position berechnen
        from musiai.ui.midi.WhiteNote import TOP_TREBLE, TOP_BASS
        from musiai.ui.midi.ClefSymbol import TREBLE
        top = TOP_TREBLE if self.clef == TREBLE else TOP_BASS
        y = ytop + top.dist(self.whitenote) * nh // 2

        painter.setPen(QPen(QColor(30, 30, 60), 1))
        symbols = {SHARP: "♯", FLAT: "♭", NATURAL: "♮"}
        text = symbols.get(self.accid, "")
        if text:
            painter.setFont(QFont("Arial", 10))
            painter.drawText(x, y - nh // 2, text)
