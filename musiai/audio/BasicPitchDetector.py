"""BasicPitchDetector - Spotify basic-pitch via Python 3.10 Subprocess."""

import logging
import json
import subprocess
import os

logger = logging.getLogger("musiai.audio.BasicPitchDetector")

# Python 3.10 Umgebung für basic-pitch (TF 2.13)
PYTHON310 = os.path.join("python310ENV", "python.exe")

# Inline-Skript das in der Python 3.10 Umgebung läuft
_DETECT_SCRIPT = '''
import os, sys, json
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from basic_pitch.inference import predict

audio_path = sys.argv[1]
tempo_bpm = float(sys.argv[2])
beats_per_measure = float(sys.argv[3])

_, midi_data, note_events = predict(audio_path)

beats_per_sec = tempo_bpm / 60.0
grid = 0.25

def quantize(b):
    return round(b / grid) * grid

notes = []
for ev in note_events:
    start_sec, end_sec, pitch, velocity, _ = ev[0], ev[1], ev[2], ev[3], ev[4]
    start_beat = quantize(start_sec * beats_per_sec)
    dur_beat = quantize(max(grid, (end_sec - start_sec) * beats_per_sec))
    # Taktgrenze
    local = start_beat % beats_per_measure
    max_dur = beats_per_measure - local
    if dur_beat > max_dur:
        dur_beat = quantize(max(grid, max_dur))
    vel_midi = max(1, min(127, int(velocity * 127)))
    notes.append({
        "pitch": int(pitch),
        "start_beat": float(start_beat),
        "duration_beats": float(dur_beat),
        "velocity": vel_midi,
        "cent_offset": 0.0,
    })

print(json.dumps(notes))
'''


class BasicPitchDetector:
    """Polyphoner Noten-Erkenner via Spotify basic-pitch.

    Läuft als Subprocess in einer Python 3.10 Umgebung weil
    basic-pitch TensorFlow <=2.13 braucht.
    """

    def __init__(self, tempo_bpm: float = 120.0,
                 beats_per_measure: float = 4.0):
        self.tempo_bpm = tempo_bpm
        self.beats_per_measure = beats_per_measure

    @staticmethod
    def is_available() -> bool:
        """Prüft ob Python 3.10 + basic-pitch verfügbar ist."""
        if not os.path.exists(PYTHON310):
            return False
        try:
            result = subprocess.run(
                [PYTHON310, "-c", "from basic_pitch.inference import predict"],
                capture_output=True, timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def detect(self, audio_path: str) -> list[dict]:
        """Audio → Noten-Liste via basic-pitch Subprocess."""
        if not os.path.exists(PYTHON310):
            raise RuntimeError(f"Python 3.10 nicht gefunden: {PYTHON310}")

        logger.info(f"basic-pitch: Erkenne Noten in {audio_path}...")
        result = subprocess.run(
            [PYTHON310, "-c", _DETECT_SCRIPT,
             audio_path, str(self.tempo_bpm), str(self.beats_per_measure)],
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode != 0:
            error = result.stderr.strip().split("\n")[-1] if result.stderr else "Unknown"
            raise RuntimeError(f"basic-pitch Fehler: {error}")

        # JSON-Output parsen (letzte Zeile)
        lines = result.stdout.strip().split("\n")
        json_line = lines[-1]
        notes = json.loads(json_line)
        logger.info(f"basic-pitch: {len(notes)} Noten erkannt")
        return notes
