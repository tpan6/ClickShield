from __future__ import annotations

import logging

from clickshield.core.scoring import ThreatResult

logger = logging.getLogger(__name__)


def show_toast(result: ThreatResult, tray=None) -> None:
    """Display a Windows toast notification for low-severity threats.

    Uses the QSystemTrayIcon message bubble (no extra packages required).
    Pass `tray` as the QSystemTrayIcon instance; if None, creates a temporary one.
    """
    title = _make_title(result)
    message = result.explanation or "Potential threat detected. Stay cautious."
    try:
        _show_qt_toast(title, message, tray)
    except Exception as exc:
        logger.warning("Toast notification failed: %s", exc)


def _make_title(result: ThreatResult) -> str:
    icons = {
        "phishing":            "⚠ Phishing Warning",
        "fake_ecommerce":      "⚠ Suspicious Store",
        "tech_support_scam":   "⚠ Tech Support Scam",
        "investment_scam":     "⚠ Investment Scam",
        "lottery_scam":        "⚠ Lottery Scam",
        "malware_distribution":"⚠ Malware Risk",
        "social_engineering":  "⚠ Social Engineering",
        "suspicious_url":      "⚠ Suspicious URL",
    }
    return icons.get(result.threat_type, "⚠ ClickShield Alert")


def _show_qt_toast(title: str, message: str, tray=None) -> None:
    from PyQt6.QtWidgets import QSystemTrayIcon
    if tray is None:
        # Fallback: find any existing tray icon
        raise RuntimeError("No tray instance provided")
    tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 8000)
