"""ChordDetector - Erkennt Akkorde aus gleichzeitigen Noten.

Portiert von MusicExplorer C# (NAudio.Chords). Normalisiert MIDI-Pitches
auf Intervall-Muster und vergleicht gegen bekannte Akkordpatterns.
"""

import logging
from collections import defaultdict

logger = logging.getLogger("musiai.notation.ChordDetector")

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class ChordDetector:
    """Erkennt Akkorde aus gleichzeitigen Noten."""

    # Chord patterns: tuple of semitone intervals from root -> suffix
    # Ported from MusicExplorer ChordPatterns + Chords.txt
    PATTERNS: dict[tuple[int, ...], str] = {
        # Triads
        (0, 4, 7):     "",       # Major
        (0, 3, 7):     "m",      # Minor
        (0, 3, 6):     "dim",    # Diminished
        (0, 4, 8):     "aug",    # Augmented
        (0, 5, 7):     "sus4",   # Suspended 4th
        (0, 2, 7):     "sus2",   # Suspended 2nd
        # Seventh chords
        (0, 4, 7, 10): "7",      # Dominant 7th
        (0, 4, 7, 11): "maj7",   # Major 7th
        (0, 3, 7, 10): "m7",     # Minor 7th
        (0, 3, 6, 10): "m7b5",   # Half-diminished 7th
        (0, 3, 6, 9):  "dim7",   # Diminished 7th
        (0, 3, 7, 11): "mMaj7",  # Minor-major 7th
        (0, 4, 8, 10): "aug7",   # Augmented 7th
        # Extended
        (0, 4, 7, 10, 14):  "9",     # Dominant 9th
        (0, 4, 7, 11, 14):  "maj9",  # Major 9th
        (0, 3, 7, 10, 14):  "m9",    # Minor 9th
        (0, 4, 7, 10, 13):  "7b9",   # Dominant 7th flat 9
        (0, 4, 7, 10, 15):  "7#9",   # Dominant 7th sharp 9
        # Sixth chords
        (0, 4, 7, 9):  "6",      # Major 6th
        (0, 3, 7, 9):  "m6",     # Minor 6th
        # Add chords
        (0, 4, 7, 14): "add9",   # Add 9
        (0, 3, 7, 14): "madd9",  # Minor add 9
        # Power chord
        (0, 7):         "5",      # Power chord
        # No-fifth variants (from Chords.txt)
        (0, 4):         "(no5)",  # Major no 5th
        (0, 3):         "m(no5)", # Minor no 5th
    }

    @staticmethod
    def detect(midi_pitches: list[int]) -> str | None:
        """Erkennt Akkordname aus MIDI-Pitches.

        Returns z.B. 'C', 'Am', 'G7', or None if not recognized.
        Tries each pitch as potential root (all inversions).
        """
        if len(midi_pitches) < 2:
            return None

        # Normalize: unique pitch classes, sorted
        pitch_classes = sorted(set(p % 12 for p in midi_pitches))
        if len(pitch_classes) < 2:
            return None

        # Try each pitch class as root
        best: str | None = None
        best_priority = 999

        for i, root in enumerate(pitch_classes):
            intervals = tuple(sorted((pc - root) % 12 for pc in pitch_classes))
            suffix = ChordDetector.PATTERNS.get(intervals)
            if suffix is not None:
                # Priority: root position (i==0) preferred, then fewer notes
                priority = i * 10 + len(intervals)
                if priority < best_priority:
                    best_priority = priority
                    note_name = NOTE_NAMES[root]
                    best = note_name + suffix

        return best

    @staticmethod
    def detect_for_measure(notes: list) -> list[tuple[float, str]]:
        """Erkennt Akkorde pro Beat-Position in einem Takt.

        Args:
            notes: Liste von Note-Objekten mit .start_beat und .pitch

        Returns:
            Liste von (start_beat, chord_name) Tupeln.
        """
        # Group notes by start_beat (quantized to nearest 0.25)
        groups: dict[float, list[int]] = defaultdict(list)
        for note in notes:
            beat = round(note.start_beat * 4) / 4
            groups[beat].append(note.pitch)

        results = []
        for beat in sorted(groups.keys()):
            pitches = groups[beat]
            if len(pitches) >= 2:
                chord = ChordDetector.detect(pitches)
                if chord:
                    results.append((beat, chord))
        return results
