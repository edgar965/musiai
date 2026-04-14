"""Tests für Audio-Import (MP3/WAV → Neue Stimme — Aufnahme)."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

MP3_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'media', 'mp3', 'test.mp3'))

_qapp = None
def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)


class TestAudioTrackLoad(unittest.TestCase):
    """AudioTrack.load() mit MP3."""

    def test_load_mp3(self):
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.model.AudioTrack import AudioTrack
        track = AudioTrack()
        result = track.load(MP3_PATH)
        self.assertTrue(result, "AudioTrack.load() should return True")

    def test_duration_positive(self):
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.model.AudioTrack import AudioTrack
        track = AudioTrack()
        track.load(MP3_PATH)
        self.assertGreater(track.duration_seconds, 0)

    def test_has_blocks(self):
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.model.AudioTrack import AudioTrack
        track = AudioTrack()
        track.load(MP3_PATH)
        self.assertGreater(len(track.blocks), 0)

    def test_block_has_samples(self):
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.model.AudioTrack import AudioTrack
        track = AudioTrack()
        track.load(MP3_PATH)
        block = track.blocks[0]
        self.assertGreater(len(block.samples), 0)
        self.assertGreater(block.sr, 0)


class TestAudioVoiceFlow(unittest.TestCase):
    """Full flow: load MP3 → create Part → add to Piece → refresh Scene."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_add_audio_part_to_piece(self):
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.TimeSignature import TimeSignature

        piece = Piece("Test")
        piece.add_part(Part("Piano"))

        track = AudioTrack()
        self.assertTrue(track.load(MP3_PATH))

        audio_part = Part(name="Audio: test", channel=1)
        audio_part.audio_track = track
        ts = TimeSignature(4, 4)
        beats = track.duration_seconds * (120 / 60.0)
        n_measures = max(1, int(beats / ts.beats_per_measure()) + 1)
        for i in range(n_measures):
            audio_part.add_measure(Measure(i + 1, ts))

        piece.add_part(audio_part)
        self.assertEqual(len(piece.parts), 2)
        self.assertTrue(piece.parts[1].audio_track is not None)

    def test_scene_refresh_with_audio(self):
        """Scene refresh should not crash with audio part."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from PySide6.QtCore import QSettings
        QSettings("MusiAI", "MusiAI").setValue(
            "ui/musicxml_bravura", "true")

        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.TimeSignature import TimeSignature
        from musiai.notation.NotationScene import NotationScene

        piece = Piece("Test")
        part = Part("Piano")
        part.add_measure(Measure(1))
        piece.add_part(part)

        track = AudioTrack()
        track.load(MP3_PATH)
        audio_part = Part(name="Audio: test", channel=1)
        audio_part.audio_track = track
        ts = TimeSignature(4, 4)
        beats = track.duration_seconds * (120 / 60.0)
        n = max(1, int(beats / ts.beats_per_measure()) + 1)
        for i in range(n):
            audio_part.add_measure(Measure(i + 1, ts))
        piece.add_part(audio_part)

        scene = NotationScene()
        scene.set_piece(piece)
        # Should have items (at least playhead + cursor)
        self.assertGreater(len(list(scene.items())), 0)

        # Refresh should not crash
        scene.refresh()
        self.assertGreater(len(list(scene.items())), 0)

    def test_waveform_items_in_scene(self):
        """Waveform items should appear in scene for audio parts."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from PySide6.QtCore import QSettings
        # Use non-bravura mode which renders WaveformItems
        QSettings("MusiAI", "MusiAI").setValue(
            "ui/musicxml_bravura", "false")

        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.TimeSignature import TimeSignature
        from musiai.notation.NotationScene import NotationScene

        piece = Piece("Test")
        part = Part("Piano")
        m = Measure(1)
        from musiai.model.Note import Note
        m.add_note(Note(60, 0, 1))
        part.add_measure(m)
        piece.add_part(part)

        track = AudioTrack()
        track.load(MP3_PATH)
        audio_part = Part(name="Audio: test", channel=1)
        audio_part.audio_track = track
        ts = TimeSignature(4, 4)
        beats = track.duration_seconds * (120 / 60.0)
        n = max(1, int(beats / ts.beats_per_measure()) + 1)
        for i in range(n):
            audio_part.add_measure(Measure(i + 1, ts))
        piece.add_part(audio_part)

        scene = NotationScene()
        scene.set_piece(piece)

        # Look for waveform items
        waveform_items = [i for i in scene.items()
                          if i.data(0) == "waveform"]
        self.assertGreater(len(waveform_items), 0,
                           "Waveform items should be in scene")

        # Restore bravura setting
        QSettings("MusiAI", "MusiAI").setValue(
            "ui/musicxml_bravura", "true")


if __name__ == "__main__":
    unittest.main()
