"""Tests für UI-Workflows - simuliert komplette Benutzer-Aktionen."""

import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Measure import Measure
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo


def make_test_piece():
    """Erstellt ein Teststück mit 4 Takten, verschiedene Expression-Werte."""
    piece = Piece("UI-Test-Piece")
    piece.tempos = [Tempo(100, 0)]
    part = Part("Piano")

    m1 = Measure(1, TimeSignature(4, 4))
    m1.add_note(Note(60, 0, 1, Expression(velocity=30)))
    m1.add_note(Note(64, 1, 1, Expression(velocity=80)))
    m1.add_note(Note(67, 2, 1, Expression(velocity=120)))
    m1.add_note(Note(72, 3, 1, Expression(velocity=60)))

    m2 = Measure(2, TimeSignature(4, 4))
    m2.add_note(Note(60, 0, 1, Expression(80, cent_offset=15, glide_type="zigzag")))
    m2.add_note(Note(64, 1, 1, Expression(80, cent_offset=-20, glide_type="zigzag")))
    m2.add_note(Note(67, 2, 1, Expression(80, cent_offset=30, glide_type="curve")))
    m2.add_note(Note(72, 3, 1, Expression(80, cent_offset=0)))

    m3 = Measure(3, TimeSignature(3, 4))
    m3.add_note(Note(60, 0, 1, Expression(80, duration_deviation=0.85)))
    m3.add_note(Note(64, 1, 1, Expression(80, duration_deviation=1.15)))
    m3.add_note(Note(67, 2, 1, Expression(80, duration_deviation=1.0)))

    m4 = Measure(4, TimeSignature(4, 4))
    m4.add_note(Note(60, 0, 2, Expression(120, 10, 1.1, "zigzag")))
    m4.add_note(Note(67, 2, 2, Expression(40, -15, 0.9, "curve")))

    part.add_measure(m1)
    part.add_measure(m2)
    part.add_measure(m3)
    part.add_measure(m4)
    piece.add_part(part)
    return piece


# ==============================================================
# MIDI IMPORT / EXPORT
# ==============================================================

class TestWorkflowMidiImport(unittest.TestCase):
    """Workflow: MIDI-Datei importieren."""

    def test_import_exported_midi(self):
        """Export → Import Roundtrip."""
        from musiai.midi.MidiExporter import MidiExporter
        from musiai.midi.MidiImporter import MidiImporter
        piece = make_test_piece()
        path = os.path.join(tempfile.gettempdir(), "wf_import.mid")
        MidiExporter().export_file(piece, path)
        piece2 = MidiImporter().import_file(path)
        self.assertGreater(len(piece2.parts), 0)
        total_notes = sum(len(m.notes) for p in piece2.parts for m in p.measures)
        self.assertGreater(total_notes, 0)
        os.unlink(path)

    def test_imported_note_count_similar(self):
        """Notenanzahl nach Import sollte ungefähr gleich sein (music21 kann leicht abweichen)."""
        from musiai.midi.MidiExporter import MidiExporter
        from musiai.midi.MidiImporter import MidiImporter
        piece = make_test_piece()
        original_count = sum(len(m.notes) for m in piece.parts[0].measures)
        path = os.path.join(tempfile.gettempdir(), "wf_count.mid")
        MidiExporter().export_file(piece, path)
        piece2 = MidiImporter().import_file(path)
        imported_count = sum(len(m.notes) for p in piece2.parts for m in p.measures)
        self.assertAlmostEqual(imported_count, original_count, delta=2)
        os.unlink(path)


class TestWorkflowMidiExport(unittest.TestCase):
    """Workflow: MIDI exportieren mit Expression-Daten."""

    def test_export_creates_valid_file(self):
        from musiai.midi.MidiExporter import MidiExporter
        piece = make_test_piece()
        path = os.path.join(tempfile.gettempdir(), "wf_export.mid")
        MidiExporter().export_file(piece, path)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 50)
        os.unlink(path)

    def test_export_contains_pitch_bend(self):
        """Cent-Offsets → Pitch Bend in MIDI."""
        import mido
        from musiai.midi.MidiExporter import MidiExporter
        piece = Piece("BendTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(80, 25.0, 1.0, "zigzag")))
        part.add_measure(m)
        piece.add_part(part)
        path = os.path.join(tempfile.gettempdir(), "wf_bend.mid")
        MidiExporter().export_file(piece, path)
        mid = mido.MidiFile(path)
        has_bend = any(msg.type == "pitchwheel" for t in mid.tracks for msg in t if hasattr(msg, "type"))
        self.assertTrue(has_bend)
        os.unlink(path)

    def test_export_velocity_preserved(self):
        """Velocity-Werte im MIDI korrekt."""
        import mido
        from musiai.midi.MidiExporter import MidiExporter
        piece = Piece("VelTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(velocity=110)))
        part.add_measure(m)
        piece.add_part(part)
        path = os.path.join(tempfile.gettempdir(), "wf_vel.mid")
        MidiExporter().export_file(piece, path)
        mid = mido.MidiFile(path)
        note_ons = [msg for t in mid.tracks for msg in t if hasattr(msg, "type") and msg.type == "note_on" and msg.velocity > 0]
        self.assertTrue(any(n.velocity == 110 for n in note_ons))
        os.unlink(path)


class TestWorkflowMusicXmlImport(unittest.TestCase):
    """Workflow: MusicXML importieren."""

    def test_musicxml_importer_exists(self):
        """MusicXML Importer kann instanziiert werden."""
        from musiai.midi.MusicXmlImporterCompat import MusicXmlImporter
        imp = MusicXmlImporter()
        self.assertTrue(hasattr(imp, 'import_file'))

    def test_import_from_exported_midi_then_musicxml(self):
        """MIDI Export → music21 → MusicXML → Re-Import."""
        from musiai.midi.MidiExporter import MidiExporter
        from musiai.midi.MidiImporter import MidiImporter
        import music21

        piece = make_test_piece()
        midi_path = os.path.join(tempfile.gettempdir(), "wf_mx.mid")
        MidiExporter().export_file(piece, midi_path)

        # music21 konvertiert MIDI → MusicXML
        score = music21.converter.parse(midi_path)
        xml_path = os.path.join(tempfile.gettempdir(), "wf_mx.musicxml")
        score.write("musicxml", xml_path)

        # MusicXML re-importieren
        piece2 = MidiImporter().import_file(xml_path)
        self.assertGreater(len(piece2.parts), 0)
        os.unlink(midi_path)
        os.unlink(xml_path)


# ==============================================================
# PROJEKT SAVE / LOAD
# ==============================================================

class TestWorkflowProjectSaveLoad(unittest.TestCase):
    """Workflow: Projekt speichern und laden."""

    def test_save_creates_file(self):
        from musiai.model.Project import Project
        proj = Project()
        proj.add_piece(make_test_piece())
        path = os.path.join(tempfile.gettempdir(), "wf_save.musiai")
        proj.save(path)
        self.assertTrue(Path(path).exists())
        os.unlink(path)

    def test_load_restores_piece(self):
        from musiai.model.Project import Project
        proj = Project()
        proj.add_piece(make_test_piece())
        path = os.path.join(tempfile.gettempdir(), "wf_load.musiai")
        proj.save(path)
        proj2 = Project()
        proj2.load(path)
        self.assertIsNotNone(proj2.current_piece)
        self.assertEqual(proj2.current_piece.title, "UI-Test-Piece")
        os.unlink(path)

    def test_expression_survives_roundtrip(self):
        from musiai.model.Project import Project
        proj = Project()
        piece = Piece("ExprTest")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1, Expression(110, 15.0, 1.08, "zigzag")))
        m.add_note(Note(64, 1, 1, Expression(40, -20.0, 0.92, "curve")))
        part.add_measure(m)
        piece.add_part(part)
        proj.add_piece(piece)
        path = os.path.join(tempfile.gettempdir(), "wf_expr.musiai")
        proj.save(path)
        proj2 = Project()
        proj2.load(path)
        notes = proj2.current_piece.parts[0].measures[0].notes
        self.assertEqual(notes[0].expression.velocity, 110)
        self.assertAlmostEqual(notes[0].expression.cent_offset, 15.0)
        self.assertEqual(notes[0].expression.glide_type, "zigzag")
        self.assertEqual(notes[1].expression.glide_type, "curve")
        self.assertAlmostEqual(notes[1].expression.duration_deviation, 0.92)
        os.unlink(path)

    def test_tempo_survives_roundtrip(self):
        from musiai.model.Project import Project
        proj = Project()
        piece = Piece("TempoTest")
        piece.tempos = [Tempo(96, 0), Tempo(72, 8), Tempo(140, 16)]
        part = Part("Piano")
        part.add_measure(Measure(1))
        piece.add_part(part)
        proj.add_piece(piece)
        path = os.path.join(tempfile.gettempdir(), "wf_tempo.musiai")
        proj.save(path)
        proj2 = Project()
        proj2.load(path)
        self.assertEqual(len(proj2.current_piece.tempos), 3)
        self.assertAlmostEqual(proj2.current_piece.tempos[1].bpm, 72.0)
        os.unlink(path)


# ==============================================================
# PLAY / PAUSE / STOP
# ==============================================================

class TestWorkflowPlayback(unittest.TestCase):
    """Workflow: Playback Transport Controls."""

    def test_play_sets_state(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.play()
        self.assertEqual(t.state, "playing")
        t.stop()

    def test_pause_preserves_position(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.seek(5.0)
        t.play()
        t.pause()
        self.assertEqual(t.state, "paused")
        self.assertAlmostEqual(t.current_beat, 5.0, delta=0.5)
        t.stop()

    def test_stop_resets_position(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.seek(10.0)
        t.stop()
        self.assertAlmostEqual(t.current_beat, 0.0)

    def test_playhead_moves(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        scene.update_playhead(4.0)
        self.assertTrue(scene.playhead.isVisible())

    def test_playhead_hides_on_stop(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        scene.update_playhead(4.0)
        scene.hide_playhead()
        self.assertFalse(scene.playhead.isVisible())

    def test_playback_engine_plays(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        engine = PlaybackEngine(SignalBus())
        engine.set_piece(make_test_piece())
        engine.play()
        self.assertEqual(engine.transport.state, "playing")
        engine.stop()

    def test_position_signal_emitted(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        positions = []
        t.position_changed.connect(lambda p: positions.append(p))
        t.seek(5.0)
        self.assertEqual(len(positions), 1)


# ==============================================================
# RECORDING
# ==============================================================

class TestWorkflowRecording(unittest.TestCase):
    """Workflow: Expression Recording."""

    def _make_recording_ctrl(self):
        from musiai.controller.RecordingController import RecordingController
        from musiai.midi.MidiKeyboard import MidiKeyboard
        from musiai.midi.MidiMapping import MidiMapping
        from musiai.audio.Transport import Transport
        from musiai.util.SignalBus import SignalBus
        return RecordingController(MidiKeyboard(), MidiMapping(), Transport(), SignalBus())

    def test_toggle_recording(self):
        ctrl = self._make_recording_ctrl()
        ctrl.set_piece(make_test_piece())
        ctrl.toggle_recording()
        self.assertTrue(ctrl.is_recording)
        ctrl.toggle_recording()
        self.assertFalse(ctrl.is_recording)

    def test_recording_signals(self):
        from musiai.controller.RecordingController import RecordingController
        from musiai.midi.MidiKeyboard import MidiKeyboard
        from musiai.midi.MidiMapping import MidiMapping
        from musiai.audio.Transport import Transport
        from musiai.util.SignalBus import SignalBus
        bus = SignalBus()
        ctrl = RecordingController(MidiKeyboard(), MidiMapping(), Transport(), bus)
        ctrl.set_piece(make_test_piece())
        signals = []
        bus.recording_started.connect(lambda: signals.append("start"))
        bus.recording_stopped.connect(lambda: signals.append("stop"))
        ctrl.start_recording()
        ctrl.stop_recording()
        self.assertEqual(signals, ["start", "stop"])


# ==============================================================
# NOTE SELECT / EDIT / DELETE
# ==============================================================

class TestWorkflowSelectAndEdit(unittest.TestCase):
    """Workflow: Note auswählen und bearbeiten."""

    def setUp(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.controller.EditController import EditController
        from musiai.util.SignalBus import SignalBus
        self.bus = SignalBus()
        self.scene = NotationScene()
        self.ctrl = EditController(self.scene, self.bus)
        self.scene.set_piece(make_test_piece())
        self.items = self.scene.get_all_note_items()

    def test_select_note(self):
        self.ctrl.select_note(self.items[0])
        self.assertIsNotNone(self.ctrl.selected_note)

    def test_change_velocity(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_velocity(110)
        self.assertEqual(self.ctrl.selected_note.expression.velocity, 110)

    def test_change_velocity_updates_color(self):
        item = self.items[0]
        self.ctrl.select_note(item)
        color_before = item.brush().color().blue()
        self.ctrl.change_velocity(127)
        color_after = item.brush().color().blue()
        self.assertGreater(color_after, color_before)

    def test_change_cent_offset_zigzag(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_cent_offset(20.0, "zigzag")
        self.assertAlmostEqual(self.ctrl.selected_note.expression.cent_offset, 20.0)
        self.assertEqual(self.ctrl.selected_note.expression.glide_type, "zigzag")

    def test_change_cent_offset_curve(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_cent_offset(-15.0, "curve")
        self.assertEqual(self.ctrl.selected_note.expression.glide_type, "curve")

    def test_change_duration_deviation(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_duration_deviation(1.15)
        self.assertAlmostEqual(self.ctrl.selected_note.expression.duration_deviation, 1.15)

    def test_deselect(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.deselect()
        self.assertIsNone(self.ctrl.selected_note)

    def test_velocity_clamped_high(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_velocity(200)
        self.assertEqual(self.ctrl.selected_note.expression.velocity, 127)

    def test_velocity_clamped_low(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_velocity(-10)
        self.assertEqual(self.ctrl.selected_note.expression.velocity, 0)

    def test_cent_clamped_high(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_cent_offset(100, "zigzag")
        self.assertEqual(self.ctrl.selected_note.expression.cent_offset, 50)

    def test_cent_clamped_low(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_cent_offset(-100, "zigzag")
        self.assertEqual(self.ctrl.selected_note.expression.cent_offset, -50)

    def test_duration_clamped(self):
        self.ctrl.select_note(self.items[0])
        self.ctrl.change_duration_deviation(20.0)
        self.assertAlmostEqual(self.ctrl.selected_note.expression.duration_deviation, 10.0)
        self.ctrl.change_duration_deviation(0.01)
        self.assertAlmostEqual(self.ctrl.selected_note.expression.duration_deviation, 0.10)


class TestWorkflowDeleteNote(unittest.TestCase):
    """Workflow: Note löschen."""

    def test_delete_reduces_count(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.controller.EditController import EditController
        from musiai.util.SignalBus import SignalBus
        scene = NotationScene()
        ctrl = EditController(scene, SignalBus())
        piece = make_test_piece()
        scene.set_piece(piece)
        total_before = sum(len(m.notes) for m in piece.parts[0].measures)
        items = scene.get_all_note_items()
        ctrl.select_note(items[0])
        ctrl.delete_selected()
        total_after = sum(len(m.notes) for m in piece.parts[0].measures)
        self.assertEqual(total_after, total_before - 1)

    def test_delete_without_selection_does_nothing(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.controller.EditController import EditController
        from musiai.util.SignalBus import SignalBus
        scene = NotationScene()
        ctrl = EditController(scene, SignalBus())
        piece = make_test_piece()
        scene.set_piece(piece)
        total_before = sum(len(m.notes) for m in piece.parts[0].measures)
        ctrl.delete_selected()  # Nichts selektiert
        total_after = sum(len(m.notes) for m in piece.parts[0].measures)
        self.assertEqual(total_after, total_before)


class TestWorkflowAddNote(unittest.TestCase):
    """Workflow: Note hinzufügen."""

    def test_add_note_to_measure(self):
        piece = make_test_piece()
        m = piece.parts[0].measures[0]
        count_before = len(m.notes)
        new_note = Note(65, 0.5, 0.5, Expression(90))
        m.add_note(new_note)
        self.assertEqual(len(m.notes), count_before + 1)

    def test_added_note_sorted(self):
        m = Measure(1)
        m.add_note(Note(60, 2.0, 1.0))
        m.add_note(Note(64, 0.0, 1.0))
        m.add_note(Note(62, 1.0, 1.0))
        beats = [n.start_beat for n in m.notes]
        self.assertEqual(beats, [0.0, 1.0, 2.0])

    def test_added_note_renders(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = make_test_piece()
        m = piece.parts[0].measures[0]
        m.add_note(Note(65, 0.5, 0.5))
        scene.set_piece(piece)
        self.assertEqual(len(scene.get_all_note_items()), 14)  # 13 + 1


class TestWorkflowAddMeasure(unittest.TestCase):
    """Workflow: Takt hinzufügen."""

    def test_add_measure_to_part(self):
        piece = make_test_piece()
        part = piece.parts[0]
        count_before = len(part.measures)
        new_measure = Measure(count_before + 1, TimeSignature(4, 4))
        new_measure.add_note(Note(60, 0, 1))
        part.add_measure(new_measure)
        self.assertEqual(len(part.measures), count_before + 1)

    def test_added_measure_renders(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = make_test_piece()
        new_m = Measure(5, TimeSignature(4, 4))
        new_m.add_note(Note(60, 0, 2))
        piece.parts[0].add_measure(new_m)
        scene.set_piece(piece)
        self.assertEqual(len(scene.measure_renderers), 5)

    def test_measure_with_different_time_signature(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = make_test_piece()
        new_m = Measure(5, TimeSignature(6, 8))
        new_m.add_note(Note(60, 0, 1.5))
        piece.parts[0].add_measure(new_m)
        scene.set_piece(piece)
        widths = [r.width for r in scene.measure_renderers]
        # 6/8 = 3 beats, Tempo 100 → scale 120/100 = 1.2
        self.assertAlmostEqual(widths[4], 3.0 * 80 * 1.2)  # 288


# ==============================================================
# COPY / PASTE
# ==============================================================

class TestWorkflowCopyPaste(unittest.TestCase):
    """Workflow: Noten kopieren und einfügen."""

    def test_copy_note(self):
        """Note kopieren = neues Note-Objekt mit gleichen Werten."""
        original = Note(60, 0, 1, Expression(110, 15.0, 1.1, "zigzag"))
        copied = Note.from_dict(original.to_dict())
        self.assertEqual(copied.pitch, original.pitch)
        self.assertEqual(copied.expression.velocity, original.expression.velocity)
        self.assertAlmostEqual(copied.expression.cent_offset, original.expression.cent_offset)
        self.assertIsNot(copied, original)

    def test_paste_note_into_measure(self):
        m = Measure(1)
        original = Note(60, 0, 1, Expression(110))
        copied = Note.from_dict(original.to_dict())
        copied.start_beat = 2.0  # An neue Position
        m.add_note(copied)
        self.assertEqual(len(m.notes), 1)
        self.assertEqual(m.notes[0].start_beat, 2.0)

    def test_copy_measure(self):
        """Ganzen Takt kopieren."""
        m = Measure(1, TimeSignature(3, 4))
        m.add_note(Note(60, 0, 1, Expression(110, 5.0)))
        m.add_note(Note(64, 1, 1, Expression(90, -10.0)))
        copied = Measure.from_dict(m.to_dict())
        copied.number = 2
        self.assertEqual(len(copied.notes), 2)
        self.assertEqual(copied.notes[0].expression.velocity, 110)
        self.assertEqual(copied.time_signature.numerator, 3)


# ==============================================================
# EXPRESSION VISUALS
# ==============================================================

class TestWorkflowExpressionVisuals(unittest.TestCase):
    """Workflow: Expression-Zeichen setzen und visualisieren."""

    def test_velocity_color_gradient(self):
        """Volle Farbskala: Gelb → Rot → Blau."""
        from musiai.notation.ColorScheme import ColorScheme
        yellow = ColorScheme.velocity_to_color(0)
        red = ColorScheme.velocity_to_color(80)
        blue = ColorScheme.velocity_to_color(127)
        self.assertEqual(yellow.green(), 255)  # Gelb hat grün
        self.assertEqual(red.red(), 255)       # Rot
        self.assertEqual(blue.blue(), 255)     # Blau

    def test_zigzag_for_instant_cent(self):
        from musiai.notation.ZigzagItem import ZigzagItem
        z = ZigzagItem(25.0, 50, 50)
        self.assertEqual(z.cents, 25.0)

    def test_curve_for_glide_cent(self):
        from musiai.notation.CurveItem import CurveItem
        c = CurveItem(-15.0, 50, 50)
        self.assertEqual(c.cents, -15.0)

    def test_duration_color_short(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.duration_to_color(0.85)
        self.assertGreater(c.red(), 200)  # Rot-Gelb

    def test_duration_color_long(self):
        from musiai.notation.ColorScheme import ColorScheme
        c = ColorScheme.duration_to_color(1.15)
        self.assertGreater(c.blue(), 150)  # Blau

    def test_duration_item_text_standard(self):
        from musiai.notation.DurationItem import DurationItem
        d = DurationItem(1.0, 50, 50)
        self.assertEqual(d.text(), "+0.00")

    def test_duration_item_text_deviation(self):
        from musiai.notation.DurationItem import DurationItem
        d = DurationItem(0.85, 50, 50)
        self.assertEqual(d.text(), "-0.15")
        d2 = DurationItem(1.2, 50, 50)
        self.assertEqual(d2.text(), "+0.20")

    def test_proportional_measure_width(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        widths = [r.width for r in scene.measure_renderers]
        self.assertLess(widths[2], widths[0])  # 3/4 < 4/4


# ==============================================================
# DIATONIC NOTE POSITIONING
# ==============================================================

class TestDiatonicPositioning(unittest.TestCase):
    """Noten sitzen auf den korrekten Notenlinien (diatonisch)."""

    def _pitch_y(self, midi_pitch, center_y=200):
        from musiai.notation.MeasureRenderer import MeasureRenderer
        from musiai.model.Measure import Measure
        r = MeasureRenderer(Measure(), 0, center_y, effective_tempo=120)
        return r.pitch_to_y(midi_pitch)

    def test_b4_on_middle_line(self):
        """B4 (MIDI 71) = 3. Linie = center_y."""
        self.assertAlmostEqual(self._pitch_y(71), 200)

    def test_e4_on_bottom_line(self):
        """E4 (MIDI 64) = 1. Linie = center_y + 24."""
        self.assertAlmostEqual(self._pitch_y(64), 224)

    def test_f5_on_top_line(self):
        """F5 (MIDI 77) = 5. Linie = center_y - 24."""
        self.assertAlmostEqual(self._pitch_y(77), 176)

    def test_g4_on_second_line(self):
        """G4 (MIDI 67) = 2. Linie = center_y + 12."""
        self.assertAlmostEqual(self._pitch_y(67), 212)

    def test_d5_on_fourth_line(self):
        """D5 (MIDI 74) = 4. Linie = center_y - 12."""
        self.assertAlmostEqual(self._pitch_y(74), 188)

    def test_c5_in_space(self):
        """C5 (MIDI 72) = Zwischenraum über 3. Linie."""
        y = self._pitch_y(72)
        self.assertLess(y, 200)    # Über center_y
        self.assertGreater(y, 188)  # Unter 4. Linie


# ==============================================================
# TEMPO AFFECTS MEASURE WIDTH
# ==============================================================

class TestTempoMeasureWidth(unittest.TestCase):
    """Tempo beeinflusst die visuelle Taktbreite."""

    def test_slow_tempo_wider(self):
        """Langsames Tempo → breitere Takte."""
        from musiai.notation.MeasureRenderer import MeasureRenderer
        from musiai.model.Measure import Measure
        m = Measure()
        r_normal = MeasureRenderer(m, 0, 100, effective_tempo=120)
        r_slow = MeasureRenderer(m, 0, 100, effective_tempo=60)
        self.assertGreater(r_slow.width, r_normal.width)

    def test_fast_tempo_narrower(self):
        """Schnelles Tempo → schmalere Takte."""
        from musiai.notation.MeasureRenderer import MeasureRenderer
        from musiai.model.Measure import Measure
        m = Measure()
        r_normal = MeasureRenderer(m, 0, 100, effective_tempo=120)
        r_fast = MeasureRenderer(m, 0, 100, effective_tempo=240)
        self.assertLess(r_fast.width, r_normal.width)

    def test_reference_tempo_scale_1(self):
        """Bei 120 BPM ist tempo_scale = 1.0."""
        from musiai.notation.MeasureRenderer import MeasureRenderer
        from musiai.model.Measure import Measure
        r = MeasureRenderer(Measure(), 0, 100, effective_tempo=120)
        self.assertAlmostEqual(r.tempo_scale, 1.0)

    def test_tempo_change_updates_scene(self):
        """Tempo ändern → Scene hat neue Breiten."""
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        piece = make_test_piece()
        scene.set_piece(piece)
        w_before = [r.width for r in scene.measure_renderers]
        piece.tempos[0].bpm = 60
        for m in piece.parts[0].measures:
            if m.tempo:
                m.tempo.bpm = 60
        scene.refresh()
        w_after = [r.width for r in scene.measure_renderers]
        for wb, wa in zip(w_before, w_after):
            self.assertGreater(wa, wb)


# ==============================================================
# EDIT MODE
# ==============================================================

class TestEditMode(unittest.TestCase):
    """Edit Mode mit Cursor."""

    def test_cursor_item_exists(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        self.assertIsNotNone(scene.cursor)

    def test_cursor_hidden_by_default(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        self.assertFalse(scene.cursor.isVisible())

    def test_update_cursor_shows(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        scene.update_cursor(2.0)
        self.assertTrue(scene.cursor.isVisible())

    def test_hide_cursor(self):
        from musiai.notation.NotationScene import NotationScene
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        scene.update_cursor(2.0)
        scene.hide_cursor()
        self.assertFalse(scene.cursor.isVisible())


# ==============================================================
# DURATION DEVIATION
# ==============================================================

class TestDurationDeviation(unittest.TestCase):
    """Dauer-Abweichung einer Note ändern."""

    def test_change_deviation(self):
        """Deviation wird korrekt gesetzt."""
        scene, ec = self._make_scene_and_controller()
        ni = scene.get_all_note_items()[0]
        ec.select_note(ni)
        ec.change_duration_deviation(0.9)
        self.assertAlmostEqual(ni.note.expression.duration_deviation, 0.9)

    def test_deviation_clamped(self):
        """Deviation wird auf 0.10-10.0 begrenzt."""
        scene, ec = self._make_scene_and_controller()
        ni = scene.get_all_note_items()[0]
        ec.select_note(ni)
        ec.change_duration_deviation(0.01)
        self.assertAlmostEqual(ni.note.expression.duration_deviation, 0.10)
        ec.change_duration_deviation(20.0)
        self.assertAlmostEqual(ni.note.expression.duration_deviation, 10.0)

    def test_deviation_creates_duration_item(self):
        """Nach Deviation != 1.0 wird DurationItem erzeugt."""
        from musiai.notation.DurationItem import DurationItem
        scene, ec = self._make_scene_and_controller()
        ni = scene.get_all_note_items()[0]
        ec.select_note(ni)
        ec.change_duration_deviation(1.15)
        items = [i for i in scene.items() if isinstance(i, DurationItem)]
        self.assertGreater(len(items), 0)

    def _make_scene_and_controller(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.controller.EditController import EditController
        from musiai.util.SignalBus import SignalBus
        scene = NotationScene()
        scene.set_piece(make_test_piece())
        bus = SignalBus()
        ec = EditController(scene, bus)
        return scene, ec


# ==============================================================
# NEUE STIMME
# ==============================================================

class TestNeueStimme(unittest.TestCase):
    """Neue Stimme hinzufügen."""

    def test_add_voice(self):
        piece = make_test_piece()
        self.assertEqual(len(piece.parts), 1)
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        new_part = Part("Stimme 2", 1)
        for m in piece.parts[0].measures:
            new_part.add_measure(Measure(m.number, m.time_signature))
        piece.add_part(new_part)
        self.assertEqual(len(piece.parts), 2)
        self.assertEqual(len(piece.parts[1].measures), len(piece.parts[0].measures))

    def test_new_voice_renders(self):
        from musiai.notation.NotationScene import NotationScene
        piece = make_test_piece()
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        new_part = Part("Stimme 2")
        for m in piece.parts[0].measures:
            new_part.add_measure(Measure(m.number, m.time_signature))
        piece.add_part(new_part)
        scene = NotationScene()
        scene.set_piece(piece)
        # Beide Parts gerendert: doppelte Taktanzahl
        n_measures = len(piece.parts[0].measures) + len(piece.parts[1].measures)
        self.assertEqual(len(scene.measure_renderers), n_measures)


# ==============================================================
# CORRECT PLAYBACK WITH EXPRESSION
# ==============================================================

class TestWorkflowCorrectPlayback(unittest.TestCase):
    """Workflow: Noten korrekt abspielen (Velocity, Cent, Duration)."""

    def test_playback_engine_note_list(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        engine = PlaybackEngine(SignalBus())
        engine.set_piece(make_test_piece())
        self.assertEqual(len(engine._all_notes), 13)

    def test_playback_engine_notes_sorted(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        engine = PlaybackEngine(SignalBus())
        engine.set_piece(make_test_piece())
        beats = [ab for ab, *_ in engine._all_notes]
        self.assertEqual(beats, sorted(beats))

    def test_pitch_bend_calculation(self):
        from musiai.util.PitchUtils import cents_to_pitch_bend
        self.assertEqual(cents_to_pitch_bend(0), 8192)
        self.assertGreater(cents_to_pitch_bend(25), 8192)
        self.assertLess(cents_to_pitch_bend(-25), 8192)


# ==============================================================
# PROPERTIES PANEL
# ==============================================================

class TestWorkflowPropertiesPanel(unittest.TestCase):
    """Workflow: Properties Panel zeigt und editiert Werte."""

    def test_show_note_values(self):
        from musiai.ui.PropertiesPanel import PropertiesPanel
        panel = PropertiesPanel()
        n = Note(60, 0, 1, Expression(100, 15.0, 1.05, "zigzag"))
        panel.show_note(n)
        self.assertEqual(panel._vel_slider.value(), 100)
        self.assertEqual(panel._cent_slider.value(), 15)
        self.assertAlmostEqual(panel._dur_spin.value(), 1.05)

    def test_clear_shows_empty(self):
        from musiai.ui.PropertiesPanel import PropertiesPanel
        panel = PropertiesPanel()
        panel.show_note(Note(60, 0, 1, Expression(100)))
        panel.clear()
        self.assertEqual(panel._stack.currentIndex(), 0)  # Leere Seite

    def test_velocity_signal(self):
        from musiai.ui.PropertiesPanel import PropertiesPanel
        panel = PropertiesPanel()
        panel.show_note(Note(60, 0, 1))
        received = []
        panel.velocity_changed.connect(lambda v: received.append(v))
        panel._vel_slider.setValue(110)
        self.assertEqual(received, [110])

    def test_cent_signal(self):
        from musiai.ui.PropertiesPanel import PropertiesPanel
        panel = PropertiesPanel()
        panel.show_note(Note(60, 0, 1))
        received = []
        panel.cent_offset_changed.connect(lambda c: received.append(c))
        panel._cent_slider.setValue(20)
        self.assertAlmostEqual(received[0], 20.0)


# ==============================================================
# FULL INTEGRATION
# ==============================================================

class TestWorkflowFullIntegration(unittest.TestCase):
    """Workflow: Kompletter AppController Lifecycle."""

    def test_app_lifecycle(self):
        from musiai.controller.AppController import AppController
        ctrl = AppController()
        piece = make_test_piece()
        ctrl.project.add_piece(piece)
        ctrl.signal_bus.piece_loaded.emit(piece)

        items = ctrl.notation_scene.get_all_note_items()
        self.assertEqual(len(items), 13)

        ctrl.edit_controller.select_note(items[0])
        ctrl.edit_controller.change_velocity(100)

        ctrl.playback_engine.play()
        self.assertEqual(ctrl.playback_engine.transport.state, "playing")
        ctrl.playback_engine.stop()

        ctrl.shutdown()

    def test_edit_and_save_persists(self):
        from musiai.controller.AppController import AppController
        ctrl = AppController()
        piece = make_test_piece()
        ctrl.project.add_piece(piece)
        ctrl.signal_bus.piece_loaded.emit(piece)

        items = ctrl.notation_scene.get_all_note_items()
        ctrl.edit_controller.select_note(items[0])
        ctrl.edit_controller.change_velocity(115)
        ctrl.edit_controller.change_cent_offset(20.0, "curve")

        path = os.path.join(tempfile.gettempdir(), "wf_integ.musiai")
        ctrl.project.save(path)

        from musiai.model.Project import Project
        proj2 = Project()
        proj2.load(path)
        # Mindestens eine Note sollte velocity=115 haben
        found = False
        for p in proj2.current_piece.parts:
            for m in p.measures:
                for n in m.notes:
                    if n.expression.velocity == 115:
                        found = True
        self.assertTrue(found)
        ctrl.shutdown()
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
