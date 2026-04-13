"""BravuraGlyphs - SMuFL Glyphen-Konstanten und Font-Loader."""

import os
from PySide6.QtGui import QFontDatabase

_loaded = False


def ensure_font():
    """Bravura Font einmalig laden."""
    global _loaded
    if _loaded:
        return
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..",
        "media", "fonts", "Bravura.otf"))
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)
    _loaded = True


FONT_NAME = "Bravura"

# Schlüssel
TREBLE_CLEF = "\uE050"
BASS_CLEF = "\uE062"

# Notenköpfe
NOTEHEAD_WHOLE = "\uE0A2"
NOTEHEAD_HALF = "\uE0A3"
NOTEHEAD_FILLED = "\uE0A4"

# Fähnchen (Flags)
FLAG_8TH_UP = "\uE240"
FLAG_8TH_DOWN = "\uE241"
FLAG_16TH_UP = "\uE242"
FLAG_16TH_DOWN = "\uE243"
FLAG_32ND_UP = "\uE244"
FLAG_32ND_DOWN = "\uE245"

# Pausen (Rests)
REST_WHOLE = "\uE4E3"
REST_HALF = "\uE4E4"
REST_QUARTER = "\uE4E5"
REST_8TH = "\uE4E6"
REST_16TH = "\uE4E7"
REST_32ND = "\uE4E8"

# Vorzeichen (Accidentals)
FLAT = "\uE260"
NATURAL = "\uE261"
SHARP = "\uE262"

# Punktierung
DOT = "\uE1E7"

# Taktart-Ziffern (Time Signature)
TIME_0 = "\uE080"
TIME_1 = "\uE081"
TIME_2 = "\uE082"
TIME_3 = "\uE083"
TIME_4 = "\uE084"
TIME_5 = "\uE085"
TIME_6 = "\uE086"
TIME_7 = "\uE087"
TIME_8 = "\uE088"
TIME_9 = "\uE089"

TIME_DIGITS = [TIME_0, TIME_1, TIME_2, TIME_3, TIME_4,
               TIME_5, TIME_6, TIME_7, TIME_8, TIME_9]
