"""ReportlabAdapter - MusicXML → PDF via ReportLab (einfach)."""

import logging
import os

logger = logging.getLogger("musiai.pdf.ReportlabAdapter")


class ReportlabAdapter:
    """Einfacher PDF-Export direkt aus Python mit ReportLab."""

    def convert(self, musicxml_path: str, output_path: str,
                on_progress=None) -> None:
        """MusicXML → einfaches PDF (Platzhalter-Layout)."""
        if on_progress:
            on_progress("ReportLab: Erzeuge PDF...")

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(output_path, pagesize=A4)
        c.setFont("Helvetica", 14)
        c.drawString(72, A4[1] - 72, "MusiAI - Notenexport")
        c.setFont("Helvetica", 10)
        c.drawString(72, A4[1] - 100,
                     f"Quelle: {os.path.basename(musicxml_path)}")
        c.drawString(72, A4[1] - 120,
                     "(Vollständiger Notensatz erfordert LilyPond oder MuseScore)")
        c.save()
