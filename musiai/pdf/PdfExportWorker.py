"""PdfExportWorker - Async MusicXML → PDF Konversion."""

import logging
import os
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("musiai.pdf.PdfExportWorker")


class PdfExportWorker(QThread):
    """Konvertiert MusicXML zu PDF in einem Hintergrund-Thread."""

    progress = Signal(str)
    finished = Signal(str)   # Pfad zur erzeugten PDF-Datei
    error = Signal(str)

    _ADAPTERS = {
        "lilypond": "musiai.pdf.LilypondAdapter.LilypondAdapter",
        "musescore": "musiai.pdf.MusescoreAdapter.MusescoreAdapter",
        "reportlab": "musiai.pdf.ReportlabAdapter.ReportlabAdapter",
    }

    def __init__(self, engine: str, musicxml_path: str, output_path: str):
        super().__init__()
        self._engine = engine
        self._musicxml_path = musicxml_path
        self._output_path = output_path

    def run(self) -> None:
        try:
            adapter = self._create_adapter()
            adapter.convert(
                self._musicxml_path, self._output_path,
                on_progress=self.progress.emit,
            )
            if os.path.exists(self._output_path):
                self.finished.emit(self._output_path)
        except Exception as e:
            logger.error(f"PDF Export fehlgeschlagen: {e}", exc_info=True)
            self.error.emit(str(e))

    def _create_adapter(self):
        """Adapter-Instanz für die gewählte Engine erstellen."""
        class_path = self._ADAPTERS.get(self._engine)
        if not class_path:
            raise ValueError(f"Unbekannte Engine: {self._engine}")
        module_path, class_name = class_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()
