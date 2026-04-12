"""MidiDeviceDialog - MIDI-Gerät auswählen."""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QPushButton, QLabel, QHBoxLayout,
)
from musiai.midi.MidiKeyboard import MidiKeyboard

logger = logging.getLogger("musiai.ui.MidiDeviceDialog")


class MidiDeviceDialog(QDialog):
    """Dialog zum Auswählen und Verbinden eines MIDI-Keyboards."""

    def __init__(self, keyboard: MidiKeyboard, parent=None):
        super().__init__(parent)
        self.keyboard = keyboard
        self.setWindowTitle("MIDI-Gerät auswählen")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._refresh_ports()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Verfügbare MIDI-Geräte:"))

        self._port_list = QListWidget()
        layout.addWidget(self._port_list)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self._refresh_ports)
        connect_btn = QPushButton("Verbinden")
        connect_btn.clicked.connect(self._connect)
        disconnect_btn = QPushButton("Trennen")
        disconnect_btn.clicked.connect(self._disconnect)
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(connect_btn)
        btn_layout.addWidget(disconnect_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    def _refresh_ports(self) -> None:
        self._port_list.clear()
        ports = MidiKeyboard.list_ports()
        if ports:
            self._port_list.addItems(ports)
            self._status_label.setText(f"{len(ports)} Geräte gefunden")
        else:
            self._status_label.setText("Keine MIDI-Geräte gefunden")

    def _connect(self) -> None:
        item = self._port_list.currentItem()
        if not item:
            self._status_label.setText("Bitte Gerät auswählen")
            return
        port_name = item.text()
        if self.keyboard.connect(port_name):
            self._status_label.setText(f"Verbunden: {port_name}")
        else:
            self._status_label.setText(f"Verbindung fehlgeschlagen: {port_name}")

    def _disconnect(self) -> None:
        self.keyboard.disconnect()
        self._status_label.setText("Getrennt")
