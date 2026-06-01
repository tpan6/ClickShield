import time
import pytest
from clickshield.core.scoring import (
    ThreatLevel,
    ThreatResult,
    ThreatSuppressor,
    classify_severity,
)


def test_classify_severity():
    assert classify_severity(0) == ThreatLevel.CLEAN
    assert classify_severity(-1) == ThreatLevel.CLEAN
    assert classify_severity(1) == ThreatLevel.LOW
    assert classify_severity(3) == ThreatLevel.LOW
    assert classify_severity(4) == ThreatLevel.MEDIUM
    assert classify_severity(6) == ThreatLevel.MEDIUM
    assert classify_severity(7) == ThreatLevel.HIGH
    assert classify_severity(10) == ThreatLevel.HIGH


def test_threat_result_level():
    r = ThreatResult(severity=8, threat_type="phishing", confidence=0.9,
                     explanation="test", indicators=[])
    assert r.level == ThreatLevel.HIGH


def test_threat_result_clean_factory():
    r = ThreatResult.clean()
    assert r.severity == 0
    assert r.level == ThreatLevel.CLEAN
    assert r.safe_to_proceed is True


def test_threat_result_error_factory():
    r = ThreatResult.error("timeout")
    assert r.severity == 0
    assert r.threat_type == "error"
    assert r.safe_to_proceed is True


class TestThreatSuppressor:
    def _make_result(self, severity=7, threat_type="phishing"):
        return ThreatResult(
            severity=severity,
            threat_type=threat_type,
            confidence=0.9,
            explanation="test",
            indicators=[],
        )

    def test_clean_always_suppressed(self):
        sup = ThreatSuppressor()
        r = ThreatResult.clean()
        assert sup.should_suppress(r, "https://example.com") is True

    def test_first_occurrence_not_suppressed(self):
        sup = ThreatSuppressor()
        r = self._make_result()
        assert sup.should_suppress(r, "https://evil.com") is False

    def test_second_occurrence_suppressed(self):
        sup = ThreatSuppressor()
        r = self._make_result()
        sup.should_suppress(r, "https://evil.com")
        assert sup.should_suppress(r, "https://evil.com") is True

    def test_different_url_not_suppressed(self):
        sup = ThreatSuppressor()
        r = self._make_result()
        sup.should_suppress(r, "https://evil.com")
        assert sup.should_suppress(r, "https://other-evil.com") is False

    def test_ttl_expiry(self):
        sup = ThreatSuppressor(ttl_seconds=1)
        r = self._make_result()
        sup.should_suppress(r, "https://evil.com")
        time.sleep(1.1)
        assert sup.should_suppress(r, "https://evil.com") is False
