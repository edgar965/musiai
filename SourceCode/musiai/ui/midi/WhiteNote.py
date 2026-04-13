"""WhiteNote - Diatonische Notenposition (portiert von MusicExplorer)."""

# Noten-Buchstaben
A, B, C, D, E, F, G = 0, 1, 2, 3, 4, 5, 6

# MIDI-Offset pro Buchstabe (A=0, B=2, C=3, D=5, E=7, F=8, G=10)
_NOTE_OFFSETS = [0, 2, 3, 5, 7, 8, 10]

# Standard-Positionen
MIDDLE_C = None  # Wird nach Klassendefiniton gesetzt


class WhiteNote:
    """Diatonische Note mit Buchstabe (A-G) und Oktave."""

    __slots__ = ('letter', 'octave')

    def __init__(self, letter: int, octave: int):
        self.letter = letter  # 0=A, 1=B, 2=C, 3=D, 4=E, 5=F, 6=G
        self.octave = octave

    def dist(self, other: 'WhiteNote') -> int:
        """Abstand in weißen Noten (positiv = höher)."""
        return (self.octave - other.octave) * 7 + (self.letter - other.letter)

    def add(self, amount: int) -> 'WhiteNote':
        """Neue Note um amount weiße Noten verschoben."""
        num = self.octave * 7 + self.letter + amount
        num = max(0, num)
        return WhiteNote(num % 7, num // 7)

    def to_midi(self) -> int:
        """Konvertiert zu MIDI-Notennummer."""
        return 9 + _NOTE_OFFSETS[self.letter] + self.octave * 12

    @staticmethod
    def from_midi(midi_note: int) -> 'WhiteNote':
        """MIDI-Notennummer → WhiteNote (nächste weiße Note)."""
        # MIDI to octave+offset
        adjusted = midi_note - 9  # A0 = MIDI 21, offset 0
        octave = adjusted // 12
        remainder = adjusted % 12
        # Finde nächsten Buchstaben
        best_letter = 0
        best_dist = 99
        for i, off in enumerate(_NOTE_OFFSETS):
            d = abs(off - remainder)
            if d < best_dist:
                best_dist = d
                best_letter = i
        return WhiteNote(best_letter, octave)

    @staticmethod
    def max(a: 'WhiteNote', b: 'WhiteNote') -> 'WhiteNote':
        return a if a.dist(b) >= 0 else b

    @staticmethod
    def min(a: 'WhiteNote', b: 'WhiteNote') -> 'WhiteNote':
        return a if a.dist(b) <= 0 else b

    def __repr__(self) -> str:
        names = "ABCDEFG"
        return f"{names[self.letter]}{self.octave}"

    def __eq__(self, other):
        return isinstance(other, WhiteNote) and self.letter == other.letter and self.octave == other.octave

    def __hash__(self):
        return hash((self.letter, self.octave))


# Standard-Positionen
MIDDLE_C = WhiteNote(C, 4)
TOP_TREBLE = WhiteNote(E, 5)
BOTTOM_TREBLE = WhiteNote(F, 4)
TOP_BASS = WhiteNote(G, 3)
BOTTOM_BASS = WhiteNote(A, 3)
