"""AudiverisAdapter - PDF → MusicXML via Audiveris OMR."""

import logging
import os
import subprocess

logger = logging.getLogger("musiai.pdf.AudiverisAdapter")


class AudiverisAdapter:
    """Konvertiert PDF zu MusicXML mit Audiveris (Java-basierte OMR)."""

    def convert(self, pdf_path: str, output_dir: str,
                on_progress=None) -> str | None:
        """PDF → MusicXML. Gibt Pfad zur erzeugten Datei zurück."""
        if on_progress:
            on_progress("Audiveris: Starte OMR...")

        cmd = [
            "audiveris", "-batch",
            "-export",
            "-output", output_dir,
            pdf_path,
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout:
            line = line.strip()
            if line and on_progress:
                on_progress(f"Audiveris: {line[:80]}")
        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"Audiveris Fehler (Code {proc.returncode})")

        # Audiveris erzeugt .mxl mit dem Input-Dateinamen
        for f in os.listdir(output_dir):
            if f.endswith((".mxl", ".musicxml", ".xml")):
                return os.path.join(output_dir, f)
        return None
