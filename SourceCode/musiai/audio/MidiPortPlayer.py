"""MidiPortPlayer - Sendet MIDI an beliebigen Output-Port (z.B. HALion via loopMIDI)."""

import logging

logger = logging.getLogger("musiai.audio.MidiPortPlayer")


class MidiPortPlayer:
    """Sendet MIDI-Daten an einen wählbaren Output-Port.

    Nutzt pygame.midi - erkennt auch virtuelle Ports wie loopMIDI.
    So kann man externe Synths (HALion, Kontakt, etc.) ansteuern.
    """

    def __init__(self):
        self._midi_out = None
        self._available = False
        self._port_id = -1
        self._port_name = ""

    @staticmethod
    def list_output_ports() -> list[tuple[int, str]]:
        """Alle verfügbaren MIDI-Output-Ports auflisten."""
        ports = []
        try:
            import pygame.midi
            if not pygame.midi.get_init():
                pygame.midi.init()
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[3]:  # is_output
                    name = info[1].decode()
                    ports.append((i, name))
        except Exception as e:
            logger.warning(f"MIDI Ports auflisten fehlgeschlagen: {e}")
        return ports

    def connect(self, port_id: int) -> bool:
        """Mit einem bestimmten Output-Port verbinden."""
        self.disconnect()
        try:
            import pygame.midi
            if not pygame.midi.get_init():
                pygame.midi.init()
            self._midi_out = pygame.midi.Output(port_id)
            info = pygame.midi.get_device_info(port_id)
            self._port_name = info[1].decode() if info else f"Port {port_id}"
            self._port_id = port_id
            self._available = True
            logger.info(f"MIDI Output verbunden: {self._port_name}")
            return True
        except Exception as e:
            logger.error(f"MIDI Port {port_id} verbinden fehlgeschlagen: {e}")
            self._available = False
            return False

    def disconnect(self) -> None:
        if self._midi_out:
            self.all_notes_off()
            self._midi_out.close()
            self._midi_out = None
            self._available = False
            logger.info(f"MIDI Output getrennt: {self._port_name}")

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def port_name(self) -> str:
        return self._port_name

    def set_instrument(self, channel: int, bank: int, program: int) -> None:
        if not self._available:
            return
        self._midi_out.set_instrument(program, channel)

    def note_on(self, channel: int, note: int, velocity: int) -> None:
        if not self._available:
            return
        self._midi_out.note_on(note, velocity, channel)

    def note_off(self, channel: int, note: int) -> None:
        if not self._available:
            return
        self._midi_out.note_off(note, 0, channel)

    def set_pitch_bend(self, channel: int, value: int) -> None:
        if not self._available:
            return
        lsb = value & 0x7F
        msb = (value >> 7) & 0x7F
        self._midi_out.write_short(0xE0 + channel, lsb, msb)

    def all_notes_off(self, channel: int = -1) -> None:
        if not self._available:
            return
        if channel < 0:
            for ch in range(16):
                self._midi_out.write_short(0xB0 + ch, 123, 0)
                self._midi_out.write_short(0xE0 + ch, 0, 64)
        else:
            self._midi_out.write_short(0xB0 + channel, 123, 0)
            self._midi_out.write_short(0xE0 + channel, 0, 64)

    def shutdown(self) -> None:
        self.disconnect()
