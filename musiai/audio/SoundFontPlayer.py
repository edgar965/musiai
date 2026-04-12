"""SoundFontPlayer - Playback über FluidSynth mit .sf2 SoundFonts."""

import logging
import os

logger = logging.getLogger("musiai.audio.SoundFontPlayer")


class SoundFontPlayer:
    """Spielt Noten über FluidSynth mit SoundFont-Dateien ab.

    Vorteile gegenüber Windows GS Wavetable:
    - Beliebige .sf2 SoundFonts ladbar (Orchester, etc.)
    - Pro Kanal verschiedene SoundFonts möglich
    - Bessere Klangqualität
    """

    def __init__(self):
        self._synth = None
        self._available = False
        self._sfont_ids: dict[str, int] = {}  # path → sfont_id
        self._init_synth()

    def _init_synth(self) -> None:
        try:
            import fluidsynth
            self._synth = fluidsynth.Synth(gain=0.8)
            self._synth.start(driver="dsound")
            self._available = True
            logger.info("FluidSynth initialisiert (dsound)")
        except Exception as e:
            logger.warning(f"FluidSynth nicht verfügbar: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def load_soundfont(self, path: str) -> int | None:
        """SoundFont laden. Gibt sfont_id zurück oder None."""
        if not self._available or not os.path.exists(path):
            return None
        if path in self._sfont_ids:
            return self._sfont_ids[path]
        try:
            sfid = self._synth.sfload(path)
            self._sfont_ids[path] = sfid
            logger.info(f"SoundFont geladen: {os.path.basename(path)} (id={sfid})")
            return sfid
        except Exception as e:
            logger.error(f"SoundFont laden fehlgeschlagen: {e}")
            return None

    def set_instrument(self, channel: int, sfont_id: int,
                       bank: int, program: int) -> None:
        """Instrument für einen Kanal setzen."""
        if not self._available:
            return
        self._synth.program_select(channel, sfont_id, bank, program)
        logger.debug(f"Kanal {channel}: SF={sfont_id} Bank={bank} Prog={program}")

    def note_on(self, channel: int, note: int, velocity: int) -> None:
        if not self._available:
            return
        self._synth.noteon(channel, note, velocity)

    def note_off(self, channel: int, note: int) -> None:
        if not self._available:
            return
        self._synth.noteoff(channel, note)

    def set_pitch_bend(self, channel: int, value: int) -> None:
        """Pitch Bend (0-16383, 8192=Mitte)."""
        if not self._available:
            return
        # FluidSynth erwartet -8192..8191
        self._synth.pitch_bend(channel, value - 8192)

    def all_notes_off(self, channel: int = -1) -> None:
        if not self._available:
            return
        if channel < 0:
            for ch in range(16):
                self._synth.cc(ch, 123, 0)
                self._synth.pitch_bend(ch, 0)
        else:
            self._synth.cc(channel, 123, 0)
            self._synth.pitch_bend(channel, 0)

    def get_loaded_soundfonts(self) -> dict[str, int]:
        """Alle geladenen SoundFonts {pfad: id}."""
        return dict(self._sfont_ids)

    def shutdown(self) -> None:
        if self._synth:
            self.all_notes_off()
            self._synth.delete()
            self._synth = None
            logger.info("FluidSynth geschlossen")
