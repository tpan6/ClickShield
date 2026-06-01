from __future__ import annotations

import base64
import hashlib
import html as html_module
import io
import logging
import re
from html.parser import HTMLParser
from typing import NamedTuple, Optional

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
# BrowserInfo — result type for URLCapture
# ---------------------------------------------------------------------------

_BROWSER_PROCESSES: dict[str, str] = {
    "chrome.exe":   "Google Chrome",
    "msedge.exe":   "Microsoft Edge",
    "brave.exe":    "Brave",
    "firefox.exe":  "Firefox",
    "opera.exe":    "Opera",
    "vivaldi.exe":  "Vivaldi",
    "chromium.exe": "Chromium",
}


class BrowserInfo(NamedTuple):
    url: Optional[str]
    browser_name: Optional[str]   # e.g. "Google Chrome"
    process_name: Optional[str]   # e.g. "chrome.exe"


# ---------------------------------------------------------------------------
# URLCapture — layered approach for reading the active browser URL
# ---------------------------------------------------------------------------


class URLCapture:
    """Reads the active browser URL + name using Windows UI Automation."""

    def get_browser_info(self) -> BrowserInfo:
        """Returns (url, browser_name, process_name) for the foreground window."""
        try:
            import psutil
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return BrowserInfo(None, None, None)

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc_name = psutil.Process(pid).name().lower()
            except psutil.NoSuchProcess:
                return BrowserInfo(None, None, None)

            if proc_name not in _BROWSER_PROCESSES:
                return BrowserInfo(None, None, None)

            browser_name = _BROWSER_PROCESSES[proc_name]

            if proc_name == "firefox.exe":
                url = self._get_firefox_url(hwnd)
            else:
                url = self._get_chromium_url(hwnd)

            if url and self._looks_like_url(url):
                return BrowserInfo(url, browser_name, proc_name)

            # Fallback: title regex
            url = self._get_url_from_title(hwnd)
            return BrowserInfo(url, browser_name, proc_name)

        except Exception as exc:
            logger.debug("URL capture failed: %s", exc)
            return BrowserInfo(None, None, None)

    def _get_chromium_url(self, hwnd: int) -> Optional[str]:
        try:
            import uiautomation as auto
            ctrl = auto.ControlFromHandle(hwnd)

            addr = ctrl.EditControl(AutomationId="omnibox")
            if addr.Exists(0, 0):
                val = addr.GetValuePattern().Value
                if val:
                    return val

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
# HTMLCapture — fetches and strips the active page's text content
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Minimal HTML → plain text extractor using stdlib only."""

    _SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []
        self.title: str = ""
        self._in_title = False
        self.forms_with_password: int = 0
        self._current_input_type: str = ""

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "input":
            attr_dict = dict(attrs)
            t = attr_dict.get("type", "").lower()
            if t == "password":
                self.forms_with_password += 1

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        else:
            self._parts.append(html_module.unescape(text))

    def get_text(self) -> str:
        return " ".join(self._parts)


class HTMLCapture:
    """Fetches the URL and returns stripped plain-text content for LLM analysis."""

    FETCH_TIMEOUT = 4.0       # seconds
    MAX_RESPONSE_BYTES = 512_000  # 512 KB — enough for any page text

    def fetch_page_text(self, url: str) -> Optional[str]:
        """Returns structured text extracted from the page, or None on failure."""
        if not url or not url.startswith("http"):
            return None
        try:
            import requests
            resp = requests.get(
                url,
                timeout=self.FETCH_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                stream=True,
            )
            # Only process HTML responses
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None

            raw_html = resp.raw.read(self.MAX_RESPONSE_BYTES).decode("utf-8", errors="replace")
            return self._extract_text(raw_html, url)

        except Exception as exc:
            logger.debug("HTML fetch failed for %s: %s", url, exc)
            return None

    def _extract_text(self, html: str, url: str) -> str:
        parser = _TextExtractor()
        try:
            parser.feed(html)
        except Exception:
            pass

        parts = []
        if parser.title:
            parts.append(f"[PAGE TITLE] {parser.title}")
        if parser.forms_with_password:
            parts.append(f"[WARNING] Page contains {parser.forms_with_password} password input field(s)")
        body = parser.get_text()
        if body:
            parts.append(body)

        return "\n".join(parts)


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
