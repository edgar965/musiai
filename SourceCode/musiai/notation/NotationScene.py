"""NotationScene - QGraphicsScene die das gesamte Stück rendert."""

import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem
from PySide6.QtGui import QColor, QPen, QFont, QBrush
from musiai.model.Piece import Piece
from musiai.notation.MeasureRenderer import MeasureRenderer
from musiai.notation.ClefHelper import ClefHelper, TREBLE, BASS
from musiai.model.Measure import Measure as MeasureModel
from musiai.model.Note import Note
from musiai.notation.PlayheadItem import PlayheadItem
from musiai.notation.CursorItem import CursorItem
from musiai.notation.NoteItem import NoteItem
from musiai.util.Constants import (
    COLOR_BACKGROUND, PIXELS_PER_BEAT, STAFF_LINE_SPACING,
)

logger = logging.getLogger("musiai.notation.NotationScene")


class NotationScene(QGraphicsScene):
    """Scene die ein Piece als farbige Notation mit Systemen rendert."""

    MARGIN_LEFT = 110
    MARGIN_TOP = 80
    LABEL_WIDTH = 100
    DEFAULT_SYSTEM_WIDTH = 1100
    PART_SPACING = 120
    SYSTEM_GAP = 50

    # Render-Modi
    MODE_MUSICXML = "musicxml"
    MODE_MIDISHEET = "midisheet"
    MODE_SVG = "svg"
    MODE_PIANOROLL = "pianoroll"

    def __init__(self):
        super().__init__()
        self.setBackgroundBrush(QColor(*COLOR_BACKGROUND))
        self.piece: Piece | None = None
        self.measure_renderers: list[MeasureRenderer] = []
        self._primary_renderers: list[MeasureRenderer] = []
        self._system_width = self.DEFAULT_SYSTEM_WIDTH
        self._render_mode = self.MODE_MUSICXML
        self.playhead = PlayheadItem()
        self.addItem(self.playhead)
        self.cursor = CursorItem()
        self.addItem(self.cursor)

    def set_render_mode(self, mode: str) -> None:
        """Render-Modus setzen."""
        if mode not in (self.MODE_MUSICXML, self.MODE_MIDISHEET,
                        self.MODE_SVG, self.MODE_PIANOROLL):
            logger.warning(f"Unbekannter Render-Modus: {mode}")
            return
        if mode != self._render_mode:
            self._render_mode = mode
            logger.info(f"Render-Modus gewechselt: {mode}")

    @property
    def render_mode(self) -> str:
        return self._render_mode

    def set_piece(self, piece: Piece) -> None:
        logger.info(f"Rendere Piece: '{piece.title}'")
        self.piece = piece
        self.refresh()

    def set_system_width(self, width: float) -> None:
        """System-Breite setzen und neu rendern (für Zoom/Resize)."""
        new_width = max(300, width - self.MARGIN_LEFT - 20)
        if abs(new_width - self._system_width) > 20:
            self._system_width = new_width
            if self.piece:
                self.refresh()

    def refresh(self) -> None:
        self.removeItem(self.playhead)
        self.removeItem(self.cursor)
        self.clear()
        self.measure_renderers.clear()
        self._primary_renderers.clear()
        self._measure_highlight = None
        self.addItem(self.playhead)
        self.addItem(self.cursor)

        if not self.piece or not self.piece.parts:
            return

        # Dispatch nach Render-Modus
        if self._render_mode == self.MODE_SVG:
            self._refresh_svg()
            return
        if self._render_mode == self.MODE_PIANOROLL:
            self._refresh_pianoroll()
            return
        if self._render_mode == self.MODE_MIDISHEET:
            self._refresh_midisheet()
            return

        note_parts = [p for p in self.piece.parts
                      if not (p.audio_track and p.audio_track.blocks)]
        audio_parts = [p for p in self.piece.parts
                       if p.audio_track and p.audio_track.blocks]
        n_note_parts = len(note_parts)

        if not note_parts:
            self._render_audio_only(audio_parts)
            return

        # Taktbreiten berechnen (basierend auf Part 0)
        systems = self._compute_systems(note_parts[0])

        center_y = self.MARGIN_TOP + 60
        max_width = 0.0

        for sys_idx, sys_measures in enumerate(systems):
            sys_top_y = center_y
            first_measure_idx = sys_measures[0]

            for part_idx, part in enumerate(note_parts):
                real_part_idx = self.piece.parts.index(part)
                x_offset = self.MARGIN_LEFT

                # Schlüssel automatisch bestimmen
                all_notes = [n for m in part.measures for n in m.notes]
                clef = ClefHelper.detect_clef(all_notes)

                # Label nur im ersten System
                if sys_idx == 0:
                    self._draw_part_label(part, real_part_idx, center_y)

                current_tempo = self.piece.initial_tempo
                for mi in range(first_measure_idx):
                    if mi < len(part.measures) and part.measures[mi].tempo:
                        current_tempo = part.measures[mi].tempo.bpm

                for local_i, m_idx in enumerate(sys_measures):
                    if m_idx >= len(part.measures):
                        break
                    measure = part.measures[m_idx]
                    if measure.tempo:
                        current_tempo = measure.tempo.bpm

                    show_clef = (local_i == 0)
                    display_tempo = current_tempo if (
                        sys_idx == 0 and local_i == 0 and part_idx == 0
                    ) else 0
                    first_vel = 0
                    if (sys_idx == 0 and local_i == 0
                            and measure.notes and part_idx == 0):
                        first_vel = measure.notes[0].expression.velocity

                    renderer = MeasureRenderer(
                        measure, x_offset, center_y, show_clef,
                        display_tempo, first_vel, current_tempo,
                        clef=clef,
                    )
                    renderer.render(self)
                    self.measure_renderers.append(renderer)
                    if part_idx == 0:
                        self._primary_renderers.append(renderer)
                    x_offset += renderer.width

                # Schlusstaktstrich (schwarz, dünn)
                pen = QPen(QColor(40, 40, 50), 1.5)
                sh = 2 * STAFF_LINE_SPACING
                self.addLine(x_offset, center_y - sh,
                             x_offset, center_y + sh, pen)
                max_width = max(max_width, x_offset)
                center_y += self.PART_SPACING

            sys_bottom_y = center_y - self.PART_SPACING

            # Partiturklammer
            if n_note_parts > 1:
                self._draw_system_bracket(sys_top_y, sys_bottom_y)

            center_y += self.SYSTEM_GAP

        # Audio-Stimmen am Ende
        for part in audio_parts:
            real_idx = self.piece.parts.index(part)
            self._draw_part_label(part, real_idx, center_y)
            self._draw_waveform(part, real_idx, center_y,
                                self.piece.initial_tempo)
            center_y += 100

        self.playhead.set_y_range(self.MARGIN_TOP, center_y)
        self.cursor.set_y_range(self.MARGIN_TOP, center_y)
        self.setSceneRect(0, 0, max_width + 60, center_y + 40)
        logger.info(f"Scene gerendert: {len(self.measure_renderers)} Renderer, "
                    f"{len(self._primary_renderers)} primär")

    # ------------------------------------------------------------------
    # System-Layout
    # ------------------------------------------------------------------

    def _compute_systems(self, ref_part) -> list[list[int]]:
        """Berechnet welche Takte in welches System kommen."""
        systems = []
        current_system = []
        current_width = 0.0
        tempo = self.piece.initial_tempo

        for i, measure in enumerate(ref_part.measures):
            if measure.tempo:
                tempo = measure.tempo.bpm
            scale = 120.0 / max(20, tempo)
            ppb = PIXELS_PER_BEAT * scale
            header = 58 if (len(current_system) == 0) else 0
            w = measure.effective_duration_beats * ppb + header

            if current_system and current_width + w > self._system_width:
                systems.append(current_system)
                current_system = [i]
                current_width = 58 + measure.effective_duration_beats * ppb
            else:
                current_system.append(i)
                current_width += w

        if current_system:
            systems.append(current_system)
        return systems

    def _draw_system_bracket(self, top_y: float, bottom_y: float) -> None:
        """Eckige Partiturklammer links vom System."""
        sh = 2 * STAFF_LINE_SPACING
        x = self.MARGIN_LEFT - 10
        pen = QPen(QColor(40, 40, 60), 2.5)
        line = self.addLine(x, top_y - sh, x, bottom_y + sh, pen)
        line.setZValue(5)
        top_hook = self.addLine(x, top_y - sh, x + 7, top_y - sh, pen)
        top_hook.setZValue(5)
        bot_hook = self.addLine(x, bottom_y + sh, x + 7, bottom_y + sh, pen)
        bot_hook.setZValue(5)

    # ------------------------------------------------------------------
    # Audio-only Fallback
    # ------------------------------------------------------------------

    def _render_audio_only(self, audio_parts) -> None:
        center_y = self.MARGIN_TOP + 60
        for part in audio_parts:
            idx = self.piece.parts.index(part)
            self._draw_part_label(part, idx, center_y)
            self._draw_waveform(part, idx, center_y, self.piece.initial_tempo)
            center_y += 100
        self.playhead.set_y_range(self.MARGIN_TOP, center_y)
        self.cursor.set_y_range(self.MARGIN_TOP, center_y)
        self.setSceneRect(0, 0, 800, center_y + 40)

    # ------------------------------------------------------------------
    # Beat ↔ X Koordinaten (nur primäre Renderer = Part 0)
    # ------------------------------------------------------------------

    def beat_to_x(self, global_beat: float) -> float:
        if not self._primary_renderers:
            return self.MARGIN_LEFT + global_beat * PIXELS_PER_BEAT
        cumulative = 0.0
        for r in self._primary_renderers:
            dur = r.measure.duration_beats
            if global_beat < cumulative + dur:
                local = global_beat - cumulative
                return r.x_offset + r.header_width + local * r.pixels_per_beat
            cumulative += dur
        last = self._primary_renderers[-1]
        overshoot = global_beat - cumulative
        return last.x_offset + last.width + overshoot * last.pixels_per_beat

    def x_to_beat(self, x: float) -> float:
        if not self._primary_renderers:
            return max(0.0, (x - self.MARGIN_LEFT) / PIXELS_PER_BEAT)
        cumulative = 0.0
        for r in self._primary_renderers:
            content_start = r.x_offset + r.header_width
            content_end = r.x_offset + r.width
            if x < content_end:
                local_x = max(0.0, x - content_start)
                return cumulative + local_x / r.pixels_per_beat
            cumulative += r.measure.duration_beats
        return cumulative

    def beat_at_x(self, x: float) -> float:
        return self.x_to_beat(x)

    # ------------------------------------------------------------------
    # Playhead / Cursor
    # ------------------------------------------------------------------

    def update_playhead(self, beat: float) -> None:
        x = self.beat_to_x(beat)
        self.playhead.show_at(x)

    def hide_playhead(self) -> None:
        self.playhead.hide()

    def update_cursor(self, beat: float) -> None:
        x = self.beat_to_x(beat)
        self.cursor.show_at(x)

    def hide_cursor(self) -> None:
        self.cursor.hide()

    # ------------------------------------------------------------------
    # Drawing Helpers
    # ------------------------------------------------------------------

    def _draw_waveform(self, part, part_idx: int,
                       y: float, tempo: float) -> None:
        from musiai.notation.WaveformItem import WaveformItem
        ppb = (self._primary_renderers[0].pixels_per_beat
               if self._primary_renderers else PIXELS_PER_BEAT)
        for i, block in enumerate(part.audio_track.blocks):
            dur_beats = block.duration_beats(tempo)
            width = dur_beats * ppb
            x = self.MARGIN_LEFT + block.start_beat * ppb
            item = WaveformItem(block.samples, block.sr, width, x, y, i)
            item.setData(0, "waveform")
            item.setData(1, part_idx)
            self.addItem(item)

    def _draw_part_label(self, part, part_idx: int, center_y: float) -> None:
        x = 4
        label = QGraphicsSimpleTextItem(part.name)
        label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        label.setBrush(QBrush(QColor(30, 30, 80)))
        label.setPos(x, center_y - 10)
        label.setZValue(5)
        label.setData(0, "part_label")
        label.setData(1, part_idx)
        self.addItem(label)

        mute_char = "\U0001F507" if part.muted else "\U0001F50A"
        mute = QGraphicsSimpleTextItem(mute_char)
        mute.setFont(QFont("Segoe UI Emoji", 12))
        mute.setPos(x, center_y + 8)
        mute.setZValue(5)
        mute.setData(0, "part_mute")
        mute.setData(1, part_idx)
        self.addItem(mute)

    # ------------------------------------------------------------------
    # Measure Highlight
    # ------------------------------------------------------------------

    def highlight_measure(self, measure) -> None:
        self.clear_measure_highlight()
        from PySide6.QtWidgets import QGraphicsRectItem
        for renderer in self.measure_renderers:
            if renderer.measure is measure:
                sh = 2 * STAFF_LINE_SPACING + 6
                rect = QGraphicsRectItem(
                    renderer.x_offset, renderer.center_y - sh,
                    renderer.width, sh * 2,
                )
                rect.setBrush(QBrush(QColor(0, 100, 255, 25)))
                rect.setPen(QPen(QColor(0, 100, 255, 80), 1.5))
                rect.setZValue(-1)
                self.addItem(rect)
                self._measure_highlight = rect
                return

    def clear_measure_highlight(self) -> None:
        if hasattr(self, '_measure_highlight') and self._measure_highlight:
            try:
                self.removeItem(self._measure_highlight)
            except RuntimeError:
                pass
            self._measure_highlight = None

    # ------------------------------------------------------------------
    # Alternative Renderer
    # ------------------------------------------------------------------

    def _refresh_svg(self) -> None:
        """Verovio SVG Rendering."""
        from musiai.notation.VerovioRenderer import VerovioRenderer
        self._verovio_renderer = VerovioRenderer()
        # file_path aus dem aktiven Tab durchreichen
        file_path = getattr(self, '_source_file_path', None)
        self._verovio_renderer.render_piece(
            self.piece, self, self._system_width, file_path)

    def _refresh_pianoroll(self) -> None:
        """Piano-Roll Rendering."""
        from musiai.notation.PianoRollRenderer import PianoRollRenderer
        renderer = PianoRollRenderer()
        renderer.render_piece(self.piece, self, self._system_width)

    # ------------------------------------------------------------------
    # NoteItem queries
    # ------------------------------------------------------------------

    def get_note_item_at(self, scene_pos) -> NoteItem | None:
        for item in self.items(scene_pos):
            if isinstance(item, NoteItem):
                return item
        return None

    def get_all_note_items(self) -> list[NoteItem]:
        return [item for item in self.items() if isinstance(item, NoteItem)]

    # ------------------------------------------------------------------
    # MIDI Sheet Rendering
    # ------------------------------------------------------------------

    def _refresh_midisheet(self) -> None:
        """MIDI-Notenblatt rendern (portiert von MusicExplorer)."""
        try:
            from musiai.ui.midi.MidiSheetRenderer import MidiSheetRenderer
            renderer = MidiSheetRenderer()
            renderer.render(self.piece, self, self._system_width)
        except Exception as e:
            logger.error(f"MIDI Sheet Fehler: {e}", exc_info=True)
            text = self.addText(f"MIDI Sheet Fehler: {e}")
            text.setPos(20, 40)
