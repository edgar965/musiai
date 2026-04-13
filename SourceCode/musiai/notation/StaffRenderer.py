"""StaffRenderer - Zeichnet die 5 Notenlinien."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsLineItem
from PySide6.QtGui import QPen, QColor
from musiai.util.Constants import STAFF_LINE_COUNT, STAFF_LINE_SPACING, COLOR_STAFF_LINE

logger = logging.getLogger("musiai.notation.StaffRenderer")


class StaffRenderer:
    """Zeichnet die Notenlinien (5 Linien) in die Scene."""

    @staticmethod
    def draw_staff_lines(
        scene: QGraphicsScene,
        x_start: float,
        width: float,
        center_y: float,
        color: QColor | None = None,
    ) -> list[QGraphicsLineItem]:
        """Zeichnet 5 Notenlinien zentriert um center_y."""
        lines = []
        pen = QPen(color or QColor(*COLOR_STAFF_LINE), 1)
        half = (STAFF_LINE_COUNT - 1) / 2.0

        for i in range(STAFF_LINE_COUNT):
            y = center_y + (i - half) * STAFF_LINE_SPACING
            line = scene.addLine(x_start, y, x_start + width, y, pen)
            line.setZValue(0)
            lines.append(line)

        return lines
