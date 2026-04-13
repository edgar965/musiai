"""Projekt-Datenklasse (Top-Level Container)."""

from __future__ import annotations
import json
from pathlib import Path
from musiai.model.Piece import Piece


class Project:
    """Top-Level Container für ein MusiAI-Projekt.

    Attributes:
        pieces: Liste der Musikstücke
        file_path: Pfad zur Projektdatei (None wenn ungespeichert)
    """

    def __init__(self):
        self.pieces: list[Piece] = []
        self.file_path: str | None = None

    def add_piece(self, piece: Piece) -> None:
        self.pieces.append(piece)

    @property
    def current_piece(self) -> Piece | None:
        return self.pieces[0] if self.pieces else None

    def save(self, path: str) -> None:
        """Projekt als JSON speichern."""
        data = {
            "version": "1.0",
            "pieces": [p.to_dict() for p in self.pieces],
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.file_path = path

    def load(self, path: str) -> None:
        """Projekt aus JSON laden."""
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        self.pieces = [Piece.from_dict(p) for p in data.get("pieces", [])]
        self.file_path = path
