"""OMRWorker - Asynchrone Notenerkennung aus Bild/PDF in einem QThread."""

import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("musiai.omr.OMRWorker")


class OMRWorker(QThread):
    """Führt Notenerkennung in einem Hintergrund-Thread aus.

    Signals:
        finished(object): OMRResult bei Erfolg
        error(str): Fehlermeldung
    """

    finished = Signal(object)  # OMRResult
    error = Signal(str)

    def __init__(self, image_path: str, engine: str = "oemer"):
        super().__init__()
        self.image_path = image_path
        self.engine = engine

    def run(self) -> None:
        try:
            from musiai.omr.SheetMusicRecognizer import SheetMusicRecognizer
            result = SheetMusicRecognizer.recognize(
                self.image_path, self.engine)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"OMR fehlgeschlagen: {e}", exc_info=True)
            self.error.emit(str(e))
