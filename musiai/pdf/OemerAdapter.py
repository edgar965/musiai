"""OemerAdapter - PDF → MusicXML via oemer (Deep Learning OMR)."""

import logging

logger = logging.getLogger("musiai.pdf.OemerAdapter")


class OemerAdapter:
    """Konvertiert PDF zu MusicXML mit oemer (neuronales Netz)."""

    def convert(self, pdf_path: str, output_dir: str,
                on_progress=None) -> str | None:
        """PDF → MusicXML. Gibt Pfad zur erzeugten Datei zurück."""
        if on_progress:
            on_progress("oemer: Starte neuronale Erkennung...")

        import oemer
        result_path = oemer.recognize(pdf_path)
        if result_path:
            return str(result_path)
        return None
