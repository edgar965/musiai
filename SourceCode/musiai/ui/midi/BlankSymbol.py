"""BlankSymbol - Unsichtbarer Platzhalter für Alignment."""

from musiai.ui.midi.MusicSymbol import MusicSymbol


class BlankSymbol(MusicSymbol):
    """Unsichtbar — füllt Lücken bei vertikaler Ausrichtung."""

    def __init__(self, start_time: int, width: int = 0):
        super().__init__(start_time)
        self._width = width

    @property
    def min_width(self) -> int:
        return 0

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        pass  # Nichts zeichnen
