"""NoteDuration - Notentypen und Dauer-Klassifikation."""

# NoteDuration Enum (aufsteigend nach Dauer)
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
BEAMABLE = {THIRTYSECOND, SIXTEENTH, TRIPLET, EIGHTH, DOTTED_EIGHTH}

# Balken-Anzahl pro Typ
BEAM_COUNT = {
    EIGHTH: 1, DOTTED_EIGHTH: 1, TRIPLET: 1,
    SIXTEENTH: 2, THIRTYSECOND: 3,
}


def from_beats(beats: float) -> int:
    """Beat-Dauer → NoteDuration (Viertelnote = 1.0 Beat)."""
    whole = 4.0
    if beats >= 28 * whole / 32:
        return WHOLE
    if beats >= 20 * whole / 32:
        return DOTTED_HALF
    if beats >= 14 * whole / 32:
        return HALF
    if beats >= 10 * whole / 32:
        return DOTTED_QUARTER
    if beats >= 7 * whole / 32:
        return QUARTER
    if beats >= 5 * whole / 32:
        return DOTTED_EIGHTH
    if beats >= 6 * whole / 64:
        return EIGHTH
    if beats >= 5 * whole / 64:
        return TRIPLET
    if beats >= 3 * whole / 64:
        return SIXTEENTH
    return THIRTYSECOND


def name(dur: int) -> str:
    """Lesbare Bezeichnung."""
    names = {
        THIRTYSECOND: "32nd", SIXTEENTH: "16th", TRIPLET: "Triplet",
        EIGHTH: "8th", DOTTED_EIGHTH: "Dotted 8th", QUARTER: "Quarter",
        DOTTED_QUARTER: "Dotted Quarter", HALF: "Half",
        DOTTED_HALF: "Dotted Half", WHOLE: "Whole",
    }
    return names.get(dur, "?")
