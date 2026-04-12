"""DemucsDetector - Source Separation + Pitch Detection pro Stimme."""

import logging
import numpy as np
import tempfile
import os

logger = logging.getLogger("musiai.audio.DemucsDetector")


class DemucsDetector:
    """Trennt Audio in Stimmen mit demucs, dann pyin pro Stimme.

    Workflow:
    1. demucs trennt in: vocals, bass, drums, other
    2. librosa.pyin erkennt Noten in jeder nicht-Drum Stimme
    3. Ergebnis: Dict mit Stimm-Namen → Noten-Listen
    """

    STEM_NAMES = ["vocals", "bass", "other"]  # drums ignorieren

    def __init__(self, tempo_bpm: float = 120.0,
                 beats_per_measure: float = 4.0):
        self.tempo_bpm = tempo_bpm
        self.beats_per_measure = beats_per_measure

    def detect(self, audio_path: str) -> dict[str, list[dict]]:
        """Audio → {stem_name: [note_dicts]}.

        Returns dict mit Stimm-Namen als Keys und Noten-Listen als Values.
        """
        import torch
        import demucs.pretrained
        import demucs.apply
        import torchaudio

        logger.info(f"Demucs: Lade {audio_path}...")

        # Audio laden (torchaudio oder librosa als Fallback)
        try:
            waveform, sr = torchaudio.load(audio_path)
        except Exception:
            import librosa
            y, sr = librosa.load(audio_path, sr=44100, mono=False)
            if y.ndim == 1:
                y = np.stack([y, y])
            waveform = torch.from_numpy(y)
            logger.info("Audio via librosa geladen (torchaudio Fallback)")

        # Auf Stereo erweitern falls Mono
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        # Demucs Modell laden
        model = demucs.pretrained.get_model("htdemucs")
        model.eval()

        # Source Separation
        logger.info("Demucs: Trenne Stimmen...")
        ref = waveform.mean(0)
        waveform = (waveform - ref.mean()) / ref.std()
        sources = demucs.apply.apply_model(
            model, waveform.unsqueeze(0), device="cpu"
        )
        sources = sources[0]  # Batch-Dimension entfernen

        # sources: [4, 2, samples] → drums, bass, other, vocals
        source_names = model.sources  # ['drums', 'bass', 'other', 'vocals']

        # Pro Stimme Noten erkennen
        from musiai.audio.PitchDetector import PitchDetector
        detector = PitchDetector(
            tempo_bpm=self.tempo_bpm,
            beats_per_measure=self.beats_per_measure,
        )

        results = {}
        for i, name in enumerate(source_names):
            if name == "drums":
                continue
            logger.info(f"Demucs: Erkenne Noten in '{name}'...")
            # Stereo → Mono, torch → numpy
            stem_audio = sources[i].mean(0).numpy().astype(np.float32)
            # Resample auf 22050 für pyin
            import librosa
            if sr != 22050:
                stem_audio = librosa.resample(
                    stem_audio, orig_sr=sr, target_sr=22050
                )
            notes = detector.detect(stem_audio, 22050)
            if notes:
                results[name] = notes
                logger.info(f"  {name}: {len(notes)} Noten")

        logger.info(f"Demucs: Fertig. {len(results)} Stimmen erkannt.")
        return results
