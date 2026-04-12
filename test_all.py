"""Umfassender Test aller MusiAI-Komponenten."""

import sys
import json
import logging
from pathlib import Path

# Logging
from musiai.util.LoggingConfig import setup_logging
logger = setup_logging(logging.DEBUG)

# Muss vor Qt-Widgets importiert werden
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

PASS = 0
FAIL = 0


def test(name: str, func):
    global PASS, FAIL
    try:
        func()
        PASS += 1
        logger.info(f"  PASS: {name}")
    except Exception as e:
        FAIL += 1
        logger.error(f"  FAIL: {name}: {e}", exc_info=True)


def section(name: str):
    logger.info(f"\n{'='*60}")
    logger.info(f"  {name}")
    logger.info(f"{'='*60}")


# ==============================================================
#  1. MODEL TESTS
# ==============================================================
section("1. Model Tests")

def test_expression():
    from musiai.model.Expression import Expression
    e = Expression(velocity=100, cent_offset=4.0, glide_type="zigzag")
    d = e.to_dict()
    e2 = Expression.from_dict(d)
    assert e2.velocity == 100
    assert e2.cent_offset == 4.0
    assert e2.glide_type == "zigzag"
    assert e2.duration_deviation == 1.0

test("Expression create & serialize", test_expression)

def test_time_signature():
    from musiai.model.TimeSignature import TimeSignature
    assert TimeSignature(4, 4).beats_per_measure() == 4.0
    assert TimeSignature(3, 4).beats_per_measure() == 3.0
    assert TimeSignature(6, 8).beats_per_measure() == 3.0

test("TimeSignature beats_per_measure", test_time_signature)

def test_tempo():
    from musiai.model.Tempo import Tempo
    t = Tempo(120.0)
    assert t.seconds_per_beat() == 0.5
    d = t.to_dict()
    t2 = Tempo.from_dict(d)
    assert t2.bpm == 120.0

test("Tempo calculate & serialize", test_tempo)

def test_note():
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression
    n = Note(pitch=60, start_beat=0.0, duration_beats=1.0,
             expression=Expression(velocity=110, cent_offset=-10))
    assert n.name == "C4"
    assert n.end_beat == 1.0
    assert n.frequency < 261.63  # Tiefer wegen neg. Cent
    d = n.to_dict()
    n2 = Note.from_dict(d)
    assert n2.expression.velocity == 110
    assert n2.expression.cent_offset == -10

test("Note properties & serialize", test_note)

def test_measure():
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    m = Measure(number=1)
    m.add_note(Note(64, 2.0, 1.0))
    m.add_note(Note(60, 0.0, 1.0))  # Ungeordnet
    assert m.notes[0].pitch == 60  # Sortiert
    assert m.get_note_at(2.0).pitch == 64
    m.remove_note(m.notes[0])
    assert len(m.notes) == 1

test("Measure add/find/remove notes", test_measure)

def test_part():
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    p = Part(name="Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1))
    p.add_measure(m)
    assert len(p.get_all_notes()) == 1

test("Part manage measures", test_part)

def test_piece():
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Tempo import Tempo
    piece = Piece(title="Test")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1))
    part.add_measure(m)
    piece.add_part(part)
    piece.tempos = [Tempo(100, 0), Tempo(80, 4)]
    assert piece.tempo_at_beat(2) == 100
    assert piece.tempo_at_beat(6) == 80

test("Piece tempo changes", test_piece)

def test_project_save_load():
    from musiai.model.Project import Project
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression

    proj = Project()
    piece = Piece("SaveTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1, Expression(90, 5.0, 1.05, "zigzag")))
    part.add_measure(m)
    piece.add_part(part)
    proj.add_piece(piece)

    path = "media/projects/test_all.musiai"
    proj.save(path)
    proj2 = Project()
    proj2.load(path)
    n = proj2.current_piece.parts[0].measures[0].notes[0]
    assert n.expression.velocity == 90
    assert n.expression.cent_offset == 5.0
    assert n.expression.glide_type == "zigzag"

test("Project save/load JSON", test_project_save_load)


# ==============================================================
#  2. UTIL TESTS
# ==============================================================
section("2. Util Tests")

def test_pitch_utils():
    from musiai.util.PitchUtils import (
        midi_to_frequency, frequency_to_midi, note_name,
        name_to_midi, cents_to_pitch_bend
    )
    assert note_name(60) == "C4"
    assert name_to_midi("A4") == 69
    assert abs(midi_to_frequency(69) - 440.0) < 0.01
    m, c = frequency_to_midi(440.0)
    assert m == 69 and abs(c) < 0.1
    assert cents_to_pitch_bend(0) == 8192

test("Pitch utils", test_pitch_utils)

def test_constants():
    from musiai.util.Constants import DEFAULT_VELOCITY, PIXELS_PER_BEAT
    assert DEFAULT_VELOCITY == 80
    assert PIXELS_PER_BEAT == 80

test("Constants", test_constants)


# ==============================================================
#  3. NOTATION TESTS
# ==============================================================
section("3. Notation Tests")

def test_color_scheme():
    from musiai.notation.ColorScheme import ColorScheme
    # Velocity: gelb(0) → rot(80) → blau(127)
    yellow = ColorScheme.velocity_to_color(0)
    assert yellow.red() == 255 and yellow.green() == 255  # Gelb
    red = ColorScheme.velocity_to_color(80)
    assert red.red() == 255 and red.green() == 0  # Rot
    blue = ColorScheme.velocity_to_color(127)
    assert blue.blue() == 255 and blue.red() == 0  # Blau

    # Duration
    short_c = ColorScheme.duration_to_color(0.8)
    assert short_c.red() > 200  # Rot-Gelb
    long_c = ColorScheme.duration_to_color(1.2)
    assert long_c.blue() > 200  # Blau
    std_c = ColorScheme.duration_to_color(1.0)
    assert std_c.red() == 100  # Grau

test("ColorScheme velocity & duration", test_color_scheme)

def test_notation_scene():
    from musiai.notation.NotationScene import NotationScene
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression

    scene = NotationScene()
    piece = Piece("SceneTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1, Expression(100, 4.0, 1.05, "zigzag")))
    m.add_note(Note(64, 1, 1, Expression(40, -10.0, 0.9, "curve")))
    m.add_note(Note(67, 2, 1))
    part.add_measure(m)
    piece.add_part(part)
    scene.set_piece(piece)

    items = scene.get_all_note_items()
    assert len(items) == 3
    assert len(scene.measure_renderers) == 1

test("NotationScene render piece", test_notation_scene)

def test_note_item():
    from musiai.notation.NoteItem import NoteItem
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression
    n = Note(60, 0, 1, Expression(velocity=120))
    item = NoteItem(n, 100, 100)
    assert item.note is n
    item.set_selected_visual(True)
    item.set_selected_visual(False)
    n.expression.velocity = 30
    item.update_from_note()

test("NoteItem create & update", test_note_item)

def test_zigzag_item():
    from musiai.notation.ZigzagItem import ZigzagItem
    z = ZigzagItem(20.0, 100, 100)
    assert z.cents == 20.0
    z.update_cents(-15.0)
    assert z.cents == -15.0

test("ZigzagItem create & update", test_zigzag_item)

def test_curve_item():
    from musiai.notation.CurveItem import CurveItem
    c = CurveItem(30.0, 100, 100)
    assert c.cents == 30.0
    c.update_cents(-20.0)
    assert c.cents == -20.0

test("CurveItem create & update", test_curve_item)

def test_duration_item():
    from musiai.notation.DurationItem import DurationItem
    d = DurationItem(1.1, 100, 100)
    assert d.isVisible()
    d.update_deviation(1.0)
    assert not d.isVisible()  # Standard = unsichtbar

test("DurationItem visibility", test_duration_item)

def test_playhead_item():
    from musiai.notation.PlayheadItem import PlayheadItem
    p = PlayheadItem()
    assert not p.isVisible()
    p.show_at(200)
    assert p.isVisible()
    p.hide()
    assert not p.isVisible()

test("PlayheadItem show/hide", test_playhead_item)


# ==============================================================
#  4. MIDI TESTS
# ==============================================================
section("4. MIDI Tests")

def test_midi_mapping():
    from musiai.midi.MidiMapping import MidiMapping
    m = MidiMapping()
    result = m.map_cc(1, 100)  # Mod Wheel
    assert result == ("velocity", 100.0)
    result = m.map_cc(11, 64)  # Expression
    assert result[0] == "duration"
    assert 0.9 < result[1] < 1.1  # Mitte ≈ 1.0
    cents = m.map_pitch_bend(8192)  # Mitte
    assert abs(cents) < 0.1
    cents = m.map_pitch_bend(16383)  # Maximum
    assert cents > 40

test("MidiMapping CC & pitch bend", test_midi_mapping)

def test_midi_keyboard_list():
    from musiai.midi.MidiKeyboard import MidiKeyboard
    # list_ports soll nicht crashen, auch ohne Geräte
    ports = MidiKeyboard.list_ports()
    assert isinstance(ports, list)

test("MidiKeyboard list_ports", test_midi_keyboard_list)

def test_midi_exporter():
    from musiai.midi.MidiExporter import MidiExporter
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression

    piece = Piece("ExportTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1, Expression(100, 5.0, 1.0, "zigzag")))
    m.add_note(Note(64, 1, 1, Expression(80, 0, 1.0)))
    part.add_measure(m)
    piece.add_part(part)

    exporter = MidiExporter()
    path = "media/music/test_export.mid"
    exporter.export_file(piece, path)
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

test("MidiExporter write MIDI", test_midi_exporter)


# ==============================================================
#  5. AUDIO TESTS
# ==============================================================
section("5. Audio Tests")

def test_transport():
    from musiai.audio.Transport import Transport
    t = Transport()
    assert t.state == "stopped"
    assert t.current_beat == 0.0
    t.tempo_bpm = 120
    t.set_end_beat(16.0)
    t.seek(4.0)
    assert t.current_beat == 4.0
    # Play/Stop ohne Timer laufen zu lassen
    t.play()
    assert t.state == "playing"
    t.pause()
    assert t.state == "paused"
    t.stop()
    assert t.state == "stopped"
    assert t.current_beat == 0.0

test("Transport play/pause/stop/seek", test_transport)

def test_playback_engine():
    from musiai.audio.PlaybackEngine import PlaybackEngine
    from musiai.util.SignalBus import SignalBus
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note

    bus = SignalBus()
    engine = PlaybackEngine(bus)
    piece = Piece("EngineTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1))
    part.add_measure(m)
    piece.add_part(part)
    engine.set_piece(piece)
    assert len(engine._all_notes) == 1

test("PlaybackEngine set_piece", test_playback_engine)


# ==============================================================
#  6. UI TESTS
# ==============================================================
section("6. UI Tests")

def test_main_window():
    from musiai.ui.MainWindow import MainWindow
    from musiai.notation.NotationScene import NotationScene
    w = MainWindow()
    scene = NotationScene()
    w.set_notation_scene(scene)
    assert w.notation_view is not None
    assert w.toolbar is not None
    assert w.status_bar is not None
    assert w.properties_panel is not None

test("MainWindow creation", test_main_window)

def test_properties_panel():
    from musiai.ui.PropertiesPanel import PropertiesPanel
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression
    p = PropertiesPanel()
    n = Note(60, 0, 1, Expression(100, 5.0, 1.05, "zigzag"))
    p.show_note(n)
    assert p._vel_slider.value() == 100
    assert p._cent_slider.value() == 5
    p.clear()

test("PropertiesPanel show_note", test_properties_panel)

def test_status_bar():
    from musiai.ui.StatusBar import StatusBar
    s = StatusBar()
    s.set_position(3, 2.5)
    s.set_midi_status(True, "Keyboard")
    s.set_midi_status(False)
    s.set_message("Test")

test("StatusBar updates", test_status_bar)


# ==============================================================
#  7. CONTROLLER TESTS
# ==============================================================
section("7. Controller Tests")

def test_edit_controller():
    from musiai.controller.EditController import EditController
    from musiai.notation.NotationScene import NotationScene
    from musiai.notation.NoteItem import NoteItem
    from musiai.util.SignalBus import SignalBus
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression

    bus = SignalBus()
    scene = NotationScene()
    ctrl = EditController(scene, bus)

    # Piece rendern
    piece = Piece("EditTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1, Expression(80)))
    m.add_note(Note(64, 1, 1, Expression(80)))
    part.add_measure(m)
    piece.add_part(part)
    scene.set_piece(piece)

    # Note auswählen
    items = scene.get_all_note_items()
    assert len(items) == 2
    ctrl.select_note(items[0])
    assert ctrl.selected_note is not None

    # Velocity ändern
    ctrl.change_velocity(110)
    assert ctrl.selected_note.expression.velocity == 110

    # Cent ändern
    ctrl.change_cent_offset(15.0, "zigzag")
    assert ctrl.selected_note.expression.cent_offset == 15.0
    assert ctrl.selected_note.expression.glide_type == "zigzag"

    # Duration ändern
    ctrl.change_duration_deviation(1.1)
    assert ctrl.selected_note.expression.duration_deviation == 1.1

    # Deselect
    ctrl.deselect()
    assert ctrl.selected_note is None

test("EditController select/edit/deselect", test_edit_controller)

def test_edit_controller_delete():
    from musiai.controller.EditController import EditController
    from musiai.notation.NotationScene import NotationScene
    from musiai.util.SignalBus import SignalBus
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note

    bus = SignalBus()
    scene = NotationScene()
    ctrl = EditController(scene, bus)

    piece = Piece("DeleteTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 1))
    m.add_note(Note(64, 1, 1))
    part.add_measure(m)
    piece.add_part(part)
    scene.set_piece(piece)

    items = scene.get_all_note_items()
    ctrl.select_note(items[0])
    ctrl.delete_selected()
    # Nach Delete und Refresh: nur noch 1 Note
    assert len(piece.parts[0].measures[0].notes) == 1

test("EditController delete note", test_edit_controller_delete)

def test_recording_controller():
    from musiai.controller.RecordingController import RecordingController
    from musiai.midi.MidiKeyboard import MidiKeyboard
    from musiai.midi.MidiMapping import MidiMapping
    from musiai.audio.Transport import Transport
    from musiai.util.SignalBus import SignalBus
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note

    bus = SignalBus()
    kb = MidiKeyboard()
    mapping = MidiMapping()
    transport = Transport()
    ctrl = RecordingController(kb, mapping, transport, bus)

    piece = Piece("RecTest")
    part = Part("Piano")
    m = Measure(1)
    m.add_note(Note(60, 0, 2))
    part.add_measure(m)
    piece.add_part(part)
    ctrl.set_piece(piece)

    assert len(ctrl._all_notes) == 1
    ctrl.start_recording()
    assert ctrl.is_recording
    ctrl.stop_recording()
    assert not ctrl.is_recording

test("RecordingController setup", test_recording_controller)


# ==============================================================
#  8. INTEGRATION TEST
# ==============================================================
section("8. Integration Test")

def test_app_controller():
    from musiai.controller.AppController import AppController
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression

    ctrl = AppController()

    # Piece programmatisch laden
    piece = Piece("IntegrationTest")
    part = Part("Piano")
    for i in range(4):
        m = Measure(i + 1)
        m.add_note(Note(60 + i * 2, 0, 1, Expression(60 + i * 20)))
        m.add_note(Note(64 + i * 2, 1, 1, Expression(60 + i * 20, i * 5.0, 1.0, "zigzag" if i % 2 else "none")))
        m.add_note(Note(67 + i * 2, 2, 1, Expression(60 + i * 20, 0, 0.9 + i * 0.05)))
        part.add_measure(m)
    piece.add_part(part)

    ctrl.project.add_piece(piece)
    ctrl.signal_bus.piece_loaded.emit(piece)

    # Prüfung
    items = ctrl.notation_scene.get_all_note_items()
    assert len(items) == 12  # 4 Takte × 3 Noten
    assert len(ctrl.notation_scene.measure_renderers) == 4

    # Note auswählen und bearbeiten
    ctrl.edit_controller.select_note(items[0])
    ctrl.edit_controller.change_velocity(120)
    assert items[0].note.expression.velocity == 120

    ctrl.shutdown()

test("AppController full integration", test_app_controller)


# ==============================================================
#  ERGEBNIS
# ==============================================================
section("ERGEBNIS")
total = PASS + FAIL
logger.info(f"  {PASS}/{total} Tests bestanden")
if FAIL > 0:
    logger.error(f"  {FAIL} Tests FEHLGESCHLAGEN!")
else:
    logger.info(f"  ALLE TESTS BESTANDEN!")

print(f"\n{'='*60}")
print(f"  {PASS}/{total} Tests bestanden", "- ALLE OK!" if FAIL == 0 else f"- {FAIL} FEHLGESCHLAGEN!")
print(f"{'='*60}")

sys.exit(1 if FAIL > 0 else 0)
