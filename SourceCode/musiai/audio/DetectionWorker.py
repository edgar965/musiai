"""DetectionWorker - Asynchrone Notenerkennung in einem QThread."""

import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("musiai.audio.DetectionWorker")


class DetectionWorker(QThread):
    """Führt Notenerkennung in einem Hintergrund-Thread aus.

    Signals:
        progress(str): Status-Text (z.B. "Trenne Stimmen...")
        finished(list): Ergebnis-Liste [{stem: notes}, ...] oder [notes]
        error(str): Fehlermeldung
    """

    progress = Signal(str)
    finished = Signal(object)  # dict oder list
    error = Signal(str)

    def __init__(self, engine: str, audio_path: str,
                 tempo_bpm: float, beats_per_measure: float = 4.0):
        super().__init__()
        self.engine = engine
        self.audio_path = audio_path
        self.tempo_bpm = tempo_bpm
        self.beats_per_measure = beats_per_measure

    def run(self) -> None:
        try:
            if self.engine == "basic-pitch":
                self._run_basic_pitch()
            elif self.engine == "demucs+pyin":
                self._run_demucs()
            else:
                self._run_pyin()
        except Exception as e:
            logger.error(f"Detection Worker Fehler: {e}", exc_info=True)
            self.error.emit(str(e))

    def _run_pyin(self) -> None:
        self.progress.emit("Lade Audio...")
        import librosa
        import numpy as np

        y, sr = librosa.load(self.audio_path, sr=22050, mono=True)
        if len(y) > sr * 30:
            y = y[:sr * 30]

        self.progress.emit("Erkenne Tonhöhen (pyin)...")
        from musiai.audio.PitchDetector import PitchDetector
        det = PitchDetector(self.tempo_bpm, self.beats_per_measure)
        notes = det.detect(y, sr)

        self.progress.emit(f"{len(notes)} Noten erkannt")
        self.finished.emit({"pyin": notes})

    def _run_demucs(self) -> None:
        self.progress.emit("Lade demucs Modell...")
        import torch
        import demucs.pretrained
        import demucs.apply
        import numpy as np

        model = demucs.pretrained.get_model("htdemucs")
        model.eval()

        self.progress.emit("Lade Audio...")
        try:
            import torchaudio
            waveform, sr = torchaudio.load(self.audio_path)
        except Exception:
            import librosa
            y, sr = librosa.load(self.audio_path, sr=44100, mono=False)
            if y.ndim == 1:
                y = np.stack([y, y])
            waveform = torch.from_numpy(y)

        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        self.progress.emit("Trenne Stimmen (demucs)...")
        ref = waveform.mean(0)
        waveform_norm = (waveform - ref.mean()) / ref.std()
        sources = demucs.apply.apply_model(
            model, waveform_norm.unsqueeze(0), device="cpu"
        )[0]

        source_names = model.sources
        from musiai.audio.PitchDetector import PitchDetector
        import librosa

        results = {}
        for i, name in enumerate(source_names):
            if name == "drums":
                continue
            self.progress.emit(f"Erkenne Noten: {name}...")
            stem = sources[i].mean(0).numpy().astype(np.float32)
            if sr != 22050:
                stem = librosa.resample(stem, orig_sr=sr, target_sr=22050)
            det = PitchDetector(self.tempo_bpm, self.beats_per_measure)
            notes = det.detect(stem, 22050)
            if notes:
                results[name] = notes

        total = sum(len(n) for n in results.values())
        self.progress.emit(f"{total} Noten in {len(results)} Stimmen")
        self.finished.emit(results)

    def _run_basic_pitch(self) -> None:
        self.progress.emit("Starte basic-pitch (extern)...")
        from musiai.audio.BasicPitchDetector import BasicPitchDetector
        det = BasicPitchDetector(self.tempo_bpm, self.beats_per_measure)
        notes = det.detect(self.audio_path)
        self.progress.emit(f"{len(notes)} Noten erkannt")
        self.finished.emit({"basic-pitch": notes})
