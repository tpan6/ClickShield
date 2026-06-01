import json

from clickshield.core.analyzer import AnalysisRequest, LLMAnalyzer
from clickshield.core.scoring import ThreatLevel


def _make_analyzer():
    return LLMAnalyzer(api_key="test-key", timeout=5)


def _make_request(url=None, clipboard_url=None, screenshot_b64="abc123"):
    return AnalysisRequest(
        screenshot_b64=screenshot_b64,
        url=url,
        clipboard_url=clipboard_url,
    )


class TestParseResponse:
    def test_valid_json_phishing(self):
        ana = _make_analyzer()
        raw = json.dumps({
            "severity": 9,
            "threat_type": "phishing",
            "confidence": 0.95,
            "explanation": "This looks like a fake bank login page.",
            "indicators": ["Wrong domain", "Fake SSL badge"],
            "safe_to_proceed": False,
        })
        result = ana._parse_response(raw)
        assert result.severity == 9
        assert result.threat_type == "phishing"
        assert result.level == ThreatLevel.HIGH
        assert result.safe_to_proceed is False
        assert len(result.indicators) == 2

    def test_valid_json_clean(self):
        ana = _make_analyzer()
        raw = json.dumps({
            "severity": 0,
            "threat_type": "clean",
            "confidence": 1.0,
            "explanation": "No threats detected.",
            "indicators": [],
            "safe_to_proceed": True,
        })
        result = ana._parse_response(raw)
        assert result.severity == 0
        assert result.level == ThreatLevel.CLEAN

    def test_json_in_markdown_fence(self):
        ana = _make_analyzer()
        raw = '```json\n{"severity": 5, "threat_type": "fake_ecommerce", "confidence": 0.7, "explanation": "Suspicious store.", "indicators": ["Too cheap"], "safe_to_proceed": true}\n```'
        result = ana._parse_response(raw)
        assert result.severity == 5
        assert result.threat_type == "fake_ecommerce"

    def test_regex_fallback(self):
        ana = _make_analyzer()
        raw = 'I detected a threat. "severity": 7, "threat_type": "tech_support_scam", "confidence": 0.8'
        result = ana._parse_response(raw)
        assert result.severity == 7
        assert result.threat_type == "tech_support_scam"

    def test_malformed_returns_error_gracefully(self):
        ana = _make_analyzer()
        raw = "This is not JSON at all."
        result = ana._parse_response(raw)
        # Should not raise — returns default zero severity
        assert result.severity == 0


class TestExtractJson:
    def test_bare_json(self):
        text = '{"severity": 3}'
        assert LLMAnalyzer._extract_json(text) is not None

    def test_fenced_json(self):
        text = '```json\n{"severity": 3}\n```'
        result = LLMAnalyzer._extract_json(text)
        assert result is not None
        assert '"severity": 3' in result

    def test_no_json(self):
        assert LLMAnalyzer._extract_json("no json here") is None


class TestBuildUserText:
    def test_with_url(self):
        ana = _make_analyzer()
        req = _make_request(url="https://evil.com", clipboard_url=None)
        text = ana._build_user_text(req)
        assert "https://evil.com" in text
        assert "CLIPBOARD URL: None" in text

    def test_without_url(self):
        ana = _make_analyzer()
        req = _make_request(url=None, clipboard_url="https://pasted.com")
        text = ana._build_user_text(req)
        assert "Unknown" in text
        assert "https://pasted.com" in text
