"""BarSymbol - Taktstrich (portiert von BarSymbol.java)."""

from musiai.ui.midi.MusicSymbol import MusicSymbol


class BarSymbol(MusicSymbol):
    """Vertikaler Taktstrich."""

    def __init__(self, start_time: int):
        super().__init__(start_time)
        self._width = self.min_width

    @property
    def min_width(self) -> int:
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        return 2 * SC.LineSpace

    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        from PySide6.QtGui import QPen, QColor
        from musiai.ui.midi.SheetConfig import SheetConfig as SC
        nw = SC.NoteWidth
        ls = SC.LineSpace
        lw = SC.LineWidth

        use_bravura = (config.get('use_bravura', False)
                       if isinstance(config, dict) else False)
        if use_bravura:
            from musiai.ui.midi.SMuFLMetadata import SMuFLMetadata
            fs = SMuFLMetadata.notehead_font_size(ls)
            sc = SMuFLMetadata.font_scale(fs)
            bar_thick = SMuFLMetadata.get_engraving_default(
                'thinBarlineThickness', 0.16)
            bar_w = max(1, int(bar_thick * sc + 0.5))
        else:
            bar_w = 1
        pen = QPen(QColor(0, 0, 0), bar_w)
        painter.setPen(pen)
        bx = x + nw // 2
        ystart = ytop - lw
        yend = ytop - lw + 4 * (lw + ls)
        painter.drawLine(bx, ystart, bx, yend)
