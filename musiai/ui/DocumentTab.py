"""DocumentTab - Daten-Container für einen geöffneten Tab."""

import logging

logger = logging.getLogger("musiai.ui.DocumentTab")


class DocumentTab:
    """Hält den Zustand eines einzelnen Dokument-Tabs."""

    def __init__(self, piece, notation_scene, notation_view, edit_controller,
                 file_path: str | None = None, file_type: str | None = None):
        self.piece = piece
        self.notation_scene = notation_scene
        self.notation_view = notation_view
        self.edit_controller = edit_controller
        self.file_path = file_path
        self.file_type = file_type  # "midi", "musicxml", "pdf"

    @property
    def title(self) -> str:
        """Tab-Titel aus Piece-Titel oder Dateiname."""
        if self.piece and self.piece.title:
            return self.piece.title
        if self.file_path:
            import os
            return os.path.basename(self.file_path)
        return "Unbenannt"
