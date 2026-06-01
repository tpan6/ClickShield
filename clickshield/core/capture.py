from __future__ import annotations

import base64
import hashlib
import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ScreenCapture
# ---------------------------------------------------------------------------

class ScreenCapture:
    """Captures the primary monitor and returns a JPEG base64 string."""

    MAX_WIDTH = 1280
    MAX_HEIGHT = 720
    JPEG_QUALITY = 75

    def capture_to_base64(self) -> str:
        try:
            import mss
            import mss.tools
            from PIL import Image

            with mss.mss() as sct:
                monitor = sct.monitors[1]  # primary monitor
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

            img.thumbnail((self.MAX_WIDTH, self.MAX_HEIGHT), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self.JPEG_QUALITY)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

        except Exception as exc:
            logger.warning("Screenshot capture failed: %s", exc)
            return ""


# ---------------------------------------------------------------------------
# URLCapture — layered approach for reading the active browser URL
# ---------------------------------------------------------------------------

_BROWSER_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "firefox.exe",
    "opera.exe",
    "vivaldi.exe",
    "chromium.exe",
}


class URLCapture:
    """Reads the active browser URL using Windows UI Automation."""

    UIA_TIMEOUT = 0.5  # seconds

    def get_active_browser_url(self) -> Optional[str]:
        try:
            import psutil
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc_name = psutil.Process(pid).name().lower()
            except psutil.NoSuchProcess:
                return None

            if proc_name not in _BROWSER_PROCESSES:
                return None

            if proc_name == "firefox.exe":
                url = self._get_firefox_url(hwnd)
            else:
                url = self._get_chromium_url(hwnd)

            if url and self._looks_like_url(url):
                return url

            # Fallback: try to extract URL from window title
            return self._get_url_from_title(hwnd)

        except Exception as exc:
            logger.debug("URL capture failed: %s", exc)
            return None

    def _get_chromium_url(self, hwnd: int) -> Optional[str]:
        try:
            import uiautomation as auto
            ctrl = auto.ControlFromHandle(hwnd)

            # Primary: by AutomationId
            addr = ctrl.EditControl(AutomationId="omnibox")
            if addr.Exists(0, 0):
                val = addr.GetValuePattern().Value
                if val:
                    return val

            # Secondary: by class name
            addr = ctrl.EditControl(ClassName="OmniboxViewViews")
            if addr.Exists(0, 0):
                val = addr.GetValuePattern().Value
                if val:
                    return val

        except Exception as exc:
            logger.debug("Chromium UIA failed: %s", exc)
        return None

    def _get_firefox_url(self, hwnd: int) -> Optional[str]:
        try:
            import uiautomation as auto
            ctrl = auto.ControlFromHandle(hwnd)

            # Firefox address bar label varies by version
            for name in (
                "Search with Google or enter address",
                "Address and search bar",
                "Enter Search or Address",
            ):
                addr = ctrl.EditControl(Name=name)
                if addr.Exists(0, 0):
                    val = addr.GetValuePattern().Value
                    if val:
                        return val

            # Try toolbar path
            toolbar = ctrl.ToolBarControl(Name="Navigation Toolbar")
            if toolbar.Exists(0, 0):
                addr = toolbar.EditControl(foundIndex=1)
                if addr.Exists(0, 0):
                    val = addr.GetValuePattern().Value
                    if val:
                        return val

        except Exception as exc:
            logger.debug("Firefox UIA failed: %s", exc)
        return None

    @staticmethod
    def _get_url_from_title(hwnd: int) -> Optional[str]:
        try:
            import win32gui
            title = win32gui.GetWindowText(hwnd)
            m = re.search(r"https?://[^\s\"'<>]+", title)
            return m.group(0) if m else None
        except Exception:
            return None

    @staticmethod
    def _looks_like_url(text: str) -> bool:
        return bool(re.match(r"https?://", text))


# ---------------------------------------------------------------------------
# ClipboardMonitor — detects when a URL is pasted into the clipboard
# ---------------------------------------------------------------------------

class ClipboardMonitor:
    """Tracks clipboard changes and returns a URL if one was just pasted."""

    def __init__(self):
        self._last_hash: str = ""

    def get_clipboard_url(self) -> Optional[str]:
        text = self._read_clipboard()
        if text is None:
            return None

        h = hashlib.md5(text.encode()).hexdigest()
        if h == self._last_hash:
            return None

        self._last_hash = h
        text = text.strip()
        if re.match(r"https?://", text) and len(text) < 2048:
            return text
        return None

    @staticmethod
    def _read_clipboard() -> Optional[str]:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        return None
