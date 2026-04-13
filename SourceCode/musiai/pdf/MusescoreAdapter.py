"""MusescoreAdapter - MusicXML → PDF via MuseScore CLI."""

import logging
import os
import subprocess

logger = logging.getLogger("musiai.pdf.MusescoreAdapter")

MUSESCORE_COMMANDS = ["mscore", "musescore", "MuseScore4"]


class MusescoreAdapter:
    """Konvertiert MusicXML zu PDF mit MuseScore CLI."""

    def convert(self, musicxml_path: str, output_path: str,
                on_progress=None) -> None:
        """MusicXML → PDF via MuseScore Batch-Export."""
        if on_progress:
            on_progress("MuseScore: Exportiere PDF...")

        for cmd_name in MUSESCORE_COMMANDS:
            try:
                result = subprocess.run(
                    [cmd_name, "-o", output_path, musicxml_path],
                    capture_output=True, text=True, timeout=120,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0 and os.path.exists(output_path):
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        raise RuntimeError("MuseScore nicht gefunden oder Export fehlgeschlagen")
