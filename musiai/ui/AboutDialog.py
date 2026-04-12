"""AboutDialog - Info-Dialog mit Versionsnummer."""

import logging
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

logger = logging.getLogger("musiai.ui.AboutDialog")

VERSION = "0.12"
VERSION_DATE = "2026-04-12"


class AboutDialog(QDialog):
    """Info-Dialog: zeigt Version, Titel und Beschreibung."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Über MusiAI")
        self.setFixedSize(360, 220)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("MusiAI")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Music Expression Editor")
        subtitle.setFont(QFont("Arial", 11))
        subtitle.setStyleSheet("color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        version = QLabel(f"Version {VERSION}  ({VERSION_DATE})")
        version.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        version.setStyleSheet("color: #2d5aa0; margin-top: 10px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        desc = QLabel("Farbige Notation mit Mikrotönen,\nExpression-Control und MIDI-Keyboard.")
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #888; margin-top: 8px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)
