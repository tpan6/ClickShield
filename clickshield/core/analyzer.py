from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openai import OpenAI, OpenAIError

from clickshield.core.scoring import ThreatResult

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "resources" / "prompts" / "scam_analysis.txt"
_SYSTEM_PROMPT: str | None = None
_HTML_CHAR_LIMIT = 3000  # max page text chars sent to the model


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _SYSTEM_PROMPT


@dataclass
class AnalysisRequest:
    screenshot_b64: str               # Base64-encoded JPEG
    url: str | None                   # Active browser URL
    clipboard_url: str | None         # Recently pasted URL from clipboard
    browser_name: str | None = None   # Detected browser (e.g. "Google Chrome")
    page_html: str | None = None      # Stripped text content of the active page
    timestamp: datetime = field(default_factory=datetime.now)


class LLMAnalyzer:
    """Sends screenshots (+ page HTML) to GPT-5.4-nano via the OpenAI API."""

    OPENAI_BASE = "https://api.openai.com/v1"
    OPENROUTER_BASE = "https://openrouter.ai/api/v1"
    MODEL_OPENAI = "gpt-5.4-nano"
    MODEL_OPENROUTER = "openai/gpt-5.4-nano"

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        provider: str = "openai",
    ):
        self._timeout = timeout
        self._provider = provider

        if provider == "openrouter":
            base_url = self.OPENROUTER_BASE
            model = self.MODEL_OPENROUTER
        else:
            base_url = self.OPENAI_BASE
            model = self.MODEL_OPENAI

        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def analyze(self, request: AnalysisRequest) -> ThreatResult:
        """Synchronous — call from a background thread, never the Qt main thread."""
        try:
            user_text = self._build_user_text(request)
            content: list[dict] = [{"type": "text", "text": user_text}]

            if request.screenshot_b64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{request.screenshot_b64}",
                        "detail": "low",   # low detail = faster + cheaper for classification
                    },
                })

            messages = [
                {"role": "system", "content": _load_system_prompt()},
                {"role": "user", "content": content},
            ]

            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.1,
                max_tokens=512,
            )

            raw = response.choices[0].message.content or ""
            logger.debug("LLM raw response: %s", raw[:500])
            return self._parse_response(raw)

        except OpenAIError as exc:
            logger.warning("LLM API error: %s", exc)
            return ThreatResult.error(str(exc))
        except Exception as exc:
            logger.warning("Unexpected analyzer error: %s", exc)
            return ThreatResult.error(str(exc))

    def is_available(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------

    def _build_user_text(self, request: AnalysisRequest) -> str:
        lines = []
        lines.append(f"ACTIVE URL: {request.url or 'Unknown (no browser active)'}")
        lines.append(f"BROWSER: {request.browser_name or 'Unknown'}")
        lines.append(f"CLIPBOARD URL: {request.clipboard_url or 'None'}")
        lines.append(f"TIMESTAMP: {request.timestamp.isoformat()}")

        if request.page_html:
            lines.append("")
            lines.append("PAGE TEXT CONTENT (stripped HTML):")
            lines.append(request.page_html[:_HTML_CHAR_LIMIT])

        lines.append("")
        lines.append("Analyze the screenshot and page content for scam or phishing threats.")
        return "\n".join(lines)

    def _parse_response(self, raw: str) -> ThreatResult:
        json_str = self._extract_json(raw)
        if json_str:
            try:
                data = json.loads(json_str)
                return ThreatResult(
                    severity=int(data.get("severity", 0)),
                    threat_type=str(data.get("threat_type", "unknown")),
                    confidence=float(data.get("confidence", 0.5)),
                    explanation=str(data.get("explanation", "")),
                    indicators=list(data.get("indicators", [])),
                    safe_to_proceed=bool(data.get("safe_to_proceed", True)),
                    raw_response=raw,
                )
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("JSON parse failed: %s. Falling back to regex.", exc)

        severity = self._regex_int(raw, r'"severity"\s*:\s*(\d+)', default=0)
        confidence = self._regex_float(raw, r'"confidence"\s*:\s*([\d.]+)', default=0.5)
        threat_type = self._regex_str(raw, r'"threat_type"\s*:\s*"([^"]+)"', default="unknown")
        explanation = self._regex_str(raw, r'"explanation"\s*:\s*"([^"]+)"', default="Unable to parse analysis.")
        return ThreatResult(
            severity=severity,
            threat_type=threat_type,
            confidence=confidence,
            explanation=explanation,
            indicators=[],
            safe_to_proceed=(severity < 7),
            raw_response=raw,
        )

    @staticmethod
    def _extract_json(text: str) -> str | None:
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        m = re.search(r"(\{[^{}]*\})", text, re.DOTALL)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _regex_int(text: str, pattern: str, default: int) -> int:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else default

    @staticmethod
    def _regex_float(text: str, pattern: str, default: float) -> float:
        m = re.search(pattern, text)
        return float(m.group(1)) if m else default

    @staticmethod
    def _regex_str(text: str, pattern: str, default: str) -> str:
        m = re.search(pattern, text)
        return m.group(1) if m else default
