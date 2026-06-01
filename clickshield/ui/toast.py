from __future__ import annotations

import logging

from clickshield.core.scoring import ThreatResult

logger = logging.getLogger(__name__)


def show_toast(result: ThreatResult) -> None:
    """Display a Windows 10/11 native toast notification for low-severity threats."""
    title = _make_title(result)
    message = result.explanation
    try:
        # Use win10toast-reborn if available, else fall back to plyer
        _show_win10toast(title, message)
    except Exception:
        try:
            _show_plyer(title, message)
        except Exception as exc:
            logger.warning("Toast notification failed: %s", exc)


def _make_title(result: ThreatResult) -> str:
    icons = {
        "phishing": "⚠ Phishing Warning",
        "fake_ecommerce": "⚠ Suspicious Store",
        "tech_support_scam": "⚠ Tech Support Scam",
        "investment_scam": "⚠ Investment Scam",
        "lottery_scam": "⚠ Lottery Scam",
        "malware_distribution": "⚠ Malware Risk",
        "social_engineering": "⚠ Social Engineering",
        "suspicious_url": "⚠ Suspicious URL",
    }
    return icons.get(result.threat_type, "⚠ ClickShield Alert")


def _show_win10toast(title: str, message: str) -> None:
    from win10toast import ToastNotifier
    notifier = ToastNotifier()
    notifier.show_toast(
        title,
        message,
        duration=8,
        threaded=True,
    )


def _show_plyer(title: str, message: str) -> None:
    from plyer import notification
    notification.notify(
        title=title,
        message=message,
        app_name="ClickShield",
        timeout=8,
    )
