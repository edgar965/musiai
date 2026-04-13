"""AudioPlayer - Spielt Audio-Dateien (wav/mp3) synchron zum Transport ab."""

import logging

logger = logging.getLogger("musiai.audio.AudioPlayer")


class AudioPlayer:
    """Spielt Audio-Dateien über pygame.mixer synchron zum Transport.

    Unterstützt Play/Pause/Stop/Seek und synchronisiert sich
    mit der Beat-Position des Transports.
    """

    def __init__(self):
        self._available = False
        self._tracks: dict[int, dict] = {}  # part_idx → {path, offset_sec}
        self._playing = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2)
            self._available = True
            logger.info("AudioPlayer initialisiert (pygame.mixer)")
        except Exception as e:
            logger.warning(f"AudioPlayer nicht verfügbar: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def set_track(self, part_idx: int, file_path: str,
                  offset_seconds: float = 0.0) -> None:
        """Audio-Track für eine Stimme registrieren."""
        self._tracks[part_idx] = {
            "path": file_path,
            "offset": offset_seconds,
        }

    def remove_track(self, part_idx: int) -> None:
        self._tracks.pop(part_idx, None)

    def play(self, start_seconds: float = 0.0) -> None:
        """Alle registrierten Audio-Tracks abspielen."""
        if not self._available or not self._tracks:
            return
        import pygame
        # Nur den ersten Track abspielen (pygame.mixer.music = 1 Stream)
        # Für mehrere Tracks müsste man pygame.mixer.Sound nutzen
        for info in self._tracks.values():
            try:
                pygame.mixer.music.load(info["path"])
                start = max(0.0, start_seconds - info["offset"])
                pygame.mixer.music.play(start=start)
                self._playing = True
                logger.info(f"Audio Play: {info['path']} ab {start:.1f}s")
                break  # Nur ein Track gleichzeitig via music
            except Exception as e:
                logger.error(f"Audio Play fehlgeschlagen: {e}")

    def pause(self) -> None:
        if not self._available:
            return
        import pygame
        if self._playing:
            pygame.mixer.music.pause()

    def unpause(self) -> None:
        if not self._available:
            return
        import pygame
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        if not self._available:
            return
        import pygame
        pygame.mixer.music.stop()
        self._playing = False

    def set_muted(self, muted: bool) -> None:
        if not self._available:
            return
        import pygame
        pygame.mixer.music.set_volume(0.0 if muted else 1.0)

    def shutdown(self) -> None:
        self.stop()
        self._tracks.clear()
