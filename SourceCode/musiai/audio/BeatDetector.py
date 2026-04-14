"""BeatDetector - Erkennt Beats, Tempo und Taktart aus Audio."""

import logging
import numpy as np

logger = logging.getLogger("musiai.audio.BeatDetector")


class BeatResult:
    """Ergebnis einer Beat-Erkennung."""

    def __init__(self):
        self.bpm: float = 120.0
        self.beat_times: list[float] = []   # Sekunden
        self.downbeat_indices: list[int] = []  # Indices in beat_times
        self.time_signature: tuple[int, int] = (4, 4)
        self.tempo_curve: list[tuple[float, float]] = []  # (time, bpm)
        self.engine: str = ""

    def beats_per_measure(self) -> int:
        return self.time_signature[0]

    def tempo_at(self, time: float) -> float:
        """BPM an einer bestimmten Zeitposition."""
        if not self.tempo_curve:
            return self.bpm
        result = self.tempo_curve[0][1]
        for t, bpm in self.tempo_curve:
            if t <= time:
                result = bpm
            else:
                break
        return result


class BeatDetector:
    """Beat-Erkennung mit verschiedenen Engines."""

    ENGINES = {
        "librosa": {
            "name": "librosa beat_track",
            "desc": "Standard Beat-Tracking. Schnell, gute Grundlage.",
            "module": "librosa",
        },
        "librosa_dynamic": {
            "name": "librosa dynamic tempo",
            "desc": "Beat-Tracking mit Tempo-Kurve pro Beat.\n"
                    "Erkennt Tempo-Schwankungen (rit./accel.).",
            "module": "librosa",
        },
        "madmom": {
            "name": "madmom RNN (Python 3.10)",
            "desc": "Neuronales Netz für Beat/Downbeat.\n"
                    "Beste Genauigkeit, braucht Python 3.10.",
            "module": "madmom",
        },
    }

    @staticmethod
    def detect_available() -> dict[str, bool]:
        """Prüft welche Engines installiert sind."""
        result = {}
        for key, info in BeatDetector.ENGINES.items():
            if key == "madmom":
                import os
                base = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", "..", ".."))
                result[key] = os.path.exists(
                    os.path.join(base, "python310ENV", "python.exe"))
            else:
                try:
                    __import__(info["module"])
                    result[key] = True
                except ImportError:
                    result[key] = False
        return result

    @staticmethod
    def detect(audio_path: str, engine: str = "librosa") -> BeatResult:
        """Beat-Erkennung mit der gewählten Engine."""
        if engine == "librosa":
            return BeatDetector._detect_librosa(audio_path)
        elif engine == "librosa_dynamic":
            return BeatDetector._detect_librosa_dynamic(audio_path)
        elif engine == "madmom":
            return BeatDetector._detect_madmom(audio_path)
        else:
            raise ValueError(f"Unbekannte Engine: {engine}")

    @staticmethod
    def _detect_librosa(audio_path: str) -> BeatResult:
        """librosa beat_track — globales Tempo + Beat-Positionen."""
        import librosa
        logger.info(f"librosa beat_track: {audio_path}")

        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        result = BeatResult()
        result.engine = "librosa"
        result.bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
        result.beat_times = beat_times.tolist()

        # Estimate time signature from beat spacing
        result.time_signature = BeatDetector._estimate_time_sig(
            beat_times, result.bpm)

        # Tempo curve from inter-beat intervals
        result.tempo_curve = BeatDetector._build_tempo_curve(beat_times)

        logger.info(f"librosa: {result.bpm:.1f} BPM, "
                    f"{len(result.beat_times)} beats, "
                    f"{result.time_signature[0]}/{result.time_signature[1]}")
        return result

    @staticmethod
    def _detect_librosa_dynamic(audio_path: str) -> BeatResult:
        """librosa mit dynamischer Tempo-Schätzung pro Beat."""
        import librosa
        logger.info(f"librosa dynamic: {audio_path}")

        y, sr = librosa.load(audio_path, sr=22050, mono=True)

        # Onset strength for tempo estimation
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        # Dynamic tempo (per-frame)
        dtempo = librosa.feature.tempo(
            onset_envelope=onset_env, sr=sr, aggregate=None)

        # Global beat tracking
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        result = BeatResult()
        result.engine = "librosa_dynamic"
        result.bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
        result.beat_times = beat_times.tolist()
        result.time_signature = BeatDetector._estimate_time_sig(
            beat_times, result.bpm)

        # Build tempo curve from inter-beat intervals (more accurate)
        result.tempo_curve = BeatDetector._build_tempo_curve(beat_times)

        # Enhance with frame-level tempo where available
        if len(dtempo) > 0:
            frame_times = librosa.frames_to_time(
                np.arange(len(dtempo)), sr=sr)
            # Sample at beat positions
            for i, bt in enumerate(beat_times):
                idx = np.searchsorted(frame_times, bt)
                if idx < len(dtempo):
                    # Blend: 70% from IBIs, 30% from frame tempo
                    if i < len(result.tempo_curve):
                        ibi_bpm = result.tempo_curve[i][1]
                        frame_bpm = float(dtempo[idx])
                        blended = 0.7 * ibi_bpm + 0.3 * frame_bpm
                        result.tempo_curve[i] = (bt, blended)

        logger.info(f"librosa_dynamic: {result.bpm:.1f} BPM, "
                    f"{len(result.beat_times)} beats, "
                    f"tempo range: {min(t[1] for t in result.tempo_curve):.0f}"
                    f"-{max(t[1] for t in result.tempo_curve):.0f}")
        return result

    @staticmethod
    def _detect_madmom(audio_path: str) -> BeatResult:
        """madmom RNN — via separaten Python 3.10 Prozess."""
        import subprocess
        import json
        import os
        logger.info(f"madmom RNN: {audio_path}")

        # Look for python310ENV relative to project root
        base = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", ".."))
        python310 = os.path.join(base, "python310ENV", "python.exe")
        if not os.path.exists(python310):
            raise RuntimeError(
                f"madmom braucht {python310}")

        script = '''
import sys, json
import madmom
proc = madmom.features.beats.RNNBeatProcessor()
act = proc(sys.argv[1])
dbn = madmom.features.beats.DBNBeatTrackingProcessor(fps=100)
beats = dbn(act)
# Downbeats
try:
    db_proc = madmom.features.downbeats.RNNDownBeatProcessor()
    db_act = db_proc(sys.argv[1])
    db_dbn = madmom.features.downbeats.DBNDownBeatTrackingProcessor(
        beats_per_bar=[3, 4], fps=100)
    downbeats = db_dbn(db_act)
    result = {"beats": beats.tolist(),
              "downbeats": downbeats.tolist()}
except Exception:
    result = {"beats": beats.tolist(), "downbeats": []}
print(json.dumps(result))
'''
        proc = subprocess.run(
            [python310, "-c", script, audio_path],
            capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"madmom failed: {proc.stderr}")

        data = json.loads(proc.stdout)
        beat_times = np.array(data["beats"])

        result = BeatResult()
        result.engine = "madmom"
        result.beat_times = beat_times.tolist()
        result.tempo_curve = BeatDetector._build_tempo_curve(beat_times)
        result.bpm = np.median([t[1] for t in result.tempo_curve]) \
            if result.tempo_curve else 120.0

        # Downbeat info for time signature
        if data.get("downbeats"):
            db = np.array(data["downbeats"])
            # db[:,0] = time, db[:,1] = beat position (1-based)
            if db.ndim == 2 and db.shape[1] >= 2:
                max_beat = int(db[:, 1].max())
                result.time_signature = (max_beat, 4)
                result.downbeat_indices = [
                    i for i, b in enumerate(beat_times)
                    if any(abs(b - db[j, 0]) < 0.05
                           for j in range(len(db)) if db[j, 1] == 1)
                ]
        else:
            result.time_signature = BeatDetector._estimate_time_sig(
                beat_times, result.bpm)

        logger.info(f"madmom: {result.bpm:.1f} BPM, "
                    f"{len(result.beat_times)} beats")
        return result

    @staticmethod
    def _build_tempo_curve(beat_times) -> list[tuple[float, float]]:
        """Tempo-Kurve aus Beat-Abständen (Inter-Beat-Intervalle)."""
        if len(beat_times) < 2:
            return [(0.0, 120.0)]
        curve = []
        for i in range(1, len(beat_times)):
            ibi = beat_times[i] - beat_times[i - 1]
            if ibi > 0:
                bpm = 60.0 / ibi
                curve.append((float(beat_times[i - 1]), bpm))
        return curve

    @staticmethod
    def _estimate_time_sig(beat_times, global_bpm) -> tuple[int, int]:
        """Taktart schätzen aus Beat-Positionen."""
        if len(beat_times) < 8:
            return (4, 4)
        # Look for accent pattern by onset strength periodicity
        # Simple heuristic: check if beats group in 3s or 4s
        ibis = np.diff(beat_times)
        median_ibi = np.median(ibis)
        # If some IBIs are ~1.5x median, likely compound meter
        long_beats = np.sum(ibis > median_ibi * 1.3)
        if long_beats > len(ibis) * 0.2:
            return (3, 4)
        return (4, 4)
