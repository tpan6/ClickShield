from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from clickshield.core.scoring import ThreatResult

logger = logging.getLogger(__name__)

_HISTORY_DIR = Path.home() / ".clickshield"
_HISTORY_FILE = _HISTORY_DIR / "history.json"
_SCREENSHOTS_DIR = _HISTORY_DIR / "screenshots"
_MAX_RECORDS = 200


@dataclass
class ScanRecord:
    """One complete scan event — stored to disk and shown in the dashboard."""

    id: str                           # ISO timestamp used as unique ID
    timestamp: str                    # ISO format
    url: Optional[str]
    browser_name: Optional[str]
    severity: int
    threat_type: str
    confidence: float
    explanation: str
    indicators: list[str]
    safe_to_proceed: bool
    raw_response: str
    screenshot_path: Optional[str]    # Relative path inside ~/.clickshield/screenshots/

    @classmethod
    def from_result(
        cls,
        result: ThreatResult,
        url: Optional[str],
        browser_name: Optional[str],
        screenshot_b64: str,
        ts: Optional[datetime] = None,
    ) -> "ScanRecord":
        ts = ts or datetime.now()
        record_id = ts.strftime("%Y%m%d_%H%M%S_%f")

        screenshot_path: Optional[str] = None
        if screenshot_b64:
            screenshot_path = _save_screenshot(record_id, screenshot_b64)

        return cls(
            id=record_id,
            timestamp=ts.isoformat(),
            url=url,
            browser_name=browser_name,
            severity=result.severity,
            threat_type=result.threat_type,
            confidence=result.confidence,
            explanation=result.explanation,
            indicators=result.indicators,
            safe_to_proceed=result.safe_to_proceed,
            raw_response=result.raw_response,
            screenshot_path=screenshot_path,
        )

    @property
    def screenshot_full_path(self) -> Optional[Path]:
        if self.screenshot_path:
            return _SCREENSHOTS_DIR / self.screenshot_path
        return None

    @property
    def datetime_obj(self) -> datetime:
        try:
            return datetime.fromisoformat(self.timestamp)
        except ValueError:
            return datetime.now()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ScanRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _save_screenshot(record_id: str, b64: str) -> Optional[str]:
    """Saves base64 JPEG to disk. Returns filename (not full path)."""
    try:
        import base64
        _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{record_id}.jpg"
        (_SCREENSHOTS_DIR / filename).write_bytes(base64.b64decode(b64))
        return filename
    except Exception as exc:
        logger.warning("Could not save screenshot: %s", exc)
        return None


class HistoryStore:
    """
    Persists scan records to ~/.clickshield/history.json.
    Keeps the most recent _MAX_RECORDS entries; older ones are dropped.
    """

    def __init__(self):
        self._records: list[ScanRecord] = []
        self._load()

    # ------------------------------------------------------------------
    # Public

    def add(self, record: ScanRecord) -> None:
        self._records.insert(0, record)  # newest first
        if len(self._records) > _MAX_RECORDS:
            dropped = self._records[_MAX_RECORDS:]
            self._records = self._records[:_MAX_RECORDS]
            self._cleanup_screenshots(dropped)
        self._save()

    def all(self) -> list[ScanRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._cleanup_screenshots(self._records)
        self._records = []
        self._save()

    @property
    def total_scans(self) -> int:
        return len(self._records)

    @property
    def threats_today(self) -> int:
        today = datetime.now().date()
        return sum(
            1 for r in self._records
            if r.severity > 0 and r.datetime_obj.date() == today
        )

    # ------------------------------------------------------------------
    # Persistence

    def _load(self) -> None:
        if not _HISTORY_FILE.exists():
            return
        try:
            data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
            self._records = [ScanRecord.from_dict(d) for d in data]
            logger.debug("Loaded %d history records.", len(self._records))
        except Exception as exc:
            logger.warning("Could not load history: %s", exc)

    def _save(self) -> None:
        try:
            _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            _HISTORY_FILE.write_text(
                json.dumps([r.to_dict() for r in self._records], indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not save history: %s", exc)

    def _cleanup_screenshots(self, records: list[ScanRecord]) -> None:
        for r in records:
            p = r.screenshot_full_path
            if p and p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
