"""ClefHelper - Automatische Schlüsselwahl und Referenzpositionen."""

import logging

logger = logging.getLogger("musiai.notation.ClefHelper")

# Schlüssel-Konstanten
TREBLE = "treble"
BASS = "bass"

# Referenz-Positionen (diatonische staff_pos für die Mitte des Systems)
# Treble: B4 (MIDI 71) auf der 3. Linie
# Bass: D3 (MIDI 50) auf der 3. Linie
_REF_PITCH = {TREBLE: 71, BASS: 50}

# Chromatic → Diatonic Mapping (C=0, D=1, E=2, F=3, G=4, A=5, B=6)
_CHROMATIC_TO_DIATONIC = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]


class ClefHelper:
    """Bestimmt den Schlüssel und berechnet Positionen."""

    @staticmethod
    def detect_clef(notes) -> str:
        """Schlüssel wählen der die wenigsten Hilfslinien braucht.

        Treble-System: Linien E4-F5 (MIDI 64-77), optimal für ~60-84
        Bass-System: Linien G2-A3 (MIDI 43-57), optimal für ~36-64
        """
        pitches = [n.pitch for n in notes if hasattr(n, 'pitch')]
        if not pitches:
            return TREBLE

        # Zähle Hilfslinien für beide Schlüssel
        treble_ledgers = sum(
            max(0, 64 - p) + max(0, p - 77) for p in pitches
        )
        bass_ledgers = sum(
            max(0, 43 - p) + max(0, p - 57) for p in pitches
        )
        return BASS if bass_ledgers < treble_ledgers else TREBLE

    @staticmethod
    def reference_pitch(clef: str) -> int:
        """MIDI-Pitch der Mittellinie für den Schlüssel."""
        return _REF_PITCH.get(clef, 71)

    @staticmethod
    def ref_staff_pos(clef: str) -> int:
        """Diatonische Staff-Position der Mittellinie."""
        p = ClefHelper.reference_pitch(clef)
        octave = p // 12
        pc = p % 12
        return octave * 7 + _CHROMATIC_TO_DIATONIC[pc]

    @staticmethod
    def clef_symbol(clef: str) -> str:
        """Unicode-Zeichen für den Schlüssel."""
        return "𝄞" if clef == TREBLE else "𝄢"

    @staticmethod
    def pitch_to_staff_pos(midi_pitch: int) -> int:
        """MIDI-Pitch → diatonische Staff-Position."""
        octave = midi_pitch // 12
        pc = midi_pitch % 12
        return octave * 7 + _CHROMATIC_TO_DIATONIC[pc]

    @staticmethod
    def needs_ledger_lines(midi_pitch: int, clef: str) -> tuple[bool, bool]:
        """Prüft ob Hilfslinien über/unter dem System nötig sind.

        Returns (above, below).
        """
        sp = ClefHelper.pitch_to_staff_pos(midi_pitch)
        ref = ClefHelper.ref_staff_pos(clef)
        # 5 Linien: ref-4 bis ref+4 (Abstände 2 diatonische Schritte)
        top_line = ref + 4
        bottom_line = ref - 4
        return sp > top_line + 1, sp < bottom_line - 1
