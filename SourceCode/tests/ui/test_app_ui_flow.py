"""UI-Integration Tests — testen den echten AppController Flow.

Tests die den vollständigen Pfad testen: Controller → Model → Scene.
Kein Mocking, echte Objekte.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_qapp = None
def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)

MP3_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'media', 'mp3', 'test.mp3'))

MXL_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'media', 'music',
    'musicXML', '_Echte',
    'Beethoven - Sonata 30, Mvt.3. {Professional production score.}.mxl'))


def _create_controller():
    """Create a full AppController for testing."""
    _ensure_qapp()
    from musiai.controller.AppController import AppController
    ctrl = AppController()
    return ctrl


def _create_test_piece():
    """Create a simple test piece with notes."""
    from musiai.model.Piece import Piece
    from musiai.model.Part import Part
    from musiai.model.Measure import Measure
    from musiai.model.Note import Note
    from musiai.model.Expression import Expression
    from musiai.model.TimeSignature import TimeSignature

    piece = Piece("Test Piece")
    part = Part("Piano")
    for i in range(4):
        m = Measure(i + 1, TimeSignature(4, 4))
        m.add_note(Note(60 + i, 0.0, 1.0, Expression(velocity=80)))
        m.add_note(Note(64 + i, 1.0, 1.0, Expression(velocity=80)))
        part.add_measure(m)
    piece.add_part(part)
    return piece


def _load_piece(ctrl):
    """Load a test piece into the controller, return (piece, scene, ec)."""
    piece = _create_test_piece()
    ctrl.project.add_piece(piece)
    ctrl._open_piece_in_tab(piece)
    tab = ctrl._active_tab
    if tab:
        return piece, tab.notation_scene, tab.edit_controller
    return piece, None, None


# ==============================================================
# Audio Import Tests
# ==============================================================

class TestAudioVoiceImport(unittest.TestCase):
    """Test: Bearbeiten → Neue Stimme — Aufnahme (MP3)."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_active_piece_exists_after_load(self):
        """After loading a file, _active_piece() returns the piece."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)
        active = ctrl._active_piece()
        self.assertIsNotNone(active, "_active_piece() must not be None")

    def test_active_scene_exists_after_load(self):
        """After loading, _active_scene() returns the scene."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)
        active_scene = ctrl._active_scene()
        self.assertIsNotNone(active_scene)

    def test_add_audio_voice_full_flow(self):
        """Call _add_audio_voice with mocked file dialog → part added."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)
        parts_before = len(piece.parts)

        # Mock the file dialog to return test.mp3
        from unittest.mock import patch
        with patch('musiai.controller.AppController.QFileDialog') as mock:
            mock.getOpenFileName.return_value = (MP3_PATH, "Audio")
            ctrl._add_audio_voice()

        self.assertEqual(len(piece.parts), parts_before + 1,
                         "Audio part must be added after _add_audio_voice")
        self.assertIsNotNone(piece.parts[-1].audio_track,
                             "Last part must have audio_track")
        self.assertIn("Audio:", piece.parts[-1].name)

    def test_scene_has_waveform_after_audio_add(self):
        """After adding audio, scene must have waveform items (any mode)."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)

        from unittest.mock import patch
        with patch('musiai.controller.AppController.QFileDialog') as mock:
            mock.getOpenFileName.return_value = (MP3_PATH, "Audio")
            ctrl._add_audio_voice()

        waveforms = [i for i in scene.items() if i.data(0) == "waveform"]
        self.assertGreater(len(waveforms), 0,
                           "Waveform items must appear in scene")


# ==============================================================
# Note Selection + Properties Tests
# ==============================================================

class TestNoteSelectionFlow(unittest.TestCase):
    """Test: Click note → Properties → Change → Save."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_staff_note_click_selects_in_ec(self):
        """Clicking a staff note selects it in EditController."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)

        note = piece.parts[0].measures[0].notes[0]

        # Simulate _on_staff_note_clicked
        class FakeChord:
            start_time = 0
        class FakeND:
            number = note.pitch
            velocity = note.expression.velocity

        ctrl._on_staff_note_clicked(FakeChord(), FakeND(), 0, False, False)
        self.assertEqual(len(ec._selected_notes), 1)
        self.assertEqual(ec._selected_notes[0], note)

    def test_velocity_change_applies_to_model(self):
        """Changing velocity via EC updates the model note."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)

        note = piece.parts[0].measures[0].notes[0]
        ec._selected_notes = [note]
        old_vel = note.expression.velocity

        ec.change_velocity(100)
        self.assertEqual(note.expression.velocity, 100)

    def test_cent_change_applies_to_model(self):
        """Changing cent offset via EC updates the model note."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)

        note = piece.parts[0].measures[0].notes[0]
        ec._selected_notes = [note]

        ec.change_cent_offset(30.0, "zigzag")
        self.assertAlmostEqual(note.expression.cent_offset, 30.0)
        self.assertEqual(note.expression.glide_type, "zigzag")

    def test_save_and_refresh_updates_scene(self):
        """Alt+S applies changes and refreshes scene."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)

        note = piece.parts[0].measures[0].notes[0]
        ec._selected_notes = [note]
        note.expression.velocity = 120
        note.expression.cent_offset = 25.0

        # Simulate Alt+S
        ctrl._save_and_refresh()

        # Scene should have refreshed without error
        self.assertGreater(len(list(scene.items())), 0)


# ==============================================================
# New Project / New Voice Tests
# ==============================================================

class TestNewProjectFlow(unittest.TestCase):
    """Test: Ctrl+N → new empty project."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_new_project_creates_tab(self):
        ctrl = _create_controller()
        tabs_before = ctrl.main_window.tab_widget.tab_count()
        ctrl._new_project()
        tabs_after = ctrl.main_window.tab_widget.tab_count()
        self.assertEqual(tabs_after, tabs_before + 1)

    def test_new_project_has_piece(self):
        ctrl = _create_controller()
        ctrl._new_project()
        piece = ctrl._active_piece()
        self.assertIsNotNone(piece)
        self.assertEqual(piece.title, "Neues Projekt")

    def test_add_new_voice(self):
        """Bearbeiten → Neue Stimme adds a part."""
        ctrl = _create_controller()
        piece, scene, ec = _load_piece(ctrl)
        self.assertIsNotNone(piece)
        parts_before = len(piece.parts)
        ctrl._add_new_voice()
        self.assertEqual(len(piece.parts), parts_before + 1)


# ==============================================================
# MP3 + Beat Detection Full Pipeline
# ==============================================================

class TestMP3BeatPipeline(unittest.TestCase):
    """Full pipeline: MP3 → Beat detection → create beat track."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_mp3_load_and_beat_detect_librosa(self):
        """Load MP3, detect beats with librosa, create beat part."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.audio.BeatDetector import BeatDetector
        result = BeatDetector.detect(MP3_PATH, "librosa")
        self.assertGreater(len(result.beat_times), 0)
        self.assertGreater(result.bpm, 0)

        # Create a piece with audio + beat track
        ctrl = _create_controller()
        ctrl._new_project()
        piece = ctrl._active_piece()
        self.assertIsNotNone(piece)

        # Add audio part
        from musiai.model.AudioTrack import AudioTrack
        from musiai.model.Part import Part
        from musiai.model.Measure import Measure
        from musiai.model.Note import Note
        from musiai.model.TimeSignature import TimeSignature

        track = AudioTrack()
        self.assertTrue(track.load(MP3_PATH))
        audio_part = Part(name="Audio: test", channel=1)
        audio_part.audio_track = track
        ts = TimeSignature(4, 4)
        n = max(1, int(result.bpm * track.duration_seconds / 60 / 4) + 1)
        for i in range(n):
            audio_part.add_measure(Measure(i + 1, ts))
        piece.add_part(audio_part)

        # Create beat part from detection result
        beat_part = Part(name="Beats", channel=2)
        beat_interval = 60.0 / result.bpm
        for i in range(n):
            m = Measure(i + 1, ts)
            # Add beat notes (woodblock-style) from beat_times
            measure_start = i * 4 * beat_interval
            for bt in result.beat_times:
                local = bt - measure_start
                if 0 <= local < 4 * beat_interval:
                    beat_in_measure = local / beat_interval
                    m.add_note(Note(60, beat_in_measure, 0.25))
            beat_part.add_measure(m)
        piece.add_part(beat_part)

        self.assertEqual(len(piece.parts), 3)  # original + audio + beats
        total_beat_notes = sum(
            len(m.notes) for m in beat_part.measures)
        self.assertGreater(total_beat_notes, 0,
                           "Beat part should have notes")

    def test_mp3_load_and_beat_detect_madmom(self):
        """Load MP3, detect beats with madmom, verify result."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.audio.BeatDetector import BeatDetector
        if not BeatDetector.detect_available().get("madmom"):
            self.skipTest("madmom not available")
        result = BeatDetector.detect(MP3_PATH, "madmom")
        self.assertEqual(result.engine, "madmom")
        self.assertGreater(len(result.beat_times), 3)
        self.assertGreater(result.bpm, 30)
        self.assertGreater(len(result.tempo_curve), 0)


# ==============================================================
# Beat Detection UI Flow (Tools → Beat erkennen)
# ==============================================================

class TestBeatDetectionUIFlow(unittest.TestCase):
    """Test: Tools → Beat erkennen (Audio) full UI flow."""

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def _run_detection(self, engine):
        """Helper: add audio voice, then beat detect via context menu."""
        ctrl = _create_controller()
        ctrl._new_project()
        ctrl._beat_engine = engine

        # 1) Add audio voice first
        from unittest.mock import patch
        with patch('musiai.controller.AppController.QFileDialog') as mock:
            mock.getOpenFileName.return_value = (MP3_PATH, "Audio")
            ctrl._add_audio_voice()

        # 2) Find audio part index
        piece = ctrl._active_piece()
        audio_idx = None
        for i, p in enumerate(piece.parts):
            if p.audio_track:
                audio_idx = i
                break

        # 3) Beat detect on that part (context menu flow)
        if audio_idx is not None:
            ctrl._on_beat_detect_part(audio_idx)

        return ctrl, ctrl._active_piece()

    def test_librosa_creates_audio_and_beat_parts(self):
        """librosa: MP3 laden → Beats erkennen → 2 Stimmen angelegt."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl, piece = self._run_detection("librosa")
        # Original "Stimme 1" + "Audio: test" + "Beats (librosa)"
        self.assertGreaterEqual(len(piece.parts), 3,
            f"Erwartet 3 Parts, bekommen {len(piece.parts)}: "
            f"{[p.name for p in piece.parts]}")
        audio_parts = [p for p in piece.parts if p.audio_track]
        self.assertEqual(len(audio_parts), 1, "1 Audio-Stimme erwartet")
        beat_parts = [p for p in piece.parts if "Beats" in p.name]
        self.assertEqual(len(beat_parts), 1, "1 Beat-Stimme erwartet")
        beat_notes = sum(len(m.notes) for m in beat_parts[0].measures)
        self.assertGreater(beat_notes, 3,
            f"Beat-Stimme muss Noten haben, hat {beat_notes}")

    def test_madmom_creates_audio_and_beat_parts(self):
        """madmom: MP3 laden → Beats erkennen → 2 Stimmen angelegt."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        from musiai.audio.BeatDetector import BeatDetector
        if not BeatDetector.detect_available().get("madmom"):
            self.skipTest("madmom not available")
        ctrl, piece = self._run_detection("madmom")
        self.assertGreaterEqual(len(piece.parts), 3)
        beat_parts = [p for p in piece.parts if "Beats" in p.name]
        self.assertEqual(len(beat_parts), 1)
        beat_notes = sum(len(m.notes) for m in beat_parts[0].measures)
        self.assertGreater(beat_notes, 3)

    def test_librosa_dynamic_creates_parts(self):
        """librosa_dynamic: MP3 → Beats → Stimmen."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl, piece = self._run_detection("librosa_dynamic")
        self.assertGreaterEqual(len(piece.parts), 3)

    def test_beat_part_has_correct_tempo(self):
        """Das Piece bekommt das erkannte Tempo."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl, piece = self._run_detection("librosa")
        self.assertGreater(piece.initial_tempo, 30)
        self.assertLess(piece.initial_tempo, 300)

    def test_scene_shows_beats_after_detection(self):
        """Nach Beat-Erkennung zeigt die Scene Pixmaps an."""
        if not os.path.exists(MP3_PATH):
            self.skipTest("test.mp3 not found")
        ctrl, piece = self._run_detection("librosa")
        scene = ctrl._active_scene()
        self.assertIsNotNone(scene)
        self.assertGreater(len(list(scene.items())), 0)

    def test_cancel_does_nothing(self):
        """Dialog abbrechen → kein Crash, keine Änderung."""
        ctrl = _create_controller()
        ctrl._new_project()
        parts_before = len(ctrl._active_piece().parts)
        from unittest.mock import patch
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=("", "")):
            ctrl._run_beat_detection()
        self.assertEqual(len(ctrl._active_piece().parts), parts_before)


if __name__ == "__main__":
    unittest.main()
