"""WhiteNote - Diatonische Notenposition (portiert von MusicExplorer).

Standard-MIDI-Oktaven: C4 = MIDI 60, A4 = MIDI 69.
Buchstaben C-basiert: C=0, D=1, E=2, F=3, G=4, A=5, B=6.
"""

# Noten-Buchstaben (C-basiert, Standard-Oktaven)
C, D, E, F, G, A, B = 0, 1, 2, 3, 4, 5, 6

# Chromatische Halbton-Offsets ab C
_NOTESCALE = {C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11}


class NoteScale:
    """Chromatische Skala (C-basiert)."""
    C = 0; Csharp = 1; Dflat = 1; D = 2; Dsharp = 3; Eflat = 3
    E = 4; F = 5; Fsharp = 6; Gflat = 6; G = 7
    Gsharp = 8; Aflat = 8; A = 9; Asharp = 10; Bflat = 10; B = 11

    @staticmethod
    def to_number(notescale: int, octave: int) -> int:
        return 12 + notescale + octave * 12

    @staticmethod
    def from_number(number: int) -> int:
        return number % 12

    @staticmethod
    def is_black_key(notescale: int) -> bool:
        return notescale in (1, 3, 6, 8, 10)


class WhiteNote:
    """Diatonische Note mit Buchstabe (C-B) und Oktave."""

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
    def from_midi(midi_note: int, key_sharps: int = 0) -> 'WhiteNote':
        """MIDI-Notennummer -> WhiteNote basierend auf Tonart.

        key_sharps < 0: schwarze Tasten als Flats (Gb, Db, etc.)
        key_sharps > 0: schwarze Tasten als Sharps (F#, C#, etc.)
        key_sharps = 0: schwarze Tasten als Sharps (Default)
        """
        adjusted = midi_note - 12  # C0 = MIDI 12
        octave = adjusted // 12
        remainder = adjusted % 12

        if not NoteScale.is_black_key(remainder):
            # Weiße Taste: direkt aus Skala
            best_letter = 0
            best_dist = 99
            for letter, offset in _NOTESCALE.items():
                d = abs(offset - remainder)
                if d < best_dist:
                    best_dist = d
                    best_letter = letter
            return WhiteNote(best_letter, octave)

        if key_sharps < 0:
            _FLAT_MAP = {1: D, 3: E, 6: G, 8: A, 10: B}
            return WhiteNote(_FLAT_MAP[remainder], octave)
        else:
            _SHARP_MAP = {1: C, 3: D, 6: F, 8: G, 10: A}
            return WhiteNote(_SHARP_MAP[remainder], octave)


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
        names = "CDEFGAB"
        return f"{names[self.letter]}{self.octave}"

    def __eq__(self, other):
        if not isinstance(other, WhiteNote):
            return False
        return self.letter == other.letter and self.octave == other.octave

    def __hash__(self):
        return hash((self.letter, self.octave))


# Standard-Positionen (Standard-MIDI-Oktaven)
# Treble staff: bottom line E4, top line F5, top space above = E5 reference
# Bass staff: bottom line G2, top line A3, top space = G3 reference
MIDDLE_C = WhiteNote(C, 4)     # MIDI 60
TOP_TREBLE = WhiteNote(E, 5)   # MIDI 76
BOTTOM_TREBLE = WhiteNote(F, 4)  # MIDI 65
TOP_BASS = WhiteNote(G, 3)     # MIDI 55
BOTTOM_BASS = WhiteNote(A, 2)  # MIDI 45
