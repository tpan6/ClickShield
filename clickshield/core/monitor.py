from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from clickshield.config.settings import AppSettings
from clickshield.core.analyzer import AnalysisRequest, LLMAnalyzer
from clickshield.core.capture import ClipboardMonitor, ScreenCapture, URLCapture
from clickshield.core.scoring import ThreatResult, ThreatSuppressor
from clickshield.utils.keystore import load_api_key

logger = logging.getLogger(__name__)


class MonitorWorker(QThread):
    """
    Background thread that periodically captures the screen and sends it to
    the LLM for analysis. Emits signals back to the Qt main thread.
    """

    analysis_complete = pyqtSignal(object)   # ThreatResult
    scan_started = pyqtSignal()
    scan_failed = pyqtSignal(str)
    status_changed = pyqtSignal(str)         # "idle" | "scanning" | "paused" | "error"

    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings
        self._paused = False
        self._stop_flag = False
        self._immediate_scan = False

        self._screen = ScreenCapture()
        self._url_capture = URLCapture()
        self._clipboard = ClipboardMonitor()
        self._suppressor = ThreatSuppressor(ttl_seconds=300)
        self._analyzer: Optional[LLMAnalyzer] = None

    # ------------------------------------------------------------------
    # Public control

    def pause(self) -> None:
        self._paused = True
        self.status_changed.emit("paused")

    def resume(self) -> None:
        self._paused = False
        self.status_changed.emit("idle")

    def trigger_immediate_scan(self) -> None:
        self._immediate_scan = True

    def stop(self) -> None:
        self._stop_flag = True
        self.quit()

    # ------------------------------------------------------------------
    # Main loop

    def run(self) -> None:
        logger.info("MonitorWorker started.")
        self.status_changed.emit("idle")

        while not self._stop_flag:
            # Sleep in small increments so we can react to stop/pause quickly
            self._sleep_interruptible(self._settings.scan_interval_seconds)

            if self._stop_flag:
                break
            if self._paused and not self._immediate_scan:
                continue
            self._immediate_scan = False

            if not self._settings.enabled:
                continue

            self._run_scan()

        logger.info("MonitorWorker stopped.")

    def _run_scan(self) -> None:
        self.scan_started.emit()
        self.status_changed.emit("scanning")

        try:
            analyzer = self._get_analyzer()
            if analyzer is None:
                self.scan_failed.emit("No API key configured.")
                self.status_changed.emit("error")
                return

            screenshot_b64 = self._screen.capture_to_base64()
            if not screenshot_b64:
                self.scan_failed.emit("Screenshot capture failed.")
                self.status_changed.emit("idle")
                return

            url = self._url_capture.get_active_browser_url()

            clipboard_url: Optional[str] = None
            if self._settings.monitor_clipboard:
                clipboard_url = self._clipboard.get_clipboard_url()

            request = AnalysisRequest(
                screenshot_b64=screenshot_b64,
                url=url,
                clipboard_url=clipboard_url,
                timestamp=datetime.now(),
            )

            result: ThreatResult = analyzer.analyze(request)
            logger.info(
                "Scan complete: severity=%d type=%s url=%s",
                result.severity,
                result.threat_type,
                url or "N/A",
            )

            if not self._suppressor.should_suppress(result, url):
                self.analysis_complete.emit(result)

        except Exception as exc:
            logger.exception("Unexpected error during scan: %s", exc)
            self.scan_failed.emit(str(exc))
        finally:
            self.status_changed.emit("idle")

    def _get_analyzer(self) -> Optional[LLMAnalyzer]:
        if self._analyzer is not None:
            return self._analyzer
        api_key = load_api_key()
        if not api_key:
            return None
        self._analyzer = LLMAnalyzer(
            api_key=api_key,
            timeout=self._settings.request_timeout,
            provider=self._settings.model_provider,
        )
        return self._analyzer

    def _sleep_interruptible(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._stop_flag or self._immediate_scan:
                return
            time.sleep(0.25)
