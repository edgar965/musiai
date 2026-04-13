"""MusiAI - Entry Point."""

import sys
import logging
from musiai.util.LoggingConfig import setup_logging

logger = setup_logging()


def _is_debugger_attached() -> bool:
    """Check if a Python debugger (debugpy/pydevd/PTVS) is attached."""
    try:
        import debugpy  # noqa: F401
        return True
    except ImportError:
        pass
    # pydevd is injected by PTVS/debugpy even without explicit import
    return "pydevd" in sys.modules


def main():
    logger.info("MusiAI startet...")

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("MusiAI")
    app.setOrganizationName("MusiAI")

    from musiai.controller.AppController import AppController
    controller = AppController()

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()

    exit_code = app.exec()

    # Clean shutdown of native audio subsystems so no background
    # threads remain.  This is critical for the PTVS/debugpy debugger
    # whose CheckAliveThread waits until has_user_threads_alive() is
    # False before sending the DAP terminated event to Visual Studio.
    _shutdown_native_audio()

    if _is_debugger_attached():
        # Let debugpy handle process exit cleanly so Visual Studio
        # receives the DAP terminated/exited events.
        logger.info("Debugger erkannt - sauberer Exit")
        sys.exit(exit_code)
    else:
        # No debugger: force-kill to avoid hangs from any remaining
        # native threads (PortMidi, FluidSynth dsound driver, SDL).
        import os
        os._exit(exit_code)


def _shutdown_native_audio():
    """Shut down all native audio subsystems that spawn background threads."""
    # 1) pygame.mixer (SDL audio thread)
    try:
        import pygame.mixer
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        logger.debug("pygame.mixer heruntergefahren")
    except Exception:
        pass

    # 2) pygame.midi (PortMidi thread)
    try:
        import pygame.midi
        pygame.midi.quit()
        logger.debug("pygame.midi heruntergefahren")
    except Exception:
        pass

    # 3) pygame top-level quit (catches anything else)
    try:
        import pygame
        pygame.quit()
        logger.debug("pygame heruntergefahren")
    except Exception:
        pass

    # 4) FluidSynth audio driver thread
    #    (already handled by controller.shutdown → SoundFontPlayer.shutdown
    #     which calls synth.delete(), but be safe)
    try:
        import fluidsynth as _fs  # noqa: F401
        # Nothing extra needed - synth.delete() in SoundFontPlayer.shutdown
        # already stops the dsound driver thread.
    except ImportError:
        pass


if __name__ == "__main__":
    main()
