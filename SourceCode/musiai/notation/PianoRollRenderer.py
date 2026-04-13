"""PianoRollRenderer - Einfache Piano-Roll Ansicht (horizontale Balken pro Note)."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt
from musiai.model.Piece import Piece
from musiai.notation.ColorScheme import ColorScheme
from musiai.util.Constants import PIXELS_PER_BEAT, MIDI_MIN_NOTE, MIDI_MAX_NOTE

logger = logging.getLogger("musiai.notation.PianoRollRenderer")

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROW_HEIGHT = 8
LABEL_WIDTH = 50
TOP_MARGIN = 30


class PianoRollRenderer:
    """Piano-Roll Darstellung: horizontale farbige Balken je Note."""

    def render_piece(self, piece: Piece, scene: QGraphicsScene,
                     system_width: float) -> None:
        """Piece als Piano-Roll in die Scene rendern."""
        if not piece or not piece.parts:
            return

        note_parts = [p for p in piece.parts
                      if not (p.audio_track and p.audio_track.blocks)]
        if not note_parts:
            return

        # Gesamtdauer in Beats
        total_beats = 0.0
        for part in note_parts:
            part_beats = sum(m.effective_duration_beats for m in part.measures)
            total_beats = max(total_beats, part_beats)

        if total_beats <= 0:
            return

        ppb = max(20.0, (system_width - LABEL_WIDTH) / total_beats)
        pitch_range = MIDI_MAX_NOTE - MIDI_MIN_NOTE + 1
        total_height = pitch_range * ROW_HEIGHT + TOP_MARGIN + 20

        # Pitch-Zeilen (Gitter)
        self._draw_grid(scene, pitch_range, total_beats, ppb)

        # Taktstriche
        self._draw_measure_lines(scene, note_parts[0], ppb, pitch_range)

        # Noten als Balken
        for part in note_parts:
            beat_offset = 0.0
            for measure in part.measures:
                for note in measure.notes:
                    if getattr(note, 'is_rest', False):
                        continue
                    x = LABEL_WIDTH + (beat_offset + note.start_beat) * ppb
                    pitch_row = MIDI_MAX_NOTE - note.pitch
                    y = TOP_MARGIN + pitch_row * ROW_HEIGHT
                    w = max(2.0, note.duration_beats * ppb - 1)
                    h = ROW_HEIGHT - 1

                    color = ColorScheme.velocity_to_color(
                        note.expression.velocity
                    )
                    rect = QGraphicsRectItem(x, y, w, h)
                    rect.setBrush(QBrush(color))
                    rect.setPen(QPen(color.darker(130), 0.5))
                    rect.setZValue(5)
                    rect.setToolTip(
                        f"{note.name} (MIDI {note.pitch})\n"
                        f"Vel: {note.expression.velocity}  "
                        f"Beat: {beat_offset + note.start_beat:.2f}"
                    )
                    scene.addItem(rect)

                beat_offset += measure.effective_duration_beats

        scene.setSceneRect(0, 0,
                           LABEL_WIDTH + total_beats * ppb + 20,
                           total_height)
        logger.info(f"Piano-Roll gerendert: {total_beats:.1f} Beats, "
                    f"{len(note_parts)} Parts")

    def _draw_grid(self, scene: QGraphicsScene, pitch_range: int,
                   total_beats: float, ppb: float) -> None:
        """Horizontale Gitterlinien und Pitch-Labels."""
        right_edge = LABEL_WIDTH + total_beats * ppb
        white_keys = {0, 2, 4, 5, 7, 9, 11}  # C D E F G A B

        for i in range(pitch_range):
            pitch = MIDI_MAX_NOTE - i
            y = TOP_MARGIN + i * ROW_HEIGHT
            semitone = pitch % 12

            # Hintergrund: weiss fuer Stammtoene, hellgrau fuer Vorzeichen
            if semitone not in white_keys:
                bg = QGraphicsRectItem(LABEL_WIDTH, y,
                                       right_edge - LABEL_WIDTH, ROW_HEIGHT)
                bg.setBrush(QBrush(QColor(235, 235, 240)))
                bg.setPen(QPen(Qt.PenStyle.NoPen))
                bg.setZValue(0)
                scene.addItem(bg)

            # Linie bei jedem C
            if semitone == 0:
                pen = QPen(QColor(180, 180, 190), 0.8)
                scene.addLine(LABEL_WIDTH, y, right_edge, y, pen)
                octave = (pitch // 12) - 1
                label = QGraphicsSimpleTextItem(f"C{octave}")
                label.setFont(QFont("Arial", 7))
                label.setBrush(QBrush(QColor(80, 80, 100)))
                label.setPos(2, y - 4)
                label.setZValue(2)
                scene.addItem(label)


    def _draw_measure_lines(self, scene: QGraphicsScene, ref_part,
                            ppb: float, pitch_range: int) -> None:
        """Vertikale Taktstriche."""
        beat_offset = 0.0
        bottom = TOP_MARGIN + pitch_range * ROW_HEIGHT

        for measure in ref_part.measures:
            x = LABEL_WIDTH + beat_offset * ppb
            pen = QPen(QColor(140, 140, 160), 1.0)
            scene.addLine(x, TOP_MARGIN, x, bottom, pen)

            # Taktnummer
            label = QGraphicsSimpleTextItem(str(measure.number))
            label.setFont(QFont("Arial", 7))
            label.setBrush(QBrush(QColor(100, 100, 120)))
            label.setPos(x + 2, TOP_MARGIN - 15)
            label.setZValue(2)
            scene.addItem(label)

            beat_offset += measure.effective_duration_beats

        # Schluss-Strich
        x = LABEL_WIDTH + beat_offset * ppb
        pen = QPen(QColor(100, 100, 120), 2.0)
        scene.addLine(x, TOP_MARGIN, x, bottom, pen)
