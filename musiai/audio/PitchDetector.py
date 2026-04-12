"""PitchDetector - Erkennt Noten aus Audio mit librosa.pyin + Quantisierung."""

import logging
import numpy as np

logger = logging.getLogger("musiai.audio.PitchDetector")


class PitchDetector:
    """Erkennt MIDI-Noten aus Audio-Daten.

    Nutzt librosa.pyin (probabilistic YIN) für Pitch-Tracking
    und gruppiert erkannte Pitches zu diskreten Noten mit
    Quantisierung auf Beat-Raster.
    """

    def __init__(self, tempo_bpm: float = 120.0):
        self.tempo_bpm = tempo_bpm
        self.quantize_grid = 0.25  # Viertel-Beat (Sechzehntelnote)

    def detect(self, samples: np.ndarray, sr: int) -> list[dict]:
        """Audio → Liste von Noten-Dicts.

        Returns:
            [{"pitch": 60, "start_beat": 0.0, "duration_beats": 1.0,
              "velocity": 80, "cent_offset": 3.5}, ...]
        """
        import librosa

        # Pitch tracking mit pyin
        f0, voiced_flag, voiced_prob = librosa.pyin(
            samples, fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'), sr=sr,
            frame_length=2048, hop_length=512,
        )

        times = librosa.times_like(f0, sr=sr, hop_length=512)
        beats_per_sec = self.tempo_bpm / 60.0

        # Frames zu Noten gruppieren
        notes = []
        current_midi = None
        current_start = None
        current_cents = []

        for i, (freq, is_voiced) in enumerate(zip(f0, voiced_flag)):
            t = times[i]
            if is_voiced and not np.isnan(freq) and freq > 0:
                midi_float = librosa.hz_to_midi(freq)
                midi_int = int(round(midi_float))
                cent_off = (midi_float - midi_int) * 100

                if current_midi is None or abs(midi_int - current_midi) > 1:
                    # Neue Note
                    if current_midi is not None:
                        notes.append(self._make_note(
                            current_midi, current_start, t, current_cents,
                            beats_per_sec
                        ))
                    current_midi = midi_int
                    current_start = t
                    current_cents = [cent_off]
                else:
                    current_cents.append(cent_off)
            else:
                # Stille → aktuelle Note beenden
                if current_midi is not None:
                    notes.append(self._make_note(
                        current_midi, current_start, t, current_cents,
                        beats_per_sec
                    ))
                    current_midi = None
                    current_cents = []

        # Letzte Note
        if current_midi is not None and current_start is not None:
            end_t = times[-1] if len(times) > 0 else current_start + 0.5
            notes.append(self._make_note(
                current_midi, current_start, end_t, current_cents,
                beats_per_sec
            ))

        logger.info(f"Erkannt: {len(notes)} Noten aus {len(samples)/sr:.1f}s Audio")
        return notes

    def _make_note(self, midi: int, start_sec: float, end_sec: float,
                   cents: list[float], beats_per_sec: float) -> dict:
        start_beat = start_sec * beats_per_sec
        dur_beat = max(0.1, (end_sec - start_sec) * beats_per_sec)

        # Quantisieren
        start_beat = self._quantize(start_beat)
        dur_beat = self._quantize(max(self.quantize_grid, dur_beat))

        # Mittlerer Cent-Offset
        avg_cent = float(np.mean(cents)) if cents else 0.0
        avg_cent = round(avg_cent, 1)

        # Velocity schätzen (einfach: 80 als Default)
        return {
            "pitch": int(midi),
            "start_beat": float(start_beat),
            "duration_beats": float(dur_beat),
            "velocity": 80,
            "cent_offset": avg_cent,
        }

    def _quantize(self, beat: float) -> float:
        """Auf Beat-Raster quantisieren."""
        return round(beat / self.quantize_grid) * self.quantize_grid
