"""TempoMarking - Tempo-Bezeichnungen und Dynamik-Stufen."""


class TempoMarking:
    """Ordnet BPM-Werte musikalischen Tempo-Bezeichnungen zu."""

    TEMPO_RANGES = [
        (20, 40, "Grave"),
        (40, 55, "Largo"),
        (55, 65, "Adagio"),
        (65, 73, "Andante"),
        (73, 86, "Moderato"),
        (86, 98, "Allegretto"),
        (98, 109, "Allegro moderato"),
        (109, 132, "Allegro"),
        (132, 168, "Vivace"),
        (168, 200, "Presto"),
        (200, 400, "Prestissimo"),
    ]

    @staticmethod
    def from_bpm(bpm: float) -> str:
        """BPM → Tempo-Bezeichnung (z.B. 120 → 'Allegro')."""
        for low, high, name in TempoMarking.TEMPO_RANGES:
            if low <= bpm < high:
                return name
        return "Allegro"

    @staticmethod
    def format_tempo(bpm: float) -> str:
        """BPM → Formatierte Anzeige (z.B. '♩= 120 (Allegro)')."""
        name = TempoMarking.from_bpm(bpm)
        return f"♩= {bpm:.0f} ({name})"


class DynamicMarking:
    """Ordnet Velocity-Werte musikalischen Dynamik-Bezeichnungen zu."""

    DYNAMIC_RANGES = [
        (0, 16, "ppp", "pianississimo"),
        (16, 33, "pp", "pianissimo"),
        (33, 49, "p", "piano"),
        (49, 64, "mp", "mezzopiano"),
        (64, 80, "mf", "mezzoforte"),
        (80, 96, "f", "forte"),
        (96, 112, "ff", "fortissimo"),
        (112, 128, "fff", "fortississimo"),
    ]

    @staticmethod
    def from_velocity(velocity: int) -> str:
        """Velocity → Dynamik-Kürzel (z.B. 80 → 'f')."""
        for low, high, short, _ in DynamicMarking.DYNAMIC_RANGES:
            if low <= velocity < high:
                return short
        return "f"

    @staticmethod
    def from_velocity_long(velocity: int) -> str:
        """Velocity → Voller Dynamik-Name (z.B. 80 → 'forte')."""
        for low, high, _, long_name in DynamicMarking.DYNAMIC_RANGES:
            if low <= velocity < high:
                return long_name
        return "forte"

    @staticmethod
    def format_dynamic(velocity: int) -> str:
        """Velocity → Formatierte Anzeige (z.B. 'f (forte)')."""
        short = DynamicMarking.from_velocity(velocity)
        long_name = DynamicMarking.from_velocity_long(velocity)
        return f"{short} ({long_name})"
