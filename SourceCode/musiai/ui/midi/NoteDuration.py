"""NoteDuration - Notentypen und Dauer-Klassifikation."""

# NoteDuration Enum (aufsteigend nach Dauer)
SIXTYFOURTH = -1
THIRTYSECOND = 0
SIXTEENTH = 1
TRIPLET = 2
EIGHTH = 3
DOTTED_EIGHTH = 4
QUARTER = 5
DOTTED_QUARTER = 6
HALF = 7
DOTTED_HALF = 8
WHOLE = 9

# Beambare Dauern
BEAMABLE = {SIXTYFOURTH, THIRTYSECOND, SIXTEENTH, TRIPLET, EIGHTH, DOTTED_EIGHTH}

# Balken-Anzahl pro Typ
BEAM_COUNT = {
    EIGHTH: 1, DOTTED_EIGHTH: 1, TRIPLET: 1,
    SIXTEENTH: 2, THIRTYSECOND: 3, SIXTYFOURTH: 4,
}


# Exact beat values for each duration (quarter note = 1.0 beat)
BEATS = {
    WHOLE: 4.0,
    DOTTED_HALF: 3.0,
    HALF: 2.0,
    DOTTED_QUARTER: 1.5,
    QUARTER: 1.0,
    DOTTED_EIGHTH: 0.75,
    EIGHTH: 0.5,
    TRIPLET: 1.0 / 3.0,
    SIXTEENTH: 0.25,
    THIRTYSECOND: 0.125,
    SIXTYFOURTH: 0.0625,
}

# Sorted from longest to shortest for nearest-match lookup
_SORTED_DURATIONS = sorted(BEATS.items(), key=lambda x: -x[1])

_TOL = 0.05  # tolerance for exact matching


def from_beats(beats: float) -> int:
    """Beat-Dauer → NoteDuration (Viertelnote = 1.0 Beat).

    Uses exact matching with a small tolerance. Falls back to nearest
    standard duration if no exact match is found.
    """
    # Exact match first
    for dur, val in _SORTED_DURATIONS:
        if abs(beats - val) < _TOL:
            return dur
    # Fallback: nearest standard duration
    best_dur = THIRTYSECOND
    best_diff = abs(beats - BEATS[THIRTYSECOND])
    for dur, val in _SORTED_DURATIONS:
        diff = abs(beats - val)
        if diff < best_diff:
            best_diff = diff
            best_dur = dur
    return best_dur


def to_beats(dur: int) -> float:
    """NoteDuration → beat length (quarter note = 1.0)."""
    return BEATS.get(dur, 0.25)


def is_standard(beats: float) -> bool:
    """Return True if *beats* matches a standard NoteDuration exactly."""
    for val in BEATS.values():
        if abs(beats - val) < _TOL:
            return True
    return False


def split_complex(beats: float) -> list[float]:
    """Split a non-standard (complex) beat duration into standard parts.

    Returns a list of beat values that sum to *beats*, each one a
    standard NoteDuration value, ordered longest-first.  Used for tied
    note representation of complex durations like 1.25 = 1.0 + 0.25.
    """
    if is_standard(beats):
        return [beats]

    parts: list[float] = []
    remaining = beats
    for _dur, val in _SORTED_DURATIONS:
        while remaining - val >= -_TOL and val > _TOL:
            parts.append(val)
            remaining -= val
            if abs(remaining) < _TOL:
                remaining = 0.0
                break
        if remaining <= _TOL:
            break
    return parts if parts else [beats]


def name(dur: int) -> str:
    """Lesbare Bezeichnung."""
    names = {
        SIXTYFOURTH: "64th", THIRTYSECOND: "32nd", SIXTEENTH: "16th",
        TRIPLET: "Triplet", EIGHTH: "8th", DOTTED_EIGHTH: "Dotted 8th",
        QUARTER: "Quarter", DOTTED_QUARTER: "Dotted Quarter", HALF: "Half",
        DOTTED_HALF: "Dotted Half", WHOLE: "Whole",
    }
    return names.get(dur, "?")
