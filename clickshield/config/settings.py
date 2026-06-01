from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from clickshield.config import defaults

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path.home() / ".clickshield"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


@dataclass
class AppSettings:
    # LLM
    model_provider: str = defaults.MODEL_PROVIDER
    request_timeout: int = defaults.REQUEST_TIMEOUT

    # Monitoring
    scan_interval_seconds: int = defaults.SCAN_INTERVAL_SECONDS
    enabled: bool = True
    monitor_clipboard: bool = defaults.MONITOR_CLIPBOARD

    # Thresholds
    low_threshold: int = defaults.LOW_THRESHOLD
    medium_threshold: int = defaults.MEDIUM_THRESHOLD
    high_threshold: int = defaults.HIGH_THRESHOLD

    # UI
    overlay_opacity: float = defaults.OVERLAY_OPACITY
    sound_enabled: bool = defaults.SOUND_ENABLED

    # System
    autostart: bool = defaults.AUTOSTART

    def save(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        logger.debug("Settings saved to %s", _CONFIG_FILE)

    @classmethod
    def load(cls) -> "AppSettings":
        if not _CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            # Only apply known fields so we don't crash on old/extra keys
            valid = {f for f in cls.__dataclass_fields__}
            filtered = {k: v for k, v in data.items() if k in valid}
            return cls(**filtered)
        except Exception as exc:
            logger.warning("Could not load settings, using defaults: %s", exc)
            return cls()

    @property
    def config_dir(self) -> Path:
        return _CONFIG_DIR

    @property
    def log_file(self) -> Path:
        return _CONFIG_DIR / "clickshield.log"
