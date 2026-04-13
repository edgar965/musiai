"""PdfEngineConfig - Erkennung und Konfiguration von PDF-Engines."""

import logging
import os
import subprocess

logger = logging.getLogger("musiai.pdf.PdfEngineConfig")


class PdfEngineConfig:
    """Erkennt und konfiguriert PDF-Import/Export-Engines."""

    IMPORT_ENGINES = {
        "audiveris": {
            "name": "Audiveris (Java OMR)",
            "desc": "Open Source OMR. Beste Qualität für gescannte\n"
                    "Partituren. Benötigt Java 17+.",
        },
        "oemer": {
            "name": "oemer (Deep Learning)",
            "desc": "Python-basierte OMR mit neuronalem Netz.\n"
                    "Gut für einfache Partituren.",
        },
        "pdf2musicxml": {
            "name": "pdf2musicxml (Audio-Pipeline)",
            "desc": "Konvertiert PDF → Bild → Audio → Noten.\n"
                    "Experimentell, nutzt basic-pitch.",
        },
    }

    EXPORT_ENGINES = {
        "lilypond": {
            "name": "LilyPond",
            "desc": "Professioneller Notensatz.\n"
                    "Höchste Qualität, Open Source.",
        },
        "musescore": {
            "name": "MuseScore CLI",
            "desc": "MuseScore Batch-Export.\n"
                    "Gute Qualität, einfache Bedienung.",
        },
        "reportlab": {
            "name": "ReportLab (intern)",
            "desc": "Einfacher PDF-Export direkt aus Python.\n"
                    "Keine externe Software nötig.",
        },
    }

    @staticmethod
    def detect_import_engines() -> dict[str, bool]:
        """Prüft welche Import-Engines verfügbar sind."""
        results = {}

        # Audiveris: Java + audiveris auf PATH
        results["audiveris"] = PdfEngineConfig._check_command(
            ["audiveris", "-help"]
        ) or PdfEngineConfig._check_command(["java", "-version"])

        # oemer: Python-Paket
        try:
            __import__("oemer")
            results["oemer"] = True
        except ImportError:
            results["oemer"] = False

        # pdf2musicxml: basic-pitch verfügbar
        results["pdf2musicxml"] = os.path.exists(
            os.path.join("python310ENV", "python.exe")
        )

        return results

    @staticmethod
    def detect_export_engines() -> dict[str, bool]:
        """Prüft welche Export-Engines verfügbar sind."""
        results = {}

        # LilyPond
        results["lilypond"] = PdfEngineConfig._check_command(
            ["lilypond", "--version"]
        )

        # MuseScore
        results["musescore"] = (
            PdfEngineConfig._check_command(["mscore", "--version"]) or
            PdfEngineConfig._check_command(["musescore", "--version"]) or
            PdfEngineConfig._check_command(["MuseScore4", "--version"])
        )

        # ReportLab
        try:
            __import__("reportlab")
            results["reportlab"] = True
        except ImportError:
            results["reportlab"] = False

        return results

    @staticmethod
    def _check_command(cmd: list[str]) -> bool:
        """Prüft ob ein Kommando ausführbar ist."""
        try:
            subprocess.run(
                cmd, capture_output=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
