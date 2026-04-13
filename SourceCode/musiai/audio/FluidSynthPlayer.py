"""FluidSynthPlayer - MIDI Playback über pygame.midi (Windows GS Wavetable Synth)."""

import logging

logger = logging.getLogger("musiai.audio.FluidSynthPlayer")


class FluidSynthPlayer:
    """Spielt Noten über den Windows MIDI Synthesizer ab.

    Nutzt pygame.midi als Backend - funktioniert auf Windows ohne
    zusätzliche Soundfonts oder Treiber.
    """

    def __init__(self):
        self._midi_out = None
        self._available = False
        self._init_midi()

    def _init_midi(self) -> None:
        try:
            import pygame.midi
            pygame.midi.init()
            output_id = pygame.midi.get_default_output_id()
            if output_id < 0:
                logger.warning("Kein MIDI-Output-Device gefunden")
                return
            self._midi_out = pygame.midi.Output(output_id)
            device_info = pygame.midi.get_device_info(output_id)
            device_name = device_info[1].decode() if device_info else "Unknown"
            self._available = True
            logger.info(f"MIDI Output initialisiert: {device_name}")
        except Exception as e:
            logger.warning(f"MIDI Output nicht verfügbar: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def load_soundfont(self, path: str) -> bool:
        """Nicht nötig bei Windows MIDI - ignoriert."""
        logger.info(f"Soundfont ignoriert (Windows MIDI): {path}")
        return True

    def set_instrument(self, channel: int, bank: int, program: int) -> None:
        """Instrument/Sound für einen Kanal setzen."""
        if not self._available:
            return
        self._midi_out.set_instrument(program, channel)
        logger.debug(f"Instrument Kanal {channel}: Program {program}")

    def note_on(self, channel: int, note: int, velocity: int) -> None:
        if not self._available:
            return
        self._midi_out.note_on(note, velocity, channel)

    def note_off(self, channel: int, note: int) -> None:
        if not self._available:
            return
        self._midi_out.note_off(note, 0, channel)

    def set_pitch_bend(self, channel: int, value: int) -> None:
        """Pitch Bend setzen (0-16383, 8192=Mitte).

        pygame.midi hat kein direktes pitch_bend - wir nutzen write_short.
        """
        if not self._available:
            return
        # MIDI Pitch Bend: Status=0xE0+channel, LSB, MSB
        lsb = value & 0x7F
        msb = (value >> 7) & 0x7F
        self._midi_out.write_short(0xE0 + channel, lsb, msb)

    def all_notes_off(self, channel: int = -1) -> None:
        """Alle Noten stoppen."""
        if not self._available:
            return
        if channel < 0:
            for ch in range(16):
                # CC 123 = All Notes Off
                self._midi_out.write_short(0xB0 + ch, 123, 0)
                # Pitch Bend Reset
                self._midi_out.write_short(0xE0 + ch, 0, 64)
        else:
            self._midi_out.write_short(0xB0 + channel, 123, 0)
            self._midi_out.write_short(0xE0 + channel, 0, 64)

    def shutdown(self) -> None:
        if self._midi_out:
            self.all_notes_off()
            self._midi_out.close()
            self._midi_out = None
            logger.info("MIDI Output geschlossen")
        try:
            import pygame.midi
            pygame.midi.quit()
        except Exception:
            pass
