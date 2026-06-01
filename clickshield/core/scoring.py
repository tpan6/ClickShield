from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum


class ThreatLevel(Enum):
    CLEAN = 0
    LOW = 1    # severity 1-3 → toast
    MEDIUM = 2  # severity 4-6 → overlay dialog
    HIGH = 3   # severity 7-10 → blocking overlay


@dataclass
class ThreatResult:
    severity: int           # 0-10 from LLM
    threat_type: str        # "phishing" | "fake_ecommerce" | "tech_support_scam" | ...
    confidence: float       # 0.0-1.0
    explanation: str        # plain English for the user
    indicators: list[str]   # bullet points shown in the overlay
    safe_to_proceed: bool = True
    raw_response: str = ""  # full LLM text for logging

    @property
    def level(self) -> ThreatLevel:
        return classify_severity(self.severity)

    @classmethod
    def clean(cls) -> "ThreatResult":
        return cls(
            severity=0,
            threat_type="clean",
            confidence=1.0,
            explanation="No threats detected.",
            indicators=[],
            safe_to_proceed=True,
        )

    @classmethod
    def error(cls, message: str) -> "ThreatResult":
        """Returned when analysis fails — treated as low severity to avoid spam."""
        return cls(
            severity=0,
            threat_type="error",
            confidence=0.0,
            explanation=f"Analysis unavailable: {message}",
            indicators=[],
            safe_to_proceed=True,
            raw_response=message,
        )


def classify_severity(severity: int) -> ThreatLevel:
    if severity <= 0:
        return ThreatLevel.CLEAN
    elif severity <= 3:
        return ThreatLevel.LOW
    elif severity <= 6:
        return ThreatLevel.MEDIUM
    else:
        return ThreatLevel.HIGH


@dataclass
class _SuppressEntry:
    expires_at: float


class ThreatSuppressor:
    """Prevents re-alerting for the same threat within a TTL window."""

    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._seen: dict[str, _SuppressEntry] = {}

    def should_suppress(self, result: ThreatResult, url: str | None) -> bool:
        if result.level == ThreatLevel.CLEAN:
            return True
        # Never suppress HIGH severity — keep warning until the user leaves the page
        if result.level == ThreatLevel.HIGH:
            return False
        key = self._make_key(result, url)
        entry = self._seen.get(key)
        if entry and time.monotonic() < entry.expires_at:
            return True
        self._seen[key] = _SuppressEntry(expires_at=time.monotonic() + self._ttl)
        self._cleanup()
        return False

    def _make_key(self, result: ThreatResult, url: str | None) -> str:
        url_hash = hashlib.md5((url or "").encode()).hexdigest()[:8]
        return f"{url_hash}:{result.threat_type}"

    def _cleanup(self) -> None:
        now = time.monotonic()
        self._seen = {k: v for k, v in self._seen.items() if now < v.expires_at}
