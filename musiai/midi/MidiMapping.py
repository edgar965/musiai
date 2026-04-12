"""MidiMapping - Mappt MIDI CC/Pitch Bend auf Expression-Parameter."""

import logging

logger = logging.getLogger("musiai.midi.MidiMapping")


class MidiMapping:
    """Definiert welche MIDI-Controller auf welche Expression-Parameter wirken."""

    def __init__(self):
        # Default-Mappings
        self.velocity_cc = 1       # CC 1 (Mod Wheel) → Velocity
        self.duration_cc = 11      # CC 11 (Expression) → Duration
        self.pitch_bend_range = 50  # Pitch Bend Range in Cent

    def map_cc(self, cc_number: int, value: int) -> tuple[str, float] | None:
        """CC-Wert auf Expression-Parameter mappen.

        Returns:
            ("velocity", 0-127) oder ("duration", 0.8-1.2) oder None
        """
        if cc_number == self.velocity_cc:
            return ("velocity", float(value))

        if cc_number == self.duration_cc:
            # CC 0-127 → Duration 0.8-1.2
            deviation = 0.8 + (value / 127.0) * 0.4
            return ("duration", deviation)

        return None

    def map_pitch_bend(self, value: int) -> float:
        """Pitch Bend Wert (0-16383) → Cent-Offset.

        8192 = Mitte (0 Cent)
        0 = -range Cent
        16383 = +range Cent
        """
        normalized = (value - 8192) / 8192.0
        return normalized * self.pitch_bend_range
