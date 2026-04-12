"""SignalBus - Zentraler Event-Bus für komponentenübergreifende Kommunikation."""

import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("musiai.util.SignalBus")


class SignalBus(QObject):
    """Zentrales Signal-Hub. Verhindert zirkuläre Imports zwischen Komponenten."""

    # Piece/Projekt
    piece_loaded = Signal(object)       # Piece
    piece_changed = Signal()            # Noten/Takte geändert → Playback neu
    project_saved = Signal(str)         # Dateipfad

    # Noten-Auswahl und -Bearbeitung
    note_selected = Signal(object)      # Note (oder None)
    note_changed = Signal(object)       # Note
    note_deleted = Signal(object)       # Note
    notes_deselected = Signal()

    # Playback
    playback_started = Signal()
    playback_stopped = Signal()
    playback_position = Signal(float)   # Beat-Position

    # MIDI Keyboard
    midi_connected = Signal(str)        # Port-Name
    midi_disconnected = Signal()
    midi_note_on = Signal(int, int)     # Note, Velocity
    midi_note_off = Signal(int)         # Note
    midi_cc = Signal(int, int)          # CC-Nummer, Wert
    midi_pitch_bend = Signal(int)       # Pitch Bend Wert

    # Recording
    recording_started = Signal()
    recording_stopped = Signal()

    # UI
    status_message = Signal(str)        # Statusleisten-Text
    refresh_notation = Signal()         # Notation neu zeichnen

    def __init__(self):
        super().__init__()
        logger.debug("SignalBus initialisiert")
