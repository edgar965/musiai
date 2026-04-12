"""StatusBar - Zeigt Position, MIDI-Status und Meldungen."""

import logging
from PySide6.QtWidgets import QStatusBar, QLabel

logger = logging.getLogger("musiai.ui.StatusBar")


class StatusBar(QStatusBar):
    """Statusleiste mit Position, MIDI-Status und Meldungen."""

    def __init__(self):
        super().__init__()
        self._position_label = QLabel("Takt 1 | Beat 1.0")
        self._midi_label = QLabel("MIDI: ---")
        self._message_label = QLabel("")

        self.addWidget(self._position_label)
        self.addWidget(self._midi_label)
        self.addPermanentWidget(self._message_label)
        logger.debug("StatusBar erstellt")

    def set_position(self, measure: int, beat: float) -> None:
        self._position_label.setText(f"Takt {measure} | Beat {beat:.1f}")

    def set_midi_status(self, connected: bool, port: str = "") -> None:
        if connected:
            self._midi_label.setText(f"MIDI: {port}")
            self._midi_label.setStyleSheet("color: #5bb974;")
        else:
            self._midi_label.setText("MIDI: ---")
            self._midi_label.setStyleSheet("color: #888;")

    def set_message(self, text: str) -> None:
        self._message_label.setText(text)
        logger.debug(f"Status: {text}")
