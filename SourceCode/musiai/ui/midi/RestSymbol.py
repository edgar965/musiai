"""RestSymbol - Pausenzeichen."""

from musiai.ui.midi.MusicSymbol import MusicSymbol
from musiai.ui.midi import NoteDuration as ND


class RestSymbol(MusicSymbol):
    """Zeichnet Pausen (Ganze, Halbe, Viertel, Achtel)."""

    def __init__(self, start_time: int, duration: int):
        super().__init__(start_time)
        self.duration = duration

    @property
    def min_width(self) -> int:
        return 18

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor, QBrush, QFont
        nh = config.get('note_height', 8)
        nw = config.get('note_width', 10)
        color = QColor(40, 40, 60)
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))

        cx = x + nw

        if self.duration == ND.WHOLE:
            painter.fillRect(cx, ytop + nh, nw, nh // 2, color)
        elif self.duration == ND.HALF:
            painter.fillRect(cx, ytop + nh + nh // 2, nw, nh // 2, color)
        elif self.duration == ND.QUARTER:
            # Vereinfachtes Viertelpauesenzeichen
            painter.setFont(QFont("Segoe UI Symbol", 14))
            painter.drawText(cx - 2, ytop + nh - 2, "𝄾")
        else:
            # Achtel und kürzer: Punkt + Strich
            painter.setFont(QFont("Segoe UI Symbol", 14))
            painter.drawText(cx - 2, ytop + nh - 2, "𝄿")
