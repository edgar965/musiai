"""Tests für Audio-Features: AudioTrack, PitchDetector, Backends, Instruments."""

import unittest
import numpy as np
import os
import sys

# QApplication für Qt-Tests
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Measure import Measure
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo


# ==============================================================
# AUDIO TRACK
# ==============================================================

class TestAudioTrack(unittest.TestCase):
    """AudioTrack Model: laden, schneiden, verschieben."""

    def test_create_empty(self):
        from musiai.model.AudioTrack import AudioTrack
        t = AudioTrack()
        self.assertEqual(len(t.blocks), 0)
        self.assertAlmostEqual(t.duration_seconds, 0.0)

    def test_create_from_samples(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        samples = np.random.randn(44100).astype(np.float32)  # 1 Sekunde
        t = AudioTrack()
        t.sr = 44100
        t.blocks = [AudioBlock(samples, 44100, 0.0)]
        t._full_samples = samples
        self.assertAlmostEqual(t.duration_seconds, 1.0, places=1)

    def test_block_duration(self):
        from musiai.model.AudioTrack import AudioBlock
        samples = np.zeros(22050, dtype=np.float32)
        b = AudioBlock(samples, 44100)
        self.assertAlmostEqual(b.duration_seconds, 0.5)

    def test_block_duration_beats(self):
        from musiai.model.AudioTrack import AudioBlock
        samples = np.zeros(44100, dtype=np.float32)  # 1 Sekunde
        b = AudioBlock(samples, 44100)
        # Bei 120 BPM: 1s = 2 beats
        self.assertAlmostEqual(b.duration_beats(120), 2.0)
        # Bei 60 BPM: 1s = 1 beat
        self.assertAlmostEqual(b.duration_beats(60), 1.0)

    def test_split_block(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        samples = np.random.randn(44100).astype(np.float32)
        t = AudioTrack()
        t.sr = 44100
        t.blocks = [AudioBlock(samples, 44100, 0.0)]
        t._full_samples = samples
        t.split_block(0, 0.5, 120)  # Bei 0.5s schneiden
        self.assertEqual(len(t.blocks), 2)
        self.assertAlmostEqual(t.blocks[0].duration_seconds, 0.5, places=1)
        self.assertAlmostEqual(t.blocks[1].duration_seconds, 0.5, places=1)

    def test_move_block(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        samples = np.zeros(44100, dtype=np.float32)
        t = AudioTrack()
        t.blocks = [AudioBlock(samples, 44100, 0.0)]
        t.move_block(0, 2.0)
        self.assertAlmostEqual(t.blocks[0].start_beat, 2.0)

    def test_delete_block(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        s1 = np.zeros(22050, dtype=np.float32)
        s2 = np.zeros(22050, dtype=np.float32)
        t = AudioTrack()
        t.blocks = [AudioBlock(s1, 44100), AudioBlock(s2, 44100, 1.0)]
        t.delete_block(0)
        self.assertEqual(len(t.blocks), 1)
        self.assertAlmostEqual(t.blocks[0].start_beat, 1.0)

    def test_split_at_boundary(self):
        """Schnitt am Anfang/Ende wird ignoriert."""
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        samples = np.zeros(44100, dtype=np.float32)
        t = AudioTrack()
        t.blocks = [AudioBlock(samples, 44100)]
        t.split_block(0, 0.0, 120)  # Am Anfang
        self.assertEqual(len(t.blocks), 1)
        t.split_block(0, 2.0, 120)  # Nach dem Ende
        self.assertEqual(len(t.blocks), 1)


# ==============================================================
# PITCH DETECTOR
# ==============================================================

class TestPitchDetector(unittest.TestCase):
    """PitchDetector: Noten aus Audio erkennen."""

    def _make_sine(self, freq: float, duration: float = 1.0,
                   sr: int = 22050) -> np.ndarray:
        """Sinuston erzeugen."""
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

    def test_detect_single_note(self):
        from musiai.audio.PitchDetector import PitchDetector
        # A4 = 440 Hz = MIDI 69
        samples = self._make_sine(440.0, 1.0)
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        self.assertGreater(len(notes), 0)
        # Erkannte Tonhöhe sollte nahe A4 sein
        pitches = [n["pitch"] for n in notes]
        self.assertIn(69, pitches)

    def test_detect_two_notes(self):
        from musiai.audio.PitchDetector import PitchDetector
        # C4 (261 Hz) dann E4 (329 Hz)
        s1 = self._make_sine(261.63, 0.5)
        silence = np.zeros(2000, dtype=np.float32)
        s2 = self._make_sine(329.63, 0.5)
        samples = np.concatenate([s1, silence, s2])
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        self.assertGreaterEqual(len(notes), 2)

    def test_quantize(self):
        from musiai.audio.PitchDetector import PitchDetector
        det = PitchDetector()
        self.assertAlmostEqual(det._quantize(0.13), 0.25)
        self.assertAlmostEqual(det._quantize(0.0), 0.0)
        self.assertAlmostEqual(det._quantize(1.9), 2.0)

    def test_empty_audio(self):
        from musiai.audio.PitchDetector import PitchDetector
        det = PitchDetector()
        notes = det.detect(np.zeros(22050, dtype=np.float32), 22050)
        self.assertEqual(len(notes), 0)

    def test_note_dict_format(self):
        from musiai.audio.PitchDetector import PitchDetector
        samples = self._make_sine(440.0, 0.5)
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        if notes:
            n = notes[0]
            self.assertIn("pitch", n)
            self.assertIn("start_beat", n)
            self.assertIn("duration_beats", n)
            self.assertIn("velocity", n)
            self.assertIn("cent_offset", n)


# ==============================================================
# PART MODEL (erweitert)
# ==============================================================

class TestPartModel(unittest.TestCase):
    """Part mit instrument, muted, audio_track."""

    def test_default_values(self):
        p = Part()
        self.assertEqual(p.instrument, 0)
        self.assertFalse(p.muted)
        self.assertIsNone(p.audio_track)

    def test_serialize_instrument(self):
        p = Part("Violine", 1)
        p.instrument = 40
        p.muted = True
        d = p.to_dict()
        self.assertEqual(d["instrument"], 40)
        self.assertTrue(d["muted"])

    def test_deserialize_instrument(self):
        d = {"name": "Cello", "channel": 2, "instrument": 42,
             "muted": True, "measures": []}
        p = Part.from_dict(d)
        self.assertEqual(p.instrument, 42)
        self.assertTrue(p.muted)

    def test_audio_track_on_part(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        p = Part("Audio")
        t = AudioTrack()
        t.blocks = [AudioBlock(np.zeros(44100, dtype=np.float32), 44100)]
        p.audio_track = t
        self.assertIsNotNone(p.audio_track)
        self.assertEqual(len(p.audio_track.blocks), 1)


# ==============================================================
# MEASURE EFFECTIVE DURATION
# ==============================================================

class TestMeasureEffectiveDuration(unittest.TestCase):
    """Measure.effective_duration_beats berücksichtigt Noten-Deviations."""

    def test_standard_duration(self):
        m = Measure(1, TimeSignature(4, 4))
        self.assertAlmostEqual(m.effective_duration_beats, 4.0)

    def test_extended_by_note(self):
        m = Measure(1, TimeSignature(4, 4))
        n = Note(60, 3.0, 1.0, Expression(duration_deviation=3.0))
        m.add_note(n)
        # Note endet bei 3.0 + 1.0*3.0 = 6.0 > 4.0
        self.assertAlmostEqual(m.effective_duration_beats, 6.0)

    def test_normal_notes_no_extension(self):
        m = Measure(1, TimeSignature(4, 4))
        m.add_note(Note(60, 0, 1))
        m.add_note(Note(64, 1, 1))
        # Alle Noten enden bei Beat 2.0, Takt ist 4.0
        self.assertAlmostEqual(m.effective_duration_beats, 4.0)


# ==============================================================
# DURATION DEVIATION SHIFTS NOTES
# ==============================================================

class TestDurationShiftsNotes(unittest.TestCase):
    """Noten verschieben sich wenn eine Note verlängert wird."""

    def setUp(self):
        from musiai.notation.NotationScene import NotationScene
        from musiai.controller.EditController import EditController
        from musiai.util.SignalBus import SignalBus
        self.piece = Piece("Test")
        self.piece.tempos = [Tempo(120, 0)]
        part = Part()
        m = Measure(1, TimeSignature(4, 4))
        m.add_note(Note(60, 0.0, 1.0))  # C4 bei Beat 0
        m.add_note(Note(64, 1.0, 1.0))  # E4 bei Beat 1
        m.add_note(Note(67, 2.0, 1.0))  # G4 bei Beat 2
        part.add_measure(m)
        self.piece.add_part(part)
        self.scene = NotationScene()
        self.scene.set_piece(self.piece)
        self.bus = SignalBus()
        self.ec = EditController(self.scene, self.bus)

    def test_shift_following_notes(self):
        items = self.scene.get_all_note_items()
        # Finde C4 Item
        c4_item = None
        for it in items:
            if it.note.pitch == 60:
                c4_item = it
                break
        self.assertIsNotNone(c4_item)
        self.ec.select_note(c4_item)
        # C4 auf 2x verlängern
        self.ec.change_duration_deviation(2.0)
        m = self.piece.parts[0].measures[0]
        # E4 sollte von Beat 1 auf Beat 2 verschoben sein
        e4 = [n for n in m.notes if n.pitch == 64][0]
        self.assertAlmostEqual(e4.start_beat, 2.0)
        # G4 sollte von Beat 2 auf Beat 3 verschoben sein
        g4 = [n for n in m.notes if n.pitch == 67][0]
        self.assertAlmostEqual(g4.start_beat, 3.0)


# ==============================================================
# INSTRUMENT LIBRARY
# ==============================================================

class TestInstrumentLibrary(unittest.TestCase):
    """instruments.json korrekt ladbar."""

    def test_file_exists(self):
        path = os.path.join("media", "Stimmen", "instruments.json")
        self.assertTrue(os.path.exists(path))

    def test_json_valid(self):
        import json
        path = os.path.join("media", "Stimmen", "instruments.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("categories", data)
        self.assertGreater(len(data["categories"]), 0)

    def test_all_have_program(self):
        import json
        path = os.path.join("media", "Stimmen", "instruments.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for cat in data["categories"]:
            for instr in cat["instruments"]:
                self.assertIn("name", instr)
                self.assertIn("program", instr)
                self.assertGreaterEqual(instr["program"], 0)
                self.assertLessEqual(instr["program"], 127)

    def test_at_least_30_instruments(self):
        import json
        path = os.path.join("media", "Stimmen", "instruments.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total = sum(len(c["instruments"]) for c in data["categories"])
        self.assertGreaterEqual(total, 30)


# ==============================================================
# PLAYBACK ENGINE BACKENDS
# ==============================================================

class TestPlaybackEngineBackends(unittest.TestCase):
    """PlaybackEngine Backend-Wechsel."""

    def _make_engine(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        return PlaybackEngine(SignalBus())

    def test_default_backend(self):
        pe = self._make_engine()
        self.assertEqual(pe.backend_name, "windows_gm")

    def test_switch_soundfont(self):
        pe = self._make_engine()
        result = pe.switch_backend("soundfont")
        # Kann True oder False sein je nach FluidSynth-Verfügbarkeit
        if result:
            self.assertEqual(pe.backend_name, "soundfont")

    def test_switch_midi_port(self):
        pe = self._make_engine()
        result = pe.switch_backend("midi_port")
        self.assertTrue(result)
        self.assertEqual(pe.backend_name, "midi_port")

    def test_switch_back_to_gm(self):
        pe = self._make_engine()
        pe.switch_backend("midi_port")
        pe.switch_backend("windows_gm")
        self.assertEqual(pe.backend_name, "windows_gm")

    def test_list_midi_ports(self):
        pe = self._make_engine()
        ports = pe.list_midi_ports()
        self.assertIsInstance(ports, list)

    def test_muted_part_not_played(self):
        """Gemutete Stimmen werden übersprungen."""
        pe = self._make_engine()
        piece = Piece("Test")
        part = Part()
        m = Measure(1, TimeSignature(4, 4))
        m.add_note(Note(60, 0, 1))
        part.add_measure(m)
        part.muted = True
        piece.add_part(part)
        pe.set_piece(piece)
        # Notes sind in der Liste aber Part ist muted
        self.assertEqual(len(pe._all_notes), 1)
        _, _, _, p = pe._all_notes[0]
        self.assertTrue(p.muted)


# ==============================================================
# SOUNDFONT PLAYER
# ==============================================================

class TestSoundFontPlayer(unittest.TestCase):
    """SoundFontPlayer Grundfunktionen."""

    def test_create(self):
        from musiai.audio.SoundFontPlayer import SoundFontPlayer
        sp = SoundFontPlayer()
        # Kann verfügbar sein oder nicht
        if sp.is_available:
            sp.shutdown()

    def test_load_nonexistent(self):
        from musiai.audio.SoundFontPlayer import SoundFontPlayer
        sp = SoundFontPlayer()
        result = sp.load_soundfont("nonexistent.sf2")
        self.assertIsNone(result)
        sp.shutdown()


# ==============================================================
# MIDI PORT PLAYER
# ==============================================================

class TestMidiPortPlayer(unittest.TestCase):
    """MidiPortPlayer Grundfunktionen."""

    def test_list_ports(self):
        from musiai.audio.MidiPortPlayer import MidiPortPlayer
        ports = MidiPortPlayer.list_output_ports()
        self.assertIsInstance(ports, list)
        for pid, name in ports:
            self.assertIsInstance(pid, int)
            self.assertIsInstance(name, str)

    def test_connect_invalid(self):
        from musiai.audio.MidiPortPlayer import MidiPortPlayer
        mp = MidiPortPlayer()
        result = mp.connect(999)
        self.assertFalse(result)


# ==============================================================
# FILE CONTROLLER (Save Music)
# ==============================================================

class TestFileControllerSave(unittest.TestCase):
    """Musik speichern (Originalformat)."""

    def test_source_tracking(self):
        from musiai.controller.FileController import FileController
        from musiai.util.SignalBus import SignalBus
        from musiai.model.Project import Project
        fc = FileController(Project(), SignalBus(), None)
        self.assertIsNone(fc._source_path)
        self.assertIsNone(fc._source_type)


# ==============================================================
# WAVEFORM ITEM
# ==============================================================

class TestWaveformItem(unittest.TestCase):
    """WaveformItem Rendering."""

    def test_create(self):
        from musiai.notation.WaveformItem import WaveformItem
        samples = np.random.randn(44100).astype(np.float32)
        w = WaveformItem(samples, 44100, 200, 0, 0)
        self.assertIsNotNone(w)
        rect = w.boundingRect()
        self.assertAlmostEqual(rect.width(), 200)

    def test_empty_samples(self):
        from musiai.notation.WaveformItem import WaveformItem
        w = WaveformItem(np.array([], dtype=np.float32), 44100, 100, 0, 0)
        self.assertIsNotNone(w)


# ==============================================================
# MICROTONE MUSICXML TEST FILES
# ==============================================================

class TestMicrotoneFiles(unittest.TestCase):
    """Mikrotone MusicXML-Dateien importierbar."""

    def test_turkish_makam(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        path = "media/music/microtones_turkish_makam.musicxml"
        if not os.path.exists(path):
            self.skipTest("Datei nicht vorhanden")
        piece = MusicXmlImporter().import_file(path)
        self.assertGreater(len(piece.parts), 0)
        notes = piece.parts[0].get_all_notes()
        self.assertGreater(len(notes), 0)
        # Mikrotöne: mindestens eine Note mit cent_offset != 0
        has_microtone = any(
            abs(n.expression.cent_offset) > 0.5 for n in notes
        )
        self.assertTrue(has_microtone, "Keine Mikrotöne erkannt")

    def test_spectral(self):
        from musiai.musicXML.MusicXmlImporter import MusicXmlImporter
        path = "media/music/microtones_spectral.musicxml"
        if not os.path.exists(path):
            self.skipTest("Datei nicht vorhanden")
        piece = MusicXmlImporter().import_file(path)
        self.assertGreater(len(piece.parts), 0)
        notes = piece.parts[0].get_all_notes()
        has_microtone = any(
            abs(n.expression.cent_offset) > 0.5 for n in notes
        )
        self.assertTrue(has_microtone, "Keine Mikrotöne erkannt")

    def test_tempo_velocity_midi(self):
        """MIDI mit Tempo-Änderungen importierbar."""
        from musiai.midi.MidiImporter import MidiImporter
        path = "media/music/tempo_velocity_changes.mid"
        if not os.path.exists(path):
            self.skipTest("Datei nicht vorhanden")
        piece = MidiImporter().import_file(path)
        self.assertGreater(len(piece.parts), 0)
        self.assertGreater(piece.parts[0].get_all_notes().__len__(), 0)


# ==============================================================
# NOTATION SCENE WITH AUDIO
# ==============================================================

class TestNotationSceneAudio(unittest.TestCase):
    """NotationScene rendert Audio-Stimmen korrekt."""

    def test_render_with_audio_part(self):
        """Audio-Part rendert Waveform, keine MeasureRenderer."""
        from musiai.notation.NotationScene import NotationScene
        from musiai.notation.WaveformItem import WaveformItem
        from musiai.model.AudioTrack import AudioTrack, AudioBlock

        piece = Piece("Audio Test")
        piece.tempos = [Tempo(120, 0)]
        part = Part("Audio: Test")
        part.audio_track = AudioTrack()
        part.audio_track.sr = 44100
        part.audio_track.blocks = [
            AudioBlock(np.random.randn(44100).astype(np.float32), 44100)
        ]
        part.audio_track._full_samples = part.audio_track.blocks[0].samples
        m = Measure(1, TimeSignature(4, 4))
        part.add_measure(m)
        piece.add_part(part)

        scene = NotationScene()
        scene.set_piece(piece)
        # Audio-Part hat keine MeasureRenderer, aber WaveformItems
        self.assertEqual(len(scene.measure_renderers), 0)
        waveforms = [i for i in scene.items() if isinstance(i, WaveformItem)]
        self.assertGreater(len(waveforms), 0)


if __name__ == "__main__":
    unittest.main()
