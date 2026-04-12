"""AudioTrack - Audio-Daten einer Stimme (wav/mp3)."""

from __future__ import annotations
import logging
import numpy as np

logger = logging.getLogger("musiai.model.AudioTrack")


class AudioBlock:
    """Ein Abschnitt der Audio-Spur (nach Schnitt)."""

    def __init__(self, samples: np.ndarray, sr: int,
                 start_beat: float = 0.0, source_offset: int = 0):
        self.samples = samples        # Audio-Daten (mono float32)
        self.sr = sr                  # Sample Rate
        self.start_beat = start_beat  # Position im Takt (Beats)
        self.source_offset = source_offset  # Offset in Original-Datei

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / self.sr

    def duration_beats(self, tempo_bpm: float) -> float:
        return self.duration_seconds * (tempo_bpm / 60.0)

    def split_at_second(self, sec: float) -> tuple[AudioBlock, AudioBlock]:
        """Block an Zeitposition aufteilen."""
        idx = int(sec * self.sr)
        idx = max(1, min(idx, len(self.samples) - 1))
        left = AudioBlock(self.samples[:idx], self.sr,
                          self.start_beat, self.source_offset)
        right = AudioBlock(self.samples[idx:], self.sr,
                           self.start_beat + sec * 1.0,  # wird extern korrigiert
                           self.source_offset + idx)
        return left, right


class AudioTrack:
    """Audio-Spur mit Blöcken (geschnitten/verschoben).

    Gehört zu einem Part und wird parallel zu den Noten angezeigt.
    """

    def __init__(self, file_path: str = ""):
        self.file_path = file_path
        self.sr: int = 44100
        self.blocks: list[AudioBlock] = []
        self._full_samples: np.ndarray | None = None

    def load(self, path: str) -> bool:
        """Audio-Datei laden (wav, mp3, flac)."""
        try:
            import librosa
            samples, sr = librosa.load(path, sr=None, mono=True)
            self.file_path = path
            self.sr = sr
            self._full_samples = samples
            self.blocks = [AudioBlock(samples, sr, 0.0, 0)]
            logger.info(f"Audio geladen: {path} ({len(samples)/sr:.1f}s, {sr}Hz)")
            return True
        except Exception as e:
            logger.error(f"Audio laden fehlgeschlagen: {e}")
            return False

    @property
    def duration_seconds(self) -> float:
        if not self.blocks:
            return 0.0
        return max(b.start_beat + b.duration_seconds for b in self.blocks)

    def split_block(self, block_idx: int, offset_seconds: float,
                    tempo_bpm: float) -> None:
        """Block an einer Stelle aufschneiden (S-Taste)."""
        if block_idx >= len(self.blocks):
            return
        block = self.blocks[block_idx]
        if offset_seconds <= 0 or offset_seconds >= block.duration_seconds:
            return
        left, right = block.split_at_second(offset_seconds)
        # Rechten Block-Start korrekt berechnen
        right.start_beat = left.start_beat + left.duration_beats(tempo_bpm)
        self.blocks[block_idx] = left
        self.blocks.insert(block_idx + 1, right)
        logger.info(f"Block {block_idx} geschnitten bei {offset_seconds:.2f}s")

    def move_block(self, block_idx: int, new_start_beat: float) -> None:
        """Block verschieben."""
        if block_idx >= len(self.blocks):
            return
        self.blocks[block_idx].start_beat = max(0.0, new_start_beat)

    def delete_block(self, block_idx: int) -> None:
        """Block löschen."""
        if block_idx < len(self.blocks):
            del self.blocks[block_idx]

    def get_waveform_summary(self, width_pixels: int) -> np.ndarray:
        """Downsampled Waveform für Anzeige (min/max pro Pixel)."""
        if not self._full_samples is not None or len(self._full_samples) == 0:
            return np.zeros(width_pixels)
        samples_per_pixel = max(1, len(self._full_samples) // width_pixels)
        n = width_pixels * samples_per_pixel
        trimmed = self._full_samples[:n]
        reshaped = trimmed.reshape(width_pixels, -1)
        return np.max(np.abs(reshaped), axis=1)
