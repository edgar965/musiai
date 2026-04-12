"""NotationScene - QGraphicsScene die das gesamte Stück rendert."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QColor, QPen
from musiai.model.Piece import Piece
from musiai.notation.MeasureRenderer import MeasureRenderer
from musiai.notation.PlayheadItem import PlayheadItem
from musiai.notation.CursorItem import CursorItem
from musiai.notation.NoteItem import NoteItem
from musiai.util.Constants import COLOR_BACKGROUND, PIXELS_PER_BEAT

logger = logging.getLogger("musiai.notation.NotationScene")


class NotationScene(QGraphicsScene):
    """Scene die ein Piece als farbige Notation rendert."""

    MARGIN_LEFT = 40
    MARGIN_TOP = 80

    def __init__(self):
        super().__init__()
        self.setBackgroundBrush(QColor(*COLOR_BACKGROUND))
        self.piece: Piece | None = None
        self.measure_renderers: list[MeasureRenderer] = []
        self.playhead = PlayheadItem()
        self.addItem(self.playhead)
        self.cursor = CursorItem()
        self.addItem(self.cursor)

    def set_piece(self, piece: Piece) -> None:
        """Piece setzen und komplett rendern."""
        logger.info(f"Rendere Piece: '{piece.title}'")
        self.piece = piece
        self.refresh()

    def refresh(self) -> None:
        """Komplettes Neuzeichnen."""
        # Playhead + Cursor merken und wieder einfügen
        self.removeItem(self.playhead)
        self.removeItem(self.cursor)
        self.clear()
        self.measure_renderers.clear()
        self._measure_highlight = None  # wurde durch clear() gelöscht
        self.addItem(self.playhead)
        self.addItem(self.cursor)

        if not self.piece or not self.piece.parts:
            return

        center_y = self.MARGIN_TOP + 60
        total_width = self.MARGIN_LEFT

        for part_idx, part in enumerate(self.piece.parts):
            x_offset = self.MARGIN_LEFT

            # Standard-Velocity aus erster Note ermitteln
            first_vel = 80
            if part.measures and part.measures[0].notes:
                first_vel = part.measures[0].notes[0].expression.velocity

            # Tempo pro Takt bestimmen
            current_tempo = self.piece.initial_tempo

            for i, measure in enumerate(part.measures):
                # Per-Takt-Tempo (falls Tempowechsel)
                if measure.tempo:
                    current_tempo = measure.tempo.bpm

                show_clef = (i == 0)
                display_tempo = current_tempo if i == 0 else 0
                vel = first_vel if i == 0 else 0
                renderer = MeasureRenderer(
                    measure, x_offset, center_y, show_clef,
                    display_tempo, vel, current_tempo
                )
                renderer.render(self)
                self.measure_renderers.append(renderer)
                x_offset += renderer.width

            # Schlusstaktstrich
            pen = QPen(QColor(100, 100, 120), 3)
            staff_half = 24
            self.addLine(x_offset, center_y - staff_half,
                        x_offset, center_y + staff_half, pen)

            total_width = max(total_width, x_offset)
            center_y += 150

        # Playhead + Cursor Bereich setzen
        self.playhead.set_y_range(self.MARGIN_TOP, center_y)
        self.cursor.set_y_range(self.MARGIN_TOP, center_y)

        # Scene-Rect
        self.setSceneRect(0, 0, total_width + 60, center_y + 40)
        logger.info(f"Scene gerendert: {len(self.measure_renderers)} Takte")

    def beat_to_x(self, global_beat: float) -> float:
        """Globaler Beat → Scene-X-Koordinate (berücksichtigt Tempo pro Takt)."""
        if not self.measure_renderers:
            return self.MARGIN_LEFT + global_beat * PIXELS_PER_BEAT
        cumulative_beat = 0.0
        for r in self.measure_renderers:
            dur = r.measure.duration_beats
            if global_beat < cumulative_beat + dur:
                local = global_beat - cumulative_beat
                return r.x_offset + r.header_width + local * r.pixels_per_beat
            cumulative_beat += dur
        # Hinter dem letzten Takt
        last = self.measure_renderers[-1]
        overshoot = global_beat - cumulative_beat
        return last.x_offset + last.width + overshoot * last.pixels_per_beat

    def x_to_beat(self, x: float) -> float:
        """Scene-X-Koordinate → globaler Beat (berücksichtigt Tempo pro Takt)."""
        if not self.measure_renderers:
            return max(0.0, (x - self.MARGIN_LEFT) / PIXELS_PER_BEAT)
        cumulative_beat = 0.0
        for r in self.measure_renderers:
            content_start = r.x_offset + r.header_width
            content_end = r.x_offset + r.width
            if x < content_end:
                local_x = max(0.0, x - content_start)
                return cumulative_beat + local_x / r.pixels_per_beat
            cumulative_beat += r.measure.duration_beats
        return cumulative_beat

    def update_playhead(self, beat: float) -> None:
        """Playhead an Beat-Position setzen."""
        x = self.beat_to_x(beat)
        self.playhead.show_at(x)

    def hide_playhead(self) -> None:
        self.playhead.hide()

    def update_cursor(self, beat: float) -> None:
        """Edit-Cursor an globale Beat-Position setzen."""
        x = self.beat_to_x(beat)
        self.cursor.show_at(x)

    def hide_cursor(self) -> None:
        self.cursor.hide()

    def beat_at_x(self, x: float) -> float:
        """Alias für x_to_beat."""
        return self.x_to_beat(x)

    def highlight_measure(self, measure) -> None:
        """Takt visuell hervorheben mit blauem Hintergrund."""
        self.clear_measure_highlight()
        from PySide6.QtWidgets import QGraphicsRectItem
        from PySide6.QtGui import QBrush
        from musiai.util.Constants import STAFF_LINE_SPACING
        for renderer in self.measure_renderers:
            if renderer.measure is measure:
                sh = 2 * STAFF_LINE_SPACING + 6
                rect = QGraphicsRectItem(
                    renderer.x_offset, renderer.center_y - sh,
                    renderer.width, sh * 2
                )
                rect.setBrush(QBrush(QColor(0, 100, 255, 25)))
                rect.setPen(QPen(QColor(0, 100, 255, 80), 1.5))
                rect.setZValue(-1)
                self.addItem(rect)
                self._measure_highlight = rect
                return

    def clear_measure_highlight(self) -> None:
        if hasattr(self, '_measure_highlight') and self._measure_highlight:
            try:
                self.removeItem(self._measure_highlight)
            except RuntimeError:
                pass  # Already deleted by scene.clear()
            self._measure_highlight = None

    def get_note_item_at(self, scene_pos) -> NoteItem | None:
        """NoteItem unter einer Scene-Position finden."""
        for item in self.items(scene_pos):
            if isinstance(item, NoteItem):
                return item
        return None

    def get_all_note_items(self) -> list[NoteItem]:
        """Alle NoteItems in der Scene."""
        return [item for item in self.items() if isinstance(item, NoteItem)]
