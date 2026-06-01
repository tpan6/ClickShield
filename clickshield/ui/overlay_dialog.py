from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from clickshield.core.scoring import ThreatResult

logger = logging.getLogger(__name__)


class OverlayDialog(QDialog):
    """Medium-severity (4–6) semi-transparent warning popup."""

    proceed_clicked = pyqtSignal()
    stay_safe_clicked = pyqtSignal()

    def __init__(self, result: ThreatResult, parent: QWidget | None = None):
        super().__init__(parent)
        self._result = result
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("ClickShield Warning")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setMinimumWidth(480)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                border: 2px solid #f5a623;
                border-radius: 8px;
            }
            QLabel#header {
                color: #f5a623;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#body {
                color: #e0e0e0;
                font-size: 13px;
            }
            QLabel#indicators {
                color: #ffcc80;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 6px 18px;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel(f"⚠  Suspicious Activity Detected  (Risk: {self._result.severity}/10)")
        header.setObjectName("header")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Explanation
        body = QLabel(self._result.explanation)
        body.setObjectName("body")
        body.setWordWrap(True)
        layout.addWidget(body)

        # Indicators
        if self._result.indicators:
            bullets = "\n".join(f"  • {i}" for i in self._result.indicators)
            ind_label = QLabel(bullets)
            ind_label.setObjectName("indicators")
            ind_label.setWordWrap(True)
            layout.addWidget(ind_label)

        # Buttons
        btn_box = QDialogButtonBox()
        stay_btn = btn_box.addButton("Stay Safe (Recommended)", QDialogButtonBox.ButtonRole.AcceptRole)
        proceed_btn = btn_box.addButton("Continue Anyway", QDialogButtonBox.ButtonRole.RejectRole)

        stay_btn.setStyleSheet("background-color: #2e7d32; color: white;")
        proceed_btn.setStyleSheet("background-color: #555; color: #ccc;")

        stay_btn.clicked.connect(self._on_stay_safe)
        proceed_btn.clicked.connect(self._on_proceed)

        layout.addWidget(btn_box)

    def _on_stay_safe(self) -> None:
        self.stay_safe_clicked.emit()
        self.accept()

    def _on_proceed(self) -> None:
        self.proceed_clicked.emit()
        self.reject()
