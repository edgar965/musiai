"""MidiSheetRenderer - Hauptklasse für MIDI-Notenblatt-Rendering."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QColor, QPen, QFont, QBrush, QPixmap, QPainter
from PySide6.QtCore import Qt
from musiai.model.Piece import Piece
from musiai.ui.midi.WhiteNote import WhiteNote
from musiai.ui.midi.ChordSymbol import ChordSymbol, NoteData
from musiai.ui.midi.BarSymbol import BarSymbol
from musiai.ui.midi.ClefSymbol import TREBLE, BASS
from musiai.ui.midi.Staff import Staff
from musiai.ui.midi.SheetConfig import SheetConfig
from musiai.ui.midi import NoteDuration as ND
from musiai.notation.ClefHelper import ClefHelper
from musiai.notation.ColorScheme import ColorScheme

logger = logging.getLogger("musiai.ui.midi.MidiSheetRenderer")


class MidiSheetRenderer:
    """Rendert ein Piece als klassisches Notenblatt."""

    def __init__(self, config: SheetConfig = None):
        self.config = config or SheetConfig.large()

    def render(self, piece: Piece, scene: QGraphicsScene,
               system_width: float = 1100) -> None:
        if not piece or not piece.parts:
            return

        self.config.page_width = int(system_width) - 120  # Platz für Labels
        y_offset = 60
        cfg = self._make_config_dict()

        for part in piece.parts:
            if part.audio_track and part.audio_track.blocks:
                continue

            # Schlüssel bestimmen
            all_notes = [n for m in part.measures for n in m.notes]
            clef_str = ClefHelper.detect_clef(all_notes)
            clef = TREBLE if clef_str == "treble" else BASS

            # Symbole erstellen
            symbols = self._create_symbols(part, clef)

            # In Staffs aufteilen
            staffs = self._create_staffs(symbols, clef, cfg)

            # Part-Label
            label = scene.addText(part.name)
            label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label.setDefaultTextColor(QColor(30, 30, 80))
            label.setPos(4, y_offset)

            # Staffs rendern
            for staff in staffs:
                staff.calculate_layout(cfg)
                pixmap = self._render_staff(staff, cfg)
                item = scene.addPixmap(pixmap)
                item.setPos(100, y_offset)
                y_offset += staff.height + 15

            y_offset += 20

        scene.setSceneRect(0, 0, system_width + 60, y_offset + 40)

    def _make_config_dict(self) -> dict:
        return {
            'note_height': self.config.note_height,
            'note_width': self.config.note_width,
            'line_space': self.config.line_space,
            'line_width': self.config.line_width,
            'staff_height': self.config.staff_height,
            'note_color': QColor(200, 60, 30),
        }

    def _create_symbols(self, part, clef: int) -> list:
        """Noten und Taktstriche aus Part erstellen."""
        symbols = []
        abs_tick = 0
        tpb = 480

        for measure in part.measures:
            measure_ticks = int(measure.duration_beats * tpb)

            # Noten nach Startzeit gruppieren
            time_groups: dict[int, list] = {}
            for note in measure.notes:
                tick = abs_tick + int(note.start_beat * tpb)
                if tick not in time_groups:
                    time_groups[tick] = []
                time_groups[tick].append(note)

            for tick in sorted(time_groups):
                notes = time_groups[tick]
                note_data = []
                for n in notes:
                    wn = WhiteNote.from_midi(n.pitch)
                    dur = ND.from_beats(n.duration_beats)
                    nd = NoteData(n.pitch, wn, dur)
                    note_data.append(nd)
                chord = ChordSymbol(note_data, clef, tick)
                symbols.append(chord)

            abs_tick += measure_ticks
            symbols.append(BarSymbol(abs_tick))

        return symbols

    def _create_staffs(self, symbols: list, clef: int,
                       cfg: dict) -> list[Staff]:
        """Symbole in Zeilen aufteilen."""
        staffs = []
        start = 0
        page_w = self.config.page_width

        while start < len(symbols):
            end = start
            width = 50  # Clef + Rand
            while end < len(symbols):
                sym = symbols[end]
                w = sym.width if sym.width > 0 else sym.min_width
                if width + w > page_w and end > start:
                    # Nicht mitten im Takt abbrechen
                    # Rückwärts zum letzten BarSymbol
                    while end > start and not isinstance(symbols[end], BarSymbol):
                        end -= 1
                    if end == start:
                        end = start + 1  # Mindestens 1 Symbol
                    break
                width += w
                end += 1

            staff = Staff(symbols[start:end], clef)
            staff.calculate_layout(cfg)
            staffs.append(staff)
            start = end

        return staffs

    def _render_staff(self, staff: Staff, cfg: dict) -> QPixmap:
        """Staff auf ein QPixmap rendern."""
        width = self.config.page_width
        height = max(staff.height, 100)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 255, 255))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        staff.draw(painter, 0, cfg)
        painter.end()

        return pixmap
