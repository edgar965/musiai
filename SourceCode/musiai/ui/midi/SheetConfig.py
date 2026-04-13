"""SheetConfig - Rendering-Konstanten (portiert von SheetControl)."""


class SheetConfig:
    """Zentrale Konfiguration für die MIDI-Notenblatt-Darstellung."""

    def __init__(self, line_space: int = 12):
        self.line_width = 1
        self.left_margin = 4
        self.line_space = line_space
        self.staff_height = 4 * line_space  # 5 Linien, 4 Zwischenräume
        self.note_height = line_space  # Höhe eines Notenkopfes
        self.note_width = int(line_space * 1.3)
        self.page_width = 1100

    @staticmethod
    def large() -> 'SheetConfig':
        return SheetConfig(line_space=12)

    @staticmethod
    def small() -> 'SheetConfig':
        return SheetConfig(line_space=8)
