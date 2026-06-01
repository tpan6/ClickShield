from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from clickshield.config.settings import AppSettings
from clickshield.core.monitor import MonitorWorker
from clickshield.core.scoring import ThreatLevel, ThreatResult
from clickshield.utils.autostart import (
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
)

logger = logging.getLogger(__name__)

_ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


def _icon(name: str) -> QIcon:
    path = _ICONS_DIR / name
    if path.exists():
        return QIcon(str(path))
    return QIcon()


class TrayApp(QApplication):
    """Main application class — owns the system tray icon and monitor thread."""

    def __init__(self, settings: AppSettings, argv: list[str] | None = None):
        super().__init__(argv or sys.argv)
        self.setQuitOnLastWindowClosed(False)
        self.setApplicationName("ClickShield")
        self.setApplicationVersion("0.1.0")

        self._settings = settings
        self._monitor: MonitorWorker | None = None
        self._tray: QSystemTrayIcon | None = None
        self._active_overlay = None   # holds a reference to prevent GC

        self._setup_tray()
        self._start_monitor()

    # ------------------------------------------------------------------
    # Tray setup

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_icon("tray_normal.png"))
        self._tray.setToolTip("ClickShield — Monitoring active")

        menu = QMenu()

        self._scan_now_action = QAction("Scan Now", self)
        self._scan_now_action.triggered.connect(self._on_scan_now)
        menu.addAction(self._scan_now_action)

        self._pause_action = QAction("Pause Monitoring", self)
        self._pause_action.setCheckable(True)
        self._pause_action.triggered.connect(self._on_toggle_pause)
        menu.addAction(self._pause_action)

        menu.addSeparator()

        settings_action = QAction("Settings…", self)
        settings_action.triggered.connect(self._on_settings)
        menu.addAction(settings_action)

        log_action = QAction("View Log", self)
        log_action.triggered.connect(self._on_view_log)
        menu.addAction(log_action)

        menu.addSeparator()

        about_action = QAction("About ClickShield", self)
        about_action.triggered.connect(self._on_about)
        menu.addAction(about_action)

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ------------------------------------------------------------------
    # Monitor lifecycle

    def _start_monitor(self) -> None:
        self._monitor = MonitorWorker(self._settings)
        self._monitor.analysis_complete.connect(self._on_analysis_complete)
        self._monitor.status_changed.connect(self._on_status_changed)
        self._monitor.scan_failed.connect(self._on_scan_failed)
        self._monitor.start()

    # ------------------------------------------------------------------
    # Slots

    def _on_analysis_complete(self, result: ThreatResult) -> None:
        level = result.level
        logger.info("Analysis complete: level=%s severity=%d", level.name, result.severity)

        if level == ThreatLevel.CLEAN:
            self._set_tray_icon("tray_normal.png", "ClickShield — All clear")
            return

        if level == ThreatLevel.LOW:
            self._set_tray_icon("tray_warning.png", f"ClickShield — Low risk detected")
            from clickshield.ui.toast import show_toast
            show_toast(result)

        elif level == ThreatLevel.MEDIUM:
            self._set_tray_icon("tray_warning.png", "ClickShield — Warning")
            from clickshield.ui.overlay_dialog import OverlayDialog
            dlg = OverlayDialog(result)
            dlg.exec()
            # Reset icon after 30 s
            QTimer.singleShot(30_000, lambda: self._set_tray_icon("tray_normal.png", "ClickShield — Monitoring active"))

        elif level == ThreatLevel.HIGH:
            self._set_tray_icon("tray_danger.png", "ClickShield — DANGER")
            from clickshield.ui.blocking_overlay import BlockingOverlay
            overlay = BlockingOverlay(result, sound_enabled=self._settings.sound_enabled)
            overlay.dismissed.connect(
                lambda: self._set_tray_icon("tray_normal.png", "ClickShield — Monitoring active")
            )
            self._active_overlay = overlay  # prevent GC
            overlay.show_blocking()

    def _on_status_changed(self, status: str) -> None:
        icons = {
            "scanning": ("tray_scanning.png", "ClickShield — Scanning…"),
            "paused":   ("tray_normal.png",   "ClickShield — Paused"),
            "error":    ("tray_warning.png",  "ClickShield — Error (check settings)"),
            "idle":     ("tray_normal.png",   "ClickShield — Monitoring active"),
        }
        name, tip = icons.get(status, ("tray_normal.png", "ClickShield"))
        self._set_tray_icon(name, tip)

    def _on_scan_failed(self, msg: str) -> None:
        logger.warning("Scan failed: %s", msg)
        if "API key" in msg:
            self._tray.showMessage(
                "ClickShield — Setup Required",
                "No API key found. Open Settings to configure.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )

    def _on_scan_now(self) -> None:
        if self._monitor:
            self._monitor.trigger_immediate_scan()

    def _on_toggle_pause(self, checked: bool) -> None:
        if not self._monitor:
            return
        if checked:
            self._monitor.pause()
            self._pause_action.setText("Resume Monitoring")
        else:
            self._monitor.resume()
            self._pause_action.setText("Pause Monitoring")

    def _on_settings(self) -> None:
        from clickshield.ui.setup_wizard import SettingsDialog
        dlg = SettingsDialog(self._settings)
        if dlg.exec():
            self._settings.save()
            # Restart monitor with new settings
            if self._monitor:
                self._monitor.stop()
                self._monitor.wait(3000)
            self._start_monitor()

    def _on_view_log(self) -> None:
        import subprocess
        log = self._settings.log_file
        if log.exists():
            subprocess.Popen(["notepad.exe", str(log)])
        else:
            QMessageBox.information(None, "ClickShield", "No log file found yet.")

    def _on_about(self) -> None:
        QMessageBox.about(
            None,
            "About ClickShield",
            "<b>ClickShield v0.1.0</b><br><br>"
            "Real-time AI-powered anti-scam protection.<br><br>"
            "Screenshots are analyzed by Qwen 3.7-plus (Alibaba Cloud DashScope).<br>"
            "No screenshots are stored or shared beyond the analysis request.<br><br>"
            "<i>Stay safe online.</i>",
        )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_scan_now()

    def _on_quit(self) -> None:
        if self._monitor:
            self._monitor.stop()
            self._monitor.wait(3000)
        self.quit()

    def _set_tray_icon(self, icon_name: str, tooltip: str) -> None:
        if self._tray:
            self._tray.setIcon(_icon(icon_name))
            self._tray.setToolTip(tooltip)
