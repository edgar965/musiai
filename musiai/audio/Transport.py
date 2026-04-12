"""Transport - Play/Pause/Stop/Seek Steuerung."""

import logging
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger("musiai.audio.Transport")


class Transport(QObject):
    """Transport-Steuerung: verwaltet Abspielposition und Timing."""

    position_changed = Signal(float)  # Aktuelle Beat-Position
    state_changed = Signal(str)       # "playing", "paused", "stopped"

    TICK_INTERVAL_MS = 20  # 50 FPS Update-Rate

    def __init__(self):
        super().__init__()
        self._state = "stopped"
        self._current_beat = 0.0
        self._tempo_bpm = 120.0
        self._end_beat = 0.0

        self._timer = QTimer()
        self._timer.setInterval(self.TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_beat(self) -> float:
        return self._current_beat

    @property
    def tempo_bpm(self) -> float:
        return self._tempo_bpm

    @tempo_bpm.setter
    def tempo_bpm(self, value: float) -> None:
        self._tempo_bpm = max(20, min(300, value))

    def set_end_beat(self, beat: float) -> None:
        self._end_beat = beat

    def play(self) -> None:
        if self._state == "playing":
            return
        self._state = "playing"
        self._timer.start()
        self.state_changed.emit("playing")
        logger.info(f"Play bei Beat {self._current_beat:.1f}, {self._tempo_bpm} BPM")

    def pause(self) -> None:
        if self._state != "playing":
            return
        self._state = "paused"
        self._timer.stop()
        self.state_changed.emit("paused")
        logger.info(f"Pause bei Beat {self._current_beat:.1f}")

    def stop(self) -> None:
        self._state = "stopped"
        self._timer.stop()
        self._current_beat = 0.0
        self.position_changed.emit(0.0)
        self.state_changed.emit("stopped")
        logger.info("Stop")

    def seek(self, beat: float) -> None:
        self._current_beat = max(0.0, beat)
        self.position_changed.emit(self._current_beat)

    def _tick(self) -> None:
        """Timer-Tick: Position um einen Zeitschritt vorwärts."""
        beats_per_ms = self._tempo_bpm / 60000.0
        self._current_beat += beats_per_ms * self.TICK_INTERVAL_MS
        self.position_changed.emit(self._current_beat)

        if self._end_beat > 0 and self._current_beat >= self._end_beat:
            self.stop()
