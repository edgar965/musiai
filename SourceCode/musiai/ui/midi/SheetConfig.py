"""SheetConfig - Rendering-Konstanten (portiert von SheetControl static fields)."""


class SheetConfig:
    """Zentrale Konfiguration fuer die MIDI-Notenblatt-Darstellung.

    Class-level statics mirror the C# SheetControl constants.
    Use set_note_size() to toggle between large/small mode.
    """

    # Static constants (matching C# SheetControl)
    LineWidth = 1
    LeftMargin = 4
    PageWidth = 800

    # Dynamic statics (set by set_note_size)
    LineSpace = 7
    StaffHeight = 7 * 4 + 5
    NoteHeight = 7 + 1
    NoteWidth = 3 * 7 // 2

    # Private shortcuts used by other modules via SC._nh etc.
    _ls = 7
    _nh = 8
    _nw = 10
    _lw = 1

    @classmethod
    def set_note_size(cls, large: bool = False):
        """Set note sizes (matches C# SetNoteSize)."""
        if large:
            cls.LineSpace = 7
        else:
            cls.LineSpace = 5
        cls.StaffHeight = cls.LineSpace * 4 + cls.LineWidth * 5
        cls.NoteHeight = cls.LineSpace + cls.LineWidth
        cls.NoteWidth = 3 * cls.LineSpace // 2
        # Update shortcuts
        cls._ls = cls.LineSpace
        cls._nh = cls.NoteHeight
        cls._nw = cls.NoteWidth
        cls._lw = cls.LineWidth

    def __init__(self, line_space: int = 12):
        """Instance-level config for the Python renderer (larger default)."""
        self.line_width = 1
        self.left_margin = 4
        self.line_space = line_space
        self.staff_height = 4 * line_space
        self.note_height = line_space
        self.note_width = int(line_space * 1.3)
        self.page_width = 1100
        # Set class-level statics to match instance for drawing
        SheetConfig.LineSpace = line_space
        SheetConfig.NoteHeight = line_space + 1
        SheetConfig.NoteWidth = 3 * line_space // 2
        SheetConfig.StaffHeight = line_space * 4 + 5
        SheetConfig._ls = line_space
        SheetConfig._nh = line_space + 1
        SheetConfig._nw = 3 * line_space // 2
        SheetConfig._lw = 1

    @staticmethod
    def large() -> 'SheetConfig':
        return SheetConfig(line_space=12)

    @staticmethod
    def small() -> 'SheetConfig':
        return SheetConfig(line_space=8)

    @classmethod
    def key_signature_width(cls, key_accids: list) -> int:
        """Width needed for clef + key signature (like C# KeySignatureWidth)."""
        from musiai.ui.midi.ClefSymbol import ClefSymbol, TREBLE
        clefsym = ClefSymbol(TREBLE, 0, False)
        result = clefsym.min_width
        for accid_sym in key_accids:
            result += accid_sym.min_width
        return result + cls.LeftMargin + 5

    def to_dict(self) -> dict:
        """Config dict for draw() methods."""
        return {
            'note_height': self.note_height,
            'note_width': self.note_width,
            'line_space': self.line_space,
            'line_width': self.line_width,
            'staff_height': self.staff_height,
        }


# Initialize with default (small) note sizes
SheetConfig.set_note_size(False)
