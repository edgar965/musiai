"""BeatDetectWorker - Asynchrone Beat-Erkennung in einem QThread."""

import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("musiai.audio.BeatDetectWorker")


class BeatDetectWorker(QThread):
    """Führt Beat-Erkennung in einem Hintergrund-Thread aus.

    Signals:
        finished(object): BeatResult bei Erfolg
        error(str): Fehlermeldung
    """

    finished = Signal(object)  # BeatResult
    error = Signal(str)

    def __init__(self, audio_path: str, engine: str = "librosa"):
        super().__init__()
        self.audio_path = audio_path
        self.engine = engine

    def run(self) -> None:
        try:
            from musiai.audio.BeatDetector import BeatDetector
            result = BeatDetector.detect(self.audio_path, self.engine)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Beat-Erkennung fehlgeschlagen: {e}", exc_info=True)
            self.error.emit(str(e))
