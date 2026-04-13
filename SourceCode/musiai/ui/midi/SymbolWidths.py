"""SymbolWidths - Vertikale Ausrichtung ueber mehrere Spuren (portiert von SymbolWidths.cs)."""

from collections import defaultdict
from musiai.ui.midi.BarSymbol import BarSymbol


class SymbolWidths:
    """Berechnet maximale Breiten pro Startzeit fuer Track-Alignment."""

    def __init__(self, tracks: list[list]):
        self._widths: list[dict[int, int]] = []
        self._max_widths: dict[int, int] = defaultdict(int)
        self.start_times: list[int] = []

        if not tracks:
            return

        for track in tracks:
            tw = self._get_track_widths(track)
            self._widths.append(tw)
            for st, w in tw.items():
                self._max_widths[st] = max(self._max_widths[st], w)

        self.start_times = sorted(self._max_widths.keys())

    @staticmethod
    def _get_track_widths(symbols: list) -> dict[int, int]:
        """Breiten pro Startzeit fuer einen Track."""
        widths: dict[int, int] = defaultdict(int)
        for sym in symbols:
            if isinstance(sym, BarSymbol):
                continue
            widths[sym.start_time] += sym.min_width
        return widths

    def get_extra_width(self, track_idx: int, start_time: int) -> int:
        """Extra width needed for alignment."""
        if track_idx >= len(self._widths):
            return self._max_widths.get(start_time, 0)
        tw = self._widths[track_idx].get(start_time, 0)
        if tw == 0:
            return self._max_widths.get(start_time, 0)
        return self._max_widths.get(start_time, 0) - tw
