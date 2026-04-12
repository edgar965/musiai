"""SoundfontDialog - Soundfont-Datei auswählen."""

import logging
from PySide6.QtWidgets import QFileDialog, QWidget

logger = logging.getLogger("musiai.ui.SoundfontDialog")


class SoundfontDialog:
    """Datei-Dialog zum Auswählen einer Soundfont (.sf2)."""

    @staticmethod
    def select_soundfont(parent: QWidget) -> str | None:
        """Zeigt Dialog und gibt den gewählten Pfad zurück."""
        path, _ = QFileDialog.getOpenFileName(
            parent, "Soundfont auswählen", "media/soundfonts",
            "Soundfonts (*.sf2 *.sf3);;Alle Dateien (*)"
        )
        return path if path else None
