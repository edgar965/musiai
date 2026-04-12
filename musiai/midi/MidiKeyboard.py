"""MidiKeyboard - Live MIDI Input vom Hardware-Keyboard."""

import logging
import threading
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("musiai.midi.MidiKeyboard")


class MidiKeyboard(QObject):
    """Liest MIDI-Nachrichten vom Hardware-Keyboard via mido/rtmidi."""

    note_on = Signal(int, int)     # note, velocity
    note_off = Signal(int)         # note
    control_change = Signal(int, int)  # cc_number, value
    pitch_bend = Signal(int)       # value (0-16383)
    connected = Signal(str)        # port_name
    disconnected = Signal()

    def __init__(self):
        super().__init__()
        self._port = None
        self._port_name: str | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def is_connected(self) -> bool:
        return self._port is not None

    @staticmethod
    def list_ports() -> list[str]:
        """Verfügbare MIDI-Input-Ports auflisten."""
        try:
            import mido
            ports = mido.get_input_names()
            logger.debug(f"MIDI Ports: {ports}")
            return ports
        except Exception as e:
            logger.error(f"MIDI Ports auflisten fehlgeschlagen: {e}")
            return []

    def connect(self, port_name: str) -> bool:
        """Mit einem MIDI-Port verbinden."""
        try:
            import mido
            self.disconnect()
            self._port = mido.open_input(port_name, callback=self._on_message)
            self._port_name = port_name
            self.connected.emit(port_name)
            logger.info(f"MIDI verbunden: {port_name}")
            return True
        except Exception as e:
            logger.error(f"MIDI Verbindung fehlgeschlagen: {e}")
            return False

    def disconnect(self) -> None:
        """Verbindung trennen."""
        if self._port:
            self._port.close()
            self._port = None
            self._port_name = None
            self.disconnected.emit()
            logger.info("MIDI getrennt")

    def _on_message(self, message) -> None:
        """Callback für eingehende MIDI-Nachrichten."""
        try:
            if message.type == "note_on" and message.velocity > 0:
                self.note_on.emit(message.note, message.velocity)
            elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                self.note_off.emit(message.note)
            elif message.type == "control_change":
                self.control_change.emit(message.control, message.value)
            elif message.type == "pitchwheel":
                # mido: -8192 bis 8191 → wir normalisieren auf 0-16383
                self.pitch_bend.emit(message.pitch + 8192)
        except Exception as e:
            logger.error(f"MIDI Message Fehler: {e}")

    def shutdown(self) -> None:
        self.disconnect()
