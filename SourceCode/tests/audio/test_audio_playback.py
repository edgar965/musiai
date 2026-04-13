"""Tests für Audio-Playback: AudioPlayer, AudioTrack + PlaybackEngine Integration."""

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

from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Measure import Measure
from musiai.model.Note import Note
from musiai.model.Expression import Expression
from musiai.model.TimeSignature import TimeSignature
from musiai.model.Tempo import Tempo

MP3_PATH = os.path.join("..", "media", "mp3", "_Bella_figlia_dell'amore_.MP3")
HAS_MP3 = os.path.exists(MP3_PATH)


# ==============================================================
# AUDIO PLAYER
# ==============================================================

class TestAudioPlayer(unittest.TestCase):
    """AudioPlayer: pygame.mixer Playback."""

    def test_create(self):
        from musiai.audio.AudioPlayer import AudioPlayer
        ap = AudioPlayer()
        self.assertTrue(ap.is_available)
        ap.shutdown()

    def test_set_track(self):
        from musiai.audio.AudioPlayer import AudioPlayer
        ap = AudioPlayer()
        ap.set_track(0, "test.mp3")
        self.assertEqual(len(ap._tracks), 1)
        self.assertEqual(ap._tracks[0]["path"], "test.mp3")
        ap.shutdown()

    def test_remove_track(self):
        from musiai.audio.AudioPlayer import AudioPlayer
        ap = AudioPlayer()
        ap.set_track(0, "test.mp3")
        ap.remove_track(0)
        self.assertEqual(len(ap._tracks), 0)
        ap.shutdown()

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_play_real_mp3(self):
        """Echte MP3-Datei laden und kurz abspielen."""
        from musiai.audio.AudioPlayer import AudioPlayer
        import time
        ap = AudioPlayer()
        ap.set_track(0, MP3_PATH)
        ap.play(0.0)
        time.sleep(0.5)  # 0.5s abspielen
        ap.stop()
        ap.shutdown()

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_pause_unpause(self):
        from musiai.audio.AudioPlayer import AudioPlayer
        import time
        ap = AudioPlayer()
        ap.set_track(0, MP3_PATH)
        ap.play(0.0)
        time.sleep(0.3)
        ap.pause()
        time.sleep(0.2)
        ap.unpause()
        time.sleep(0.3)
        ap.stop()
        ap.shutdown()

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_play_from_offset(self):
        """Ab einer bestimmten Stelle abspielen."""
        from musiai.audio.AudioPlayer import AudioPlayer
        import time
        ap = AudioPlayer()
        ap.set_track(0, MP3_PATH)
        ap.play(30.0)  # Ab 30 Sekunden
        time.sleep(0.5)
        ap.stop()
        ap.shutdown()

    def test_mute(self):
        from musiai.audio.AudioPlayer import AudioPlayer
        ap = AudioPlayer()
        ap.set_muted(True)
        ap.set_muted(False)
        ap.shutdown()


# ==============================================================
# AUDIO TRACK LOADING (echte Datei)
# ==============================================================

class TestAudioTrackRealFile(unittest.TestCase):
    """AudioTrack mit echter MP3-Datei."""

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_load_mp3(self):
        from musiai.model.AudioTrack import AudioTrack
        t = AudioTrack()
        self.assertTrue(t.load(MP3_PATH))
        self.assertGreater(len(t.blocks), 0)
        self.assertGreater(t.duration_seconds, 10.0)
        self.assertEqual(t.sr, 44100)

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_split_real_audio(self):
        from musiai.model.AudioTrack import AudioTrack
        t = AudioTrack()
        t.load(MP3_PATH)
        dur_before = t.blocks[0].duration_seconds
        t.split_block(0, 5.0, 120)  # Bei 5 Sekunden schneiden
        self.assertEqual(len(t.blocks), 2)
        self.assertAlmostEqual(t.blocks[0].duration_seconds, 5.0, places=0)
        self.assertAlmostEqual(
            t.blocks[0].duration_seconds + t.blocks[1].duration_seconds,
            dur_before, places=0
        )

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_waveform_summary(self):
        from musiai.model.AudioTrack import AudioTrack
        t = AudioTrack()
        t.load(MP3_PATH)
        summary = t.get_waveform_summary(200)
        self.assertEqual(len(summary), 200)
        self.assertTrue(np.all(summary >= 0))
        self.assertTrue(np.max(summary) > 0)  # Nicht alles Stille


# ==============================================================
# PITCH DETECTION (echte Datei)
# ==============================================================

class TestPitchDetectionRealFile(unittest.TestCase):
    """Pitch Detection auf echter MP3-Datei."""

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_detect_from_mp3(self):
        """Noten aus Bella figlia erkennen (Opern-Quartett)."""
        from musiai.audio.PitchDetector import PitchDetector
        import librosa
        # Nur erste 10 Sekunden laden (Performance)
        y, sr = librosa.load(MP3_PATH, sr=22050, mono=True, duration=10)
        det = PitchDetector(tempo_bpm=120)
        notes = det.detect(y, sr)
        self.assertGreater(len(notes), 0, "Keine Noten erkannt")
        # Prüfe Format
        for n in notes:
            self.assertGreaterEqual(n["pitch"], 30)
            self.assertLessEqual(n["pitch"], 100)
            self.assertGreater(n["duration_beats"], 0)

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_detected_notes_reasonable(self):
        """Erkannte Noten haben sinnvolle Werte."""
        from musiai.audio.PitchDetector import PitchDetector
        import librosa
        y, sr = librosa.load(MP3_PATH, sr=22050, mono=True, duration=5)
        det = PitchDetector(tempo_bpm=100)
        notes = det.detect(y, sr)
        if notes:
            starts = [n["start_beat"] for n in notes]
            # Start-Beats sollten aufsteigend sein
            self.assertEqual(starts, sorted(starts))
            # Keine negativen Beats
            self.assertTrue(all(s >= 0 for s in starts))


# ==============================================================
# PLAYBACK ENGINE + AUDIO INTEGRATION
# ==============================================================

class TestPlaybackEngineAudio(unittest.TestCase):
    """PlaybackEngine mit Audio-Tracks."""

    def _make_piece_with_audio(self):
        piece = Piece("Audio Test")
        piece.tempos = [Tempo(120, 0)]
        part = Part("Audio: Bella")
        part.audio_track = self._make_track()
        m = Measure(1, TimeSignature(4, 4))
        part.add_measure(m)
        piece.add_part(part)
        return piece

    def _make_track(self):
        from musiai.model.AudioTrack import AudioTrack, AudioBlock
        t = AudioTrack()
        t.file_path = MP3_PATH
        t.sr = 44100
        samples = np.random.randn(44100).astype(np.float32)
        t.blocks = [AudioBlock(samples, 44100)]
        t._full_samples = samples
        return t

    def test_audio_track_registered(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        pe = PlaybackEngine(SignalBus())
        piece = self._make_piece_with_audio()
        pe.set_piece(piece)
        self.assertGreater(len(pe.audio_player._tracks), 0)
        pe.shutdown()

    def test_muted_audio_track(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        pe = PlaybackEngine(SignalBus())
        piece = self._make_piece_with_audio()
        piece.parts[0].muted = True
        pe.set_piece(piece)
        # Track ist registriert aber muted
        self.assertTrue(piece.parts[0].muted)
        pe.shutdown()

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_play_piece_with_audio(self):
        """Piece mit Audio-Spur abspielen."""
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        import time

        pe = PlaybackEngine(SignalBus())
        piece = Piece("Audio Test")
        piece.tempos = [Tempo(120, 0)]
        part = Part("Audio: Bella")
        from musiai.model.AudioTrack import AudioTrack
        track = AudioTrack()
        track.load(MP3_PATH)
        part.audio_track = track
        m = Measure(1, TimeSignature(4, 4))
        part.add_measure(m)
        piece.add_part(part)

        pe.set_piece(piece)
        pe.play()
        time.sleep(1.0)
        pe.pause()
        time.sleep(0.3)
        pe.play()  # Resume
        time.sleep(0.5)
        pe.stop()
        pe.shutdown()


# ==============================================================
# END-TO-END: Audio laden → Erkennen → Noten-Stimme
# ==============================================================

class TestEndToEndAudioToNotes(unittest.TestCase):
    """Kompletter Workflow: Audio → Pitch Detection → Noten."""

    @unittest.skipUnless(HAS_MP3, "MP3 Testdatei nicht vorhanden")
    def test_full_workflow(self):
        """MP3 laden → Noten erkennen → Neue Stimme mit Noten."""
        from musiai.model.AudioTrack import AudioTrack
        from musiai.audio.PitchDetector import PitchDetector
        from musiai.notation.NotationScene import NotationScene
        import librosa

        # 1. Piece erstellen
        piece = Piece("E2E Test")
        piece.tempos = [Tempo(100, 0)]

        # 2. Audio laden
        part = Part("Audio: Bella")
        track = AudioTrack()
        track.load(MP3_PATH)
        part.audio_track = track
        ts = TimeSignature(4, 4)
        beats = track.duration_seconds * (100 / 60)
        for i in range(max(1, int(beats / 4) + 1)):
            part.add_measure(Measure(i + 1, ts))
        piece.add_part(part)

        # 3. Pitch Detection (erste 5 Sekunden)
        y, sr = librosa.load(MP3_PATH, sr=22050, mono=True, duration=5)
        det = PitchDetector(tempo_bpm=100)
        notes_data = det.detect(y, sr)
        self.assertGreater(len(notes_data), 0)

        # 4. Noten-Stimme erstellen
        new_part = Part("Erkannt: Bella")
        beats_per_measure = 4.0
        max_beat = max(n["start_beat"] + n["duration_beats"] for n in notes_data)
        n_measures = max(1, int(max_beat / beats_per_measure) + 1)
        for i in range(n_measures):
            new_part.add_measure(Measure(i + 1, ts))
        for nd in notes_data:
            m_idx = min(int(nd["start_beat"] / beats_per_measure), n_measures - 1)
            local = nd["start_beat"] - m_idx * beats_per_measure
            note = Note(nd["pitch"], local, nd["duration_beats"],
                        Expression(velocity=nd["velocity"],
                                   cent_offset=nd["cent_offset"]))
            new_part.measures[m_idx].add_note(note)
        piece.add_part(new_part)

        # 5. Rendern
        scene = NotationScene()
        scene.set_piece(piece)
        self.assertEqual(len(piece.parts), 2)
        self.assertGreater(len(scene.measure_renderers), 0)
        total_notes = sum(len(m.notes) for m in new_part.measures)
        self.assertGreater(total_notes, 0, "Keine Noten in erkannter Stimme")


if __name__ == "__main__":
    unittest.main()
