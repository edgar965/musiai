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

    def __init__(self, tempo_bpm: float = 120.0,
                 beats_per_measure: float = 4.0):
        self.tempo_bpm = tempo_bpm
        self.beats_per_measure = beats_per_measure
        self.quantize_grid = 0.25  # Sechzehntelnote
        self.min_duration_beats = 0.25  # Mindestdauer

    def detect(self, samples: np.ndarray, sr: int) -> list[dict]:
        """Audio → Liste von Noten-Dicts.

        Returns:
            [{"pitch": 60, "start_beat": 0.0, "duration_beats": 1.0,
              "velocity": 80, "cent_offset": 3.5}, ...]
        """
        import librosa

        f0, voiced_flag, voiced_prob = librosa.pyin(
            samples, fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'), sr=sr,
            frame_length=2048, hop_length=512,
        )

        times = librosa.times_like(f0, sr=sr, hop_length=512)
        beats_per_sec = self.tempo_bpm / 60.0

        # Frames zu Noten gruppieren
        raw_notes = []
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
                    if current_midi is not None:
                        raw_notes.append(self._make_note(
                            current_midi, current_start, t, current_cents,
                            beats_per_sec
                        ))
                    current_midi = midi_int
                    current_start = t
                    current_cents = [cent_off]
                else:
                    current_cents.append(cent_off)
            else:
                if current_midi is not None:
                    raw_notes.append(self._make_note(
                        current_midi, current_start, t, current_cents,
                        beats_per_sec
                    ))
                    current_midi = None
                    current_cents = []

        if current_midi is not None and current_start is not None:
            end_t = times[-1] if len(times) > 0 else current_start + 0.5
            raw_notes.append(self._make_note(
                current_midi, current_start, end_t, current_cents,
                beats_per_sec
            ))

        # Nachbearbeitung
        notes = self._cleanup_notes(raw_notes)
        logger.info(f"Erkannt: {len(notes)} Noten aus {len(samples)/sr:.1f}s Audio")
        return notes

    def _make_note(self, midi: int, start_sec: float, end_sec: float,
                   cents: list[float], beats_per_sec: float) -> dict:
        start_beat = start_sec * beats_per_sec
        dur_beat = max(0.1, (end_sec - start_sec) * beats_per_sec)

        # Quantisieren
        start_beat = self._quantize(start_beat)
        dur_beat = self._quantize(max(self.quantize_grid, dur_beat))

        avg_cent = float(np.mean(cents)) if cents else 0.0
        avg_cent = round(avg_cent, 1)
        # Cent nur behalten wenn deutlich (>5ct)
        if abs(avg_cent) < 5:
            avg_cent = 0.0

        return {
            "pitch": int(midi),
            "start_beat": float(start_beat),
            "duration_beats": float(dur_beat),
            "velocity": 80,
            "cent_offset": avg_cent,
        }

    def _cleanup_notes(self, notes: list[dict]) -> list[dict]:
        """Noten bereinigen: filtern, Taktgrenzen, Überlappungen."""
        if not notes:
            return []

        # 1. Zu kurze Noten entfernen
        notes = [n for n in notes if n["duration_beats"] >= self.min_duration_beats]

        # 2. Nach Start sortieren
        notes.sort(key=lambda n: n["start_beat"])

        # 3. Überlappungen entfernen: Note darf nicht über nächste Note hinausgehen
        for i in range(len(notes) - 1):
            end = notes[i]["start_beat"] + notes[i]["duration_beats"]
            next_start = notes[i + 1]["start_beat"]
            if end > next_start:
                notes[i]["duration_beats"] = max(
                    self.quantize_grid, next_start - notes[i]["start_beat"]
                )

        # 4. Noten an Taktgrenzen kürzen
        bpm = self.beats_per_measure
        for n in notes:
            measure_start = int(n["start_beat"] / bpm) * bpm
            measure_end = measure_start + bpm
            local_start = n["start_beat"] - measure_start
            max_dur = bpm - local_start
            if n["duration_beats"] > max_dur:
                n["duration_beats"] = self._quantize(max(self.quantize_grid, max_dur))

        # 5. Duplikate entfernen (gleicher Pitch + gleicher Start)
        seen = set()
        unique = []
        for n in notes:
            key = (n["pitch"], n["start_beat"])
            if key not in seen:
                seen.add(key)
                unique.append(n)

        return unique

    def _quantize(self, beat: float) -> float:
        return round(beat / self.quantize_grid) * self.quantize_grid
