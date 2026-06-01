from __future__ import annotations

import logging
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from clickshield.core.scoring import ThreatResult
from clickshield.utils.audio import play_alert

logger = logging.getLogger(__name__)

_DISMISS_DELAY_MS = 3000   # 3 seconds before the dismiss button activates
_SAFETY_TIMEOUT_MS = 60_000  # 60-second hard release — user is never permanently locked


class BlockingOverlay(QWidget):
    """
    High-severity (7–10) full-screen red overlay.

    Grabs mouse + keyboard so no click passes through to the underlying window.
    The dismiss button activates after 3 seconds. A 60-second safety timer
    releases the grab automatically so the user is never permanently locked out.
    """

    dismissed = pyqtSignal()

    def __init__(self, result: ThreatResult, sound_enabled: bool = True):
        super().__init__(None)
        self._result = result
        self._sound_enabled = sound_enabled
        self._dismiss_btn: QPushButton | None = None
        self._countdown_label: QLabel | None = None
        self._seconds_left = _DISMISS_DELAY_MS // 1000
        self._build_ui()
        self._setup_timers()

    # ------------------------------------------------------------------
    # Public

    def show_blocking(self) -> None:
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.grabMouse()
        self.grabKeyboard()
        play_alert(self._sound_enabled)

    # ------------------------------------------------------------------
    # Build UI

    def _build_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: rgba(160, 0, 0, 255);")

        # Span all monitors
        screen_rect = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_rect)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(60, 40, 60, 40)

        # Shield icon + big title
        title = QLabel("🛡  DANGER  🛡")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        severity_lbl = QLabel(f"Threat Level: {self._result.severity}/10  |  {self._result.threat_type.replace('_', ' ').title()}")
        severity_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        severity_lbl.setFont(QFont("Segoe UI", 16))
        severity_lbl.setStyleSheet("color: #ffcccc;")
        layout.addWidget(severity_lbl)

        # Explanation
        explanation = QLabel(self._result.explanation)
        explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        explanation.setWordWrap(True)
        explanation.setFont(QFont("Segoe UI", 14))
        explanation.setStyleSheet("color: white;")
        layout.addWidget(explanation)

        # Indicators
        if self._result.indicators:
            bullets = "\n".join(f"  •  {i}" for i in self._result.indicators)
            ind_lbl = QLabel(bullets)
            ind_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ind_lbl.setWordWrap(True)
            ind_lbl.setFont(QFont("Segoe UI", 12))
            ind_lbl.setStyleSheet("color: #ffdddd;")
            layout.addWidget(ind_lbl)

        # Countdown label
        self._countdown_label = QLabel(f"You may dismiss this in {self._seconds_left}s...")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setFont(QFont("Segoe UI", 11))
        self._countdown_label.setStyleSheet("color: #ffcccc;")
        layout.addWidget(self._countdown_label)

        # Dismiss button (disabled initially)
        self._dismiss_btn = QPushButton("I Understand — Dismiss")
        self._dismiss_btn.setEnabled(False)
        self._dismiss_btn.setFixedWidth(300)
        self._dismiss_btn.setFixedHeight(48)
        self._dismiss_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._dismiss_btn.setStyleSheet("""
            QPushButton:disabled { background-color: #555; color: #888; border-radius: 6px; }
            QPushButton:enabled  { background-color: #222; color: white; border-radius: 6px; }
            QPushButton:enabled:hover { background-color: #333; }
        """)
        self._dismiss_btn.clicked.connect(self._on_dismiss)

        btn_wrapper = QWidget()
        btn_layout = QVBoxLayout(btn_wrapper)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self._dismiss_btn)
        layout.addWidget(btn_wrapper)

    def _setup_timers(self) -> None:
        # Enable dismiss button after delay
        self._enable_timer = QTimer(self)
        self._enable_timer.setSingleShot(True)
        self._enable_timer.timeout.connect(self._enable_dismiss)
        self._enable_timer.start(_DISMISS_DELAY_MS)

        # Countdown tick every second
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick_countdown)
        self._tick_timer.start(1000)

        # Safety auto-release
        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self._on_dismiss)
        self._safety_timer.start(_SAFETY_TIMEOUT_MS)

    # ------------------------------------------------------------------
    # Event overrides — consume all input until dismissed

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._dismiss_btn and self._dismiss_btn.isEnabled():
            btn_global = self._dismiss_btn.mapToGlobal(QPoint(0, 0))
            btn_rect = QRect(btn_global, self._dismiss_btn.size())
            if btn_rect.contains(event.globalPosition().toPoint()):
                self._on_dismiss()
                return
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        event.accept()

    def closeEvent(self, event) -> None:
        # Block Alt+F4 and other close attempts until dismiss
        event.ignore()

    # ------------------------------------------------------------------
    # Slots

    def _enable_dismiss(self) -> None:
        if self._dismiss_btn:
            self._dismiss_btn.setEnabled(True)
        if self._countdown_label:
            self._countdown_label.setText("Click below to dismiss.")
        self._tick_timer.stop()

    def _tick_countdown(self) -> None:
        self._seconds_left = max(0, self._seconds_left - 1)
        if self._countdown_label:
            self._countdown_label.setText(f"You may dismiss this in {self._seconds_left}s...")

    def _on_dismiss(self) -> None:
        self._safety_timer.stop()
        self._enable_timer.stop()
        self._tick_timer.stop()
        try:
            self.releaseMouse()
            self.releaseKeyboard()
        except Exception:
            pass
        self.hide()
        self.dismissed.emit()
        self.deleteLater()
