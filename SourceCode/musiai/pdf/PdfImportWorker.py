"""PdfImportWorker - Async PDF → MusicXML Konversion."""

import logging
import os
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("musiai.pdf.PdfImportWorker")


class PdfImportWorker(QThread):
    """Konvertiert PDF zu MusicXML in einem Hintergrund-Thread."""

    progress = Signal(str)
    finished = Signal(str)   # Pfad zur erzeugten MusicXML-Datei
    error = Signal(str)

    _ADAPTERS = {
        "audiveris": "musiai.pdf.AudiverisAdapter.AudiverisAdapter",
        "oemer": "musiai.pdf.OemerAdapter.OemerAdapter",
        "pdf2musicxml": "musiai.pdf.Pdf2MusicxmlAdapter.Pdf2MusicxmlAdapter",
    }

    def __init__(self, engine: str, pdf_path: str, output_dir: str):
        super().__init__()
        self._engine = engine
        self._pdf_path = pdf_path
        self._output_dir = output_dir

    def run(self) -> None:
        try:
            adapter = self._create_adapter()
            result = adapter.convert(
                self._pdf_path, self._output_dir,
                on_progress=self.progress.emit,
            )
            if result and os.path.exists(result):
                self.finished.emit(result)
            else:
                self.error.emit("Keine MusicXML-Datei erzeugt")
        except Exception as e:
            logger.error(f"PDF Import fehlgeschlagen: {e}", exc_info=True)
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
