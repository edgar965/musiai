"""Pdf2MusicxmlAdapter - Experimentelle PDF → Audio → Noten Pipeline."""

import logging

logger = logging.getLogger("musiai.pdf.Pdf2MusicxmlAdapter")


class Pdf2MusicxmlAdapter:
    """Experimentelle Pipeline: PDF → Bild → Audio → Noten → MusicXML."""

    def convert(self, pdf_path: str, output_dir: str,
                on_progress=None) -> str | None:
        """PDF → MusicXML. Noch nicht implementiert."""
        if on_progress:
            on_progress("pdf2musicxml: Experimentelle Pipeline...")
        raise NotImplementedError(
            "pdf2musicxml ist noch nicht implementiert. "
            "Bitte Audiveris oder oemer verwenden."
        )
