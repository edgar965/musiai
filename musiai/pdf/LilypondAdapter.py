"""LilypondAdapter - MusicXML → PDF via LilyPond."""

import logging
import os
import subprocess

logger = logging.getLogger("musiai.pdf.LilypondAdapter")


class LilypondAdapter:
    """Konvertiert MusicXML zu PDF mit LilyPond."""

    def convert(self, musicxml_path: str, output_path: str,
                on_progress=None) -> None:
        """MusicXML → PDF via musicxml2ly + lilypond."""
        if on_progress:
            on_progress("LilyPond: Konvertiere MusicXML...")

        # Schritt 1: MusicXML → LilyPond (.ly)
        ly_path = output_path.replace(".pdf", ".ly")
        result = subprocess.run(
            ["musicxml2ly", "--output", ly_path, musicxml_path],
            capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(f"musicxml2ly Fehler: {result.stderr[:200]}")

        # Schritt 2: LilyPond → PDF
        if on_progress:
            on_progress("LilyPond: Erzeuge PDF...")
        output_dir = os.path.dirname(output_path)
        result = subprocess.run(
            ["lilypond", "--pdf", "--output", output_dir, ly_path],
            capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(f"LilyPond Fehler: {result.stderr[:200]}")

        if not os.path.exists(output_path):
            raise RuntimeError("PDF-Datei wurde nicht erzeugt")
