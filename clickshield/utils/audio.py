from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_SOUND_PATH = Path(__file__).parent.parent / "resources" / "sounds" / "alert_high.wav"


def play_alert(enabled: bool = True) -> None:
    """Play the alert sound in a background thread. No-op if sound is disabled."""
    if not enabled:
        return
    threading.Thread(target=_play, daemon=True).start()


def _play() -> None:
    try:
        import winsound
        if _SOUND_PATH.exists():
            winsound.PlaySound(str(_SOUND_PATH), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        else:
            # Fallback to system asterisk sound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception as exc:
        logger.debug("Audio playback failed: %s", exc)
