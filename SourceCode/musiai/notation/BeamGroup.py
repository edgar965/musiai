"""BeamGroup - Balkengruppen nach MusicExplorer-Logik."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QPen, QColor
from musiai.util.Constants import STAFF_LINE_SPACING

logger = logging.getLogger("musiai.notation.BeamGroup")

# Notendauer-Klassifikation in Beats (bei Viertel = 1 Beat)
DURATION_THRESHOLDS = [
    ("whole", 3.5),
    ("dotted_half", 2.5),
    ("half", 1.75),
    ("dotted_quarter", 1.25),
    ("quarter", 0.875),
    ("dotted_eighth", 0.625),
    ("eighth", 0.375),
    ("triplet", 0.29),
    ("sixteenth", 0.1875),
    ("thirty_second", 0.0),
]

# Dauer-Typen die gebeamt werden können
BEAMABLE = {"eighth", "dotted_eighth", "triplet", "sixteenth", "thirty_second"}


def classify_duration(beats: float) -> str:
    """Beat-Dauer → Notentyp-String."""
    for name, threshold in DURATION_THRESHOLDS:
        if beats >= threshold:
            return name
    return "thirty_second"


def beam_count(dur_type: str) -> int:
    """Anzahl Balken pro Notentyp."""
    if dur_type in ("eighth", "dotted_eighth", "triplet"):
        return 1
    if dur_type == "sixteenth":
        return 2
    if dur_type == "thirty_second":
        return 3
    return 0


class BeamGroup:
    """Erkennt und zeichnet Balkengruppen (portiert von MusicExplorer)."""

    @staticmethod
    def find_beam_groups(notes, time_sig) -> list[list]:
        """Noten in Balkengruppen aufteilen.

        Regeln (aus C# ChordSymbol.CanCreateBeam):
        - Nur Achtel und kürzer
        - Gleiche Dauer innerhalb einer Gruppe (außer dotted_eighth→sixteenth)
        - Innerhalb eines Beat-Segments (Viertelnote bei 4/4, punktierte Viertel bei 6/8)
        - Alle im selben Takt
        """
        if not notes:
            return []

        denom = time_sig.denominator
        # Beat-Gruppengröße in Viertelnoten-Beats
        if denom == 8 and time_sig.numerator % 3 == 0:
            group_size = 1.5  # Zusammengesetzte Taktart (6/8, 9/8, 12/8)
        else:
            group_size = 1.0  # Einfache Taktart

        sorted_notes = sorted(notes, key=lambda n: n.start_beat)
        groups = []
        current = []

        for note in sorted_notes:
            dur_type = classify_duration(note.duration_beats)
            if dur_type not in BEAMABLE:
                # Nicht beambar → Gruppe abschließen
                if len(current) >= 2:
                    groups.append(current)
                current = []
                continue

            if not current:
                current = [note]
                continue

            prev = current[-1]
            prev_dur = classify_duration(prev.duration_beats)
            prev_end = prev.start_beat + prev.duration_beats

            # Prüfungen (MusicExplorer-Regeln):
            same_segment = (
                int(note.start_beat / group_size) ==
                int(prev.start_beat / group_size)
            )
            adjacent = abs(note.start_beat - prev_end) < 0.05
            same_duration = (dur_type == prev_dur)
            # Spezialfall: dotted_eighth → sixteenth
            dotted_pair = (
                prev_dur == "dotted_eighth" and dur_type == "sixteenth"
            ) or (
                dur_type == "dotted_eighth" and prev_dur == "sixteenth"
            )

            if same_segment and adjacent and (same_duration or dotted_pair):
                current.append(note)
                # Max Gruppengröße begrenzen
                if len(current) >= 6:
                    groups.append(current)
                    current = []
            else:
                if len(current) >= 2:
                    groups.append(current)
                current = [note]

        if len(current) >= 2:
            groups.append(current)

        return groups

    @staticmethod
    def draw_beams(scene: QGraphicsScene, note_items: list,
                   beam_notes: list, color: QColor = None):
        """Balken zwischen NoteItems zeichnen (MusicExplorer DrawHorizBarStem)."""
        if len(beam_notes) < 2:
            return

        # Finde die NoteItems für die beam_notes
        items = []
        for note in beam_notes:
            for ni in note_items:
                if ni.note is note:
                    items.append(ni)
                    break

        if len(items) < 2:
            return

        if color is None:
            color = QColor(60, 60, 80)

        # Stem-Enden bestimmen
        first_end = items[0].stem_end_pos()
        last_end = items[-1].stem_end_pos()
        if not first_end or not last_end:
            return

        # Beam-Richtung: UP wenn Stems nach oben zeigen
        stem_up = first_end[1] < items[0].y()

        # Mittlere Stems auf Linie zwischen first und last ausrichten
        # (LineUpStemEnds aus MusicExplorer)
        if len(items) > 2:
            _align_stem_ends(items, stem_up)
            # Positionen neu lesen nach Alignment
            first_end = items[0].stem_end_pos()
            last_end = items[-1].stem_end_pos()

        # Beams zeichnen
        beam_thickness = max(2.0, STAFF_LINE_SPACING / 3)
        pen = QPen(color, beam_thickness)

        dur_type = classify_duration(beam_notes[0].duration_beats)
        n_beams = beam_count(dur_type)

        for b in range(n_beams):
            offset = b * (beam_thickness + 2)
            if stem_up:
                offset = offset  # Balken oben
            else:
                offset = -offset  # Balken unten

            # Linie von erstem zu letztem Stem-Ende
            x1, y1 = items[0].stem_end_pos()
            xn, yn = items[-1].stem_end_pos()
            beam_line = scene.addLine(
                x1, y1 + offset, xn, yn + offset, pen
            )
            beam_line.setZValue(8)


def _align_stem_ends(items: list, stem_up: bool) -> None:
    """Stem-Enden für 3+ Noten ausrichten (LineUpStemEnds)."""
    if len(items) < 3:
        return

    first = items[0]
    last = items[-1]
    first_end = first.stem_end_pos()
    last_end = last.stem_end_pos()
    if not first_end or not last_end:
        return

    # Lineare Interpolation zwischen erstem und letztem Stem-Ende
    x1, y1 = first_end
    xn, yn = last_end
    dx = xn - x1
    if abs(dx) < 1:
        return

    for item in items[1:-1]:
        pos = item.stem_end_pos()
        if not pos:
            continue
        # Interpolierte Y-Position auf der Beam-Linie
        t = (item.x() - x1) / dx
        target_y = y1 + t * (yn - y1)

        # Stem-Länge anpassen
        stem = item._stem
        if stem_up:
            new_len = item.y() - target_y
            stem.setLine(stem.line().x1(), 0, stem.line().x1(), -new_len)
        else:
            new_len = target_y - item.y()
            stem.setLine(stem.line().x1(), 0, stem.line().x1(), new_len)
