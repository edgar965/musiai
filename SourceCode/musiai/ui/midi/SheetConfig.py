"""SheetConfig - Rendering-Konstanten (portiert von SheetControl)."""


class SheetConfig:
    """Zentrale Konfiguration für die MIDI-Notenblatt-Darstellung."""

    def __init__(self, line_space: int = 7):
        self.line_width = 1
        self.left_margin = 4
        self.line_space = line_space
        self.staff_height = 4 * line_space + 5 * self.line_width
        self.note_height = line_space + self.line_width
        self.note_width = 3 * line_space // 2
        self.page_width = 1100

    @staticmethod
    def large() -> 'SheetConfig':
        return SheetConfig(line_space=7)

    @staticmethod
    def small() -> 'SheetConfig':
        return SheetConfig(line_space=5)
