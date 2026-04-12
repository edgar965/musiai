"""NotationScene - QGraphicsScene die das gesamte Stück rendert."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QColor, QPen
from musiai.model.Piece import Piece
from musiai.notation.MeasureRenderer import MeasureRenderer
from musiai.notation.PlayheadItem import PlayheadItem
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

    def set_piece(self, piece: Piece) -> None:
        """Piece setzen und komplett rendern."""
        logger.info(f"Rendere Piece: '{piece.title}'")
        self.piece = piece
        self.refresh()

    def refresh(self) -> None:
        """Komplettes Neuzeichnen."""
        # Playhead merken und wieder einfügen
        self.removeItem(self.playhead)
        self.clear()
        self.measure_renderers.clear()
        self.addItem(self.playhead)

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

            for i, measure in enumerate(part.measures):
                show_clef = (i == 0)
                tempo = self.piece.initial_tempo if i == 0 else 0
                vel = first_vel if i == 0 else 0
                renderer = MeasureRenderer(
                    measure, x_offset, center_y, show_clef, tempo, vel
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

        # Playhead-Bereich setzen
        self.playhead.set_y_range(self.MARGIN_TOP, center_y)

        # Scene-Rect
        self.setSceneRect(0, 0, total_width + 60, center_y + 40)
        logger.info(f"Scene gerendert: {len(self.measure_renderers)} Takte")

    def update_playhead(self, beat: float) -> None:
        """Playhead an Beat-Position setzen."""
        x = self.MARGIN_LEFT + beat * PIXELS_PER_BEAT + PIXELS_PER_BEAT / 2
        self.playhead.show_at(x)

    def hide_playhead(self) -> None:
        self.playhead.hide()

    def get_note_item_at(self, scene_pos) -> NoteItem | None:
        """NoteItem unter einer Scene-Position finden."""
        for item in self.items(scene_pos):
            if isinstance(item, NoteItem):
                return item
        return None

    def get_all_note_items(self) -> list[NoteItem]:
        """Alle NoteItems in der Scene."""
        return [item for item in self.items() if isinstance(item, NoteItem)]
