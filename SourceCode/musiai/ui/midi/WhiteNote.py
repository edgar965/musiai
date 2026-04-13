"""WhiteNote - Diatonische Notenposition (portiert von MusicExplorer)."""

# Noten-Buchstaben (wie im C# Original)
A, B, C, D, E, F, G = 0, 1, 2, 3, 4, 5, 6

# NoteScale: Chromatische Halbton-Offsets (A=0, A#=1, B=2, C=3, ...)
_NOTESCALE = {A: 0, B: 2, C: 3, D: 5, E: 7, F: 8, G: 10}


class NoteScale:
    """Chromatische Skala (portiert von NoteScale in C#)."""
    A = 0; Asharp = 1; Bflat = 1; B = 2; C = 3
    Csharp = 4; Dflat = 4; D = 5; Dsharp = 6; Eflat = 6
    E = 7; F = 8; Fsharp = 9; Gflat = 9; G = 10
    Gsharp = 11; Aflat = 11

    @staticmethod
    def to_number(notescale: int, octave: int) -> int:
        return 9 + notescale + octave * 12

    @staticmethod
    def from_number(number: int) -> int:
        return (number + 3) % 12

    @staticmethod
    def is_black_key(notescale: int) -> bool:
        return notescale in (1, 4, 6, 9, 11)


class WhiteNote:
    """Diatonische Note mit Buchstabe (A-G) und Oktave."""

    __slots__ = ('letter', 'octave')

    def __init__(self, letter: int, octave: int):
        assert 0 <= letter <= 6, f"Letter {letter} is incorrect"
        self.letter = letter
        self.octave = octave

    def dist(self, other: 'WhiteNote') -> int:
        """Abstand in weissen Noten: self - other."""
        return (self.octave - other.octave) * 7 + (self.letter - other.letter)

    def add(self, amount: int) -> 'WhiteNote':
        """Neue Note um amount weisse Noten verschoben."""
        num = self.octave * 7 + self.letter + amount
        num = max(0, num)
        return WhiteNote(num % 7, num // 7)

    def number(self) -> int:
        """MIDI-Notennummer (C4=60)."""
        return NoteScale.to_number(_NOTESCALE[self.letter], self.octave)

    def to_midi(self) -> int:
        """Alias fuer number()."""
        return self.number()

    @staticmethod
    def from_midi(midi_note: int) -> 'WhiteNote':
        """MIDI-Notennummer -> naechste weisse Note."""
        adjusted = midi_note - 9  # A0 = MIDI 21
        octave = adjusted // 12
        remainder = adjusted % 12
        best_letter = 0
        best_dist = 99
        for letter, offset in _NOTESCALE.items():
            d = abs(offset - remainder)
            if d < best_dist:
                best_dist = d
                best_letter = letter
        return WhiteNote(best_letter, octave)

    @staticmethod
    def top(clef: int) -> 'WhiteNote':
        """Oberste Note des Notensystems fuer den Schluessel."""
        if clef == 0:  # TREBLE
            return TOP_TREBLE
        return TOP_BASS

    @staticmethod
    def bottom(clef: int) -> 'WhiteNote':
        """Unterste Note des Notensystems."""
        if clef == 0:  # TREBLE
            return BOTTOM_TREBLE
        return BOTTOM_BASS

    @staticmethod
    def max(a: 'WhiteNote', b: 'WhiteNote') -> 'WhiteNote':
        return a if a.dist(b) > 0 else b

    @staticmethod
    def min(a: 'WhiteNote', b: 'WhiteNote') -> 'WhiteNote':
        return a if a.dist(b) < 0 else b

    def __repr__(self) -> str:
        names = "ABCDEFG"
        return f"{names[self.letter]}{self.octave}"

    def __eq__(self, other):
        if not isinstance(other, WhiteNote):
            return False
        return self.letter == other.letter and self.octave == other.octave

    def __hash__(self):
        return hash((self.letter, self.octave))


# Standard-Positionen (exakt wie C#)
MIDDLE_C = WhiteNote(C, 4)
TOP_TREBLE = WhiteNote(E, 5)
BOTTOM_TREBLE = WhiteNote(F, 4)
TOP_BASS = WhiteNote(G, 3)
BOTTOM_BASS = WhiteNote(A, 3)
