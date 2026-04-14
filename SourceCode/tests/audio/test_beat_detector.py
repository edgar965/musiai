"""Tests für Beat-Erkennung mit allen 3 Engines."""

import sys
import os
import unittest
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _create_click_track(bpm: float = 120.0, duration_sec: float = 10.0,
                         sr: int = 22050) -> tuple[np.ndarray, str]:
    """Create a WAV click track with known BPM for testing.

    Returns (samples, temp_path).
    """
    import soundfile as sf

    beat_interval = 60.0 / bpm
    n_samples = int(duration_sec * sr)
    y = np.zeros(n_samples, dtype=np.float32)

    # Place clicks (short impulse) at each beat
    click_len = int(0.01 * sr)  # 10ms click
    click = np.sin(2 * np.pi * 1000 * np.arange(click_len) / sr) * 0.8

    t = 0.0
    while t < duration_sec:
        idx = int(t * sr)
        end = min(idx + click_len, n_samples)
        y[idx:end] += click[:end - idx]
        t += beat_interval

    path = tempfile.mktemp(suffix=".wav")
    sf.write(path, y, sr)
    return y, path


class TestBeatDetectorLibrosa(unittest.TestCase):
    """Test librosa beat_track engine."""

    @classmethod
    def setUpClass(cls):
        try:
            import soundfile
            cls._y, cls._path = _create_click_track(bpm=120.0, duration_sec=8.0)
            cls._available = True
        except ImportError:
            cls._available = False
            cls._path = None

    @classmethod
    def tearDownClass(cls):
        if cls._path and os.path.exists(cls._path):
            os.unlink(cls._path)

    def test_detect_returns_result(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector, BeatResult
        result = BeatDetector.detect(self._path, "librosa")
        self.assertIsInstance(result, BeatResult)
        self.assertEqual(result.engine, "librosa")

    def test_bpm_reasonable(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa")
        # Should detect ~120 BPM (±30 tolerance for simple click track)
        self.assertGreater(result.bpm, 80)
        self.assertLess(result.bpm, 180)

    def test_beats_found(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa")
        # 8 seconds at 120 BPM = ~16 beats
        self.assertGreater(len(result.beat_times), 5)

    def test_tempo_curve_populated(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa")
        self.assertGreater(len(result.tempo_curve), 0)
        for t, bpm in result.tempo_curve:
            self.assertGreater(bpm, 0)

    def test_time_signature(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa")
        num, den = result.time_signature
        self.assertIn(num, [2, 3, 4, 6])
        self.assertIn(den, [4, 8])


class TestBeatDetectorLibrosaDynamic(unittest.TestCase):
    """Test librosa dynamic tempo engine."""

    @classmethod
    def setUpClass(cls):
        try:
            import soundfile
            # Create track with tempo change: 100 BPM → 140 BPM
            sr = 22050
            y1, _ = _create_click_track(bpm=100.0, duration_sec=4.0, sr=sr)
            y2, _ = _create_click_track(bpm=140.0, duration_sec=4.0, sr=sr)
            y = np.concatenate([y1, y2])
            cls._path = tempfile.mktemp(suffix=".wav")
            import soundfile as sf
            sf.write(cls._path, y, sr)
            cls._available = True
            # Clean up the temp files from _create_click_track
            if os.path.exists(_):
                os.unlink(_)
        except ImportError:
            cls._available = False
            cls._path = None

    @classmethod
    def tearDownClass(cls):
        if cls._path and os.path.exists(cls._path):
            os.unlink(cls._path)

    def test_detect_returns_result(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector, BeatResult
        result = BeatDetector.detect(self._path, "librosa_dynamic")
        self.assertIsInstance(result, BeatResult)
        self.assertEqual(result.engine, "librosa_dynamic")

    def test_tempo_curve_has_variation(self):
        """Dynamic engine should detect tempo changes."""
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa_dynamic")
        self.assertGreater(len(result.tempo_curve), 3)
        tempos = [bpm for _, bpm in result.tempo_curve]
        tempo_range = max(tempos) - min(tempos)
        # Should detect some variation (100→140 = range ~40)
        self.assertGreater(tempo_range, 10,
                           f"Tempo range {tempo_range:.0f} too small, "
                           f"expected variation")

    def test_tempo_at_method(self):
        if not self._available:
            self.skipTest("soundfile not installed")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(self._path, "librosa_dynamic")
        # tempo_at should return reasonable values
        t0 = result.tempo_at(0.5)
        t_end = result.tempo_at(7.0)
        self.assertGreater(t0, 0)
        self.assertGreater(t_end, 0)


class TestBeatDetectorMadmom(unittest.TestCase):
    """Test madmom engine (skipped if Python 3.10 not available)."""

    @classmethod
    def setUpClass(cls):
        from musiai.audio.BeatDetector import BeatDetector
        cls._available = BeatDetector.detect_available().get("madmom", False)

    def test_madmom_availability(self):
        """Check madmom availability detection."""
        from musiai.audio.BeatDetector import BeatDetector
        avail = BeatDetector.detect_available()
        self.assertIn("madmom", avail)

    def test_madmom_with_audio(self):
        """madmom detects beats from real audio."""
        if not self._available:
            self.skipTest("python310ENV not available")
        audio = os.path.join(os.path.dirname(__file__), '..', '..',
                             'media', 'mp3', 'test.mp3')
        if not os.path.exists(audio):
            self.skipTest("test.mp3 not found")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(audio, "madmom")
        self.assertEqual(result.engine, "madmom")
        self.assertGreater(result.bpm, 30)
        self.assertGreater(len(result.beat_times), 3)
        self.assertGreater(len(result.tempo_curve), 0)


class TestBeatDetectorEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_unknown_engine(self):
        from musiai.audio.BeatDetector import BeatDetector
        with self.assertRaises(ValueError):
            BeatDetector.detect("test.wav", "nonexistent_engine")

    def test_beat_result_defaults(self):
        from musiai.audio.BeatDetector import BeatResult
        r = BeatResult()
        self.assertEqual(r.bpm, 120.0)
        self.assertEqual(r.beats_per_measure(), 4)
        self.assertEqual(r.tempo_at(5.0), 120.0)

    def test_detect_available_returns_dict(self):
        from musiai.audio.BeatDetector import BeatDetector
        avail = BeatDetector.detect_available()
        self.assertIsInstance(avail, dict)
        self.assertIn("librosa", avail)
        self.assertIn("librosa_dynamic", avail)
        self.assertIn("madmom", avail)


if __name__ == "__main__":
    unittest.main()
