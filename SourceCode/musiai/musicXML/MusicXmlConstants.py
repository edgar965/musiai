"""MusicXML-spezifische Konstanten."""

# Notennamen → Halbtöne über C
STEP_TO_SEMITONE = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}

# Dynamik-Bezeichnungen → Velocity-Werte
DYNAMICS_TO_VELOCITY = {
    "ppp": 16,
    "pp": 33,
    "p": 49,
    "mp": 64,
    "mf": 80,
    "f": 96,
    "ff": 112,
    "fff": 127,
}
