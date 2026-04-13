"""Tests für Audio Playback (audio/)."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)


class TestTransport(unittest.TestCase):
    def test_initial_state(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        self.assertEqual(t.state, "stopped")
        self.assertAlmostEqual(t.current_beat, 0.0)

    def test_play_pause_stop(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.play()
        self.assertEqual(t.state, "playing")
        t.pause()
        self.assertEqual(t.state, "paused")
        t.stop()
        self.assertEqual(t.state, "stopped")
        self.assertAlmostEqual(t.current_beat, 0.0)

    def test_seek(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.seek(8.5)
        self.assertAlmostEqual(t.current_beat, 8.5)

    def test_tempo_clamp(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        t.tempo_bpm = 5
        self.assertEqual(t.tempo_bpm, 20)
        t.tempo_bpm = 500
        self.assertEqual(t.tempo_bpm, 300)

    def test_state_changed_signal(self):
        from musiai.audio.Transport import Transport
        t = Transport()
        states = []
        t.state_changed.connect(lambda s: states.append(s))
        t.play()
        t.stop()
        self.assertEqual(states, ["playing", "stopped"])


class TestPlaybackEngine(unittest.TestCase):
    def test_set_piece(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note

        bus = SignalBus()
        engine = PlaybackEngine(bus)
        piece = Piece("Test")
        part = Part("Piano")
        m1 = Measure(1)
        m1.add_note(Note(60, 0, 1))
        m1.add_note(Note(64, 1, 1))
        m2 = Measure(2)
        m2.add_note(Note(67, 0, 2))
        part.add_measure(m1)
        part.add_measure(m2)
        piece.add_part(part)

        engine.set_piece(piece)
        self.assertEqual(len(engine._all_notes), 3)

    def test_play_stop(self):
        from musiai.audio.PlaybackEngine import PlaybackEngine
        from musiai.util.SignalBus import SignalBus
        from musiai.model.Piece import Piece
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note

        bus = SignalBus()
        engine = PlaybackEngine(bus)
        piece = Piece("Test")
        part = Part("Piano")
        m = Measure(1)
        m.add_note(Note(60, 0, 1))
        part.add_measure(m)
        piece.add_part(part)
        engine.set_piece(piece)

        engine.play()
        self.assertEqual(engine.transport.state, "playing")
        engine.stop()
        self.assertEqual(engine.transport.state, "stopped")


if __name__ == "__main__":
    unittest.main()
