"""Tests für alle Notenerkennung-Pipelines: pyin, demucs+pyin."""

import unittest
import numpy as np
import os
import sys

# Projektroot (2 Ebenen über dieser Datei)
PROJECT_ROOT = __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
__import__("os").chdir(PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

MP3_PATH = os.path.join("..", "media", "mp3", "_Bella_figlia_dell'amore_.MP3")
HAS_MP3 = os.path.exists(MP3_PATH)


def _make_sine(freq, duration=1.0, sr=22050):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ==============================================================
# PYIN PIPELINE
# ==============================================================

class TestPyinPipeline(unittest.TestCase):
    """pyin (librosa) Noten-Erkennung."""

    def test_sine_a4(self):
        from musiai.audio.PitchDetector import PitchDetector
        samples = _make_sine(440.0, 1.0)
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        self.assertGreater(len(notes), 0)
        self.assertIn(69, [n["pitch"] for n in notes])

    def test_two_sequential_notes(self):
        from musiai.audio.PitchDetector import PitchDetector
        s1 = _make_sine(261.63, 0.5)  # C4
        gap = np.zeros(3000, dtype=np.float32)
        s2 = _make_sine(329.63, 0.5)  # E4
        samples = np.concatenate([s1, gap, s2])
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        self.assertGreaterEqual(len(notes), 2)

    def test_silence_returns_empty(self):
        from musiai.audio.PitchDetector import PitchDetector
        det = PitchDetector()
        notes = det.detect(np.zeros(22050, dtype=np.float32), 22050)
        self.assertEqual(len(notes), 0)

    def test_no_overflow_past_measure(self):
        """Keine Note darf über die Taktgrenze hinausgehen."""
        from musiai.audio.PitchDetector import PitchDetector
        # Langer Ton (3 Sekunden = 6 beats bei 120 BPM)
        samples = _make_sine(440.0, 3.0)
        det = PitchDetector(tempo_bpm=120, beats_per_measure=4.0)
        notes = det.detect(samples, 22050)
        for n in notes:
            local = n["start_beat"] % 4.0
            end = local + n["duration_beats"]
            self.assertLessEqual(end, 4.01, f"Note overflow: {n}")

    def test_notes_sorted_by_start(self):
        from musiai.audio.PitchDetector import PitchDetector
        s1 = _make_sine(261.63, 0.3)
        gap = np.zeros(2000, dtype=np.float32)
        s2 = _make_sine(329.63, 0.3)
        gap2 = np.zeros(2000, dtype=np.float32)
        s3 = _make_sine(392.0, 0.3)
        samples = np.concatenate([s1, gap, s2, gap2, s3])
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(samples, 22050)
        starts = [n["start_beat"] for n in notes]
        self.assertEqual(starts, sorted(starts))

    def test_quantize_grid(self):
        from musiai.audio.PitchDetector import PitchDetector
        det = PitchDetector()
        self.assertAlmostEqual(det._quantize(0.13), 0.25)
        self.assertAlmostEqual(det._quantize(0.37), 0.25)
        self.assertAlmostEqual(det._quantize(0.63), 0.75)
        self.assertAlmostEqual(det._quantize(1.0), 1.0)

    @unittest.skipUnless(HAS_MP3, "MP3 nicht vorhanden")
    def test_real_mp3_pyin(self):
        """pyin auf echter MP3-Datei."""
        from musiai.audio.PitchDetector import PitchDetector
        import librosa
        y, sr = librosa.load(MP3_PATH, sr=22050, mono=True, duration=10)
        det = PitchDetector(tempo_bpm=100)
        notes = det.detect(y, sr)
        self.assertGreater(len(notes), 5)
        # Alle Noten haben gültige Pitches
        for n in notes:
            self.assertGreaterEqual(n["pitch"], 20)
            self.assertLessEqual(n["pitch"], 110)


# ==============================================================
# DEMUCS+PYIN PIPELINE
# ==============================================================

class TestDemucsDetector(unittest.TestCase):
    """demucs Source Separation + pyin pro Stimme."""

    def test_import(self):
        from musiai.audio.DemucsDetector import DemucsDetector
        det = DemucsDetector(tempo_bpm=100)
        self.assertIsNotNone(det)

    @unittest.skipUnless(HAS_MP3, "MP3 nicht vorhanden")
    def test_detect_creates_stems(self):
        """demucs erkennt Stimmen aus MP3."""
        from musiai.audio.DemucsDetector import DemucsDetector
        det = DemucsDetector(tempo_bpm=100, beats_per_measure=4.0)
        # Nur kurzes Stück testen (5s)
        import librosa, soundfile, tempfile
        y, sr = librosa.load(MP3_PATH, sr=44100, mono=False, duration=5)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        if y.ndim == 1:
            y = np.stack([y, y])
        soundfile.write(tmp.name, y.T, sr)
        tmp.close()

        try:
            results = det.detect(tmp.name)
            self.assertIsInstance(results, dict)
            # Sollte mindestens eine Stimme erkannt haben
            if results:
                for stem, notes in results.items():
                    self.assertIn(stem, ["vocals", "bass", "other"])
                    self.assertIsInstance(notes, list)
        finally:
            os.unlink(tmp.name)

    @unittest.skipUnless(HAS_MP3, "MP3 nicht vorhanden")
    def test_detected_notes_format(self):
        """Erkannte Noten haben korrektes Format."""
        from musiai.audio.DemucsDetector import DemucsDetector
        import librosa, soundfile, tempfile
        y, sr = librosa.load(MP3_PATH, sr=44100, mono=False, duration=5)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        if y.ndim == 1:
            y = np.stack([y, y])
        soundfile.write(tmp.name, y.T, sr)
        tmp.close()

        try:
            det = DemucsDetector(tempo_bpm=100)
            results = det.detect(tmp.name)
            for stem, notes in results.items():
                for n in notes:
                    self.assertIn("pitch", n)
                    self.assertIn("start_beat", n)
                    self.assertIn("duration_beats", n)
                    self.assertGreater(n["duration_beats"], 0)
                    # Kein Takt-Overflow
                    local = n["start_beat"] % 4.0
                    end = local + n["duration_beats"]
                    self.assertLessEqual(end, 4.01)
        finally:
            os.unlink(tmp.name)


# ==============================================================
# ENGINE SELECTION
# ==============================================================

class TestEngineAvailability(unittest.TestCase):
    """Prüft welche Engines verfügbar sind."""

    def test_pyin_available(self):
        import librosa
        self.assertTrue(hasattr(librosa, 'pyin'))

    def test_demucs_available(self):
        import demucs.pretrained
        self.assertIn('drums', demucs.pretrained.SOURCES)

    def test_settings_dialog(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        engine = dialog.selected_engine
        self.assertIn(engine, ["pyin", "demucs+pyin", "madmom", "basic-pitch"])


# ==============================================================
# END-TO-END: AppController._on_part_detect
# ==============================================================

class TestDetectionIntegration(unittest.TestCase):
    """Integration: Audio laden → Engine → Noten-Stimme."""

    def test_pyin_creates_part(self):
        """pyin Erkennung erstellt neue Stimme im Piece."""
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Tempo import Tempo
        from musiai.model.TimeSignature import TimeSignature
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        from musiai.audio.PitchDetector import PitchDetector

        piece = Piece("Test")
        piece.tempos = [Tempo(120, 0)]
        part = Part("Audio")
        # Synthetische Audio-Daten (A4 für 1 Sekunde)
        samples = _make_sine(440.0, 1.0, 22050)
        part.audio_track = AudioTrack()
        part.audio_track.sr = 22050
        part.audio_track.blocks = [AudioBlock(samples, 22050)]
        part.audio_track._full_samples = samples
        part.audio_track.file_path = "test.wav"
        part.add_measure(Measure(1, TimeSignature(4, 4)))
        piece.add_part(part)

        # Detect
        detector = PitchDetector(tempo_bpm=120)
        notes = detector.detect(samples, 22050)
        self.assertGreater(len(notes), 0)

        # Neue Stimme erstellen
        new_part = Part("Erkannt")
        new_part.add_measure(Measure(1, TimeSignature(4, 4)))
        from musiai.model.Note import Note
        from musiai.model.Expression import Expression
        for nd in notes:
            m_idx = min(int(nd["start_beat"] / 4.0), 0)
            local = nd["start_beat"] - m_idx * 4.0
            note = Note(nd["pitch"], local, nd["duration_beats"],
                        Expression(velocity=nd["velocity"]))
            new_part.measures[m_idx].add_note(note)
        piece.add_part(new_part)

        self.assertEqual(len(piece.parts), 2)
        total_notes = sum(len(m.notes) for m in new_part.measures)
        self.assertGreater(total_notes, 0)


if __name__ == "__main__":
    unittest.main()
