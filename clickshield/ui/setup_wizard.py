from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from clickshield.config.settings import AppSettings
from clickshield.utils.autostart import disable_autostart, enable_autostart
from clickshield.utils.keystore import load_api_key, save_api_key

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# First-run wizard
# ---------------------------------------------------------------------------

class FirstRunWizard(QWizard):
    """3-page wizard shown on first launch."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("ClickShield Setup")
        self.setMinimumWidth(540)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.addPage(_WelcomePage())
        self.addPage(_ApiKeyPage())
        self.addPage(_ConfigPage(settings))

    def accept(self) -> None:
        # Save API key
        key = self.field("api_key")
        if key:
            save_api_key(key.strip())

        # Save config from page 3
        cfg_page: _ConfigPage = self.page(2)
        cfg_page.apply_to(self._settings)
        self._settings.save()

        # Autostart
        if self._settings.autostart:
            enable_autostart()
        else:
            disable_autostart()

        super().accept()


class _WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to ClickShield")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        intro = QLabel(
            "<b>ClickShield</b> monitors your browser activity and warns you about "
            "scams, phishing sites, and social engineering in real time."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        privacy_box = QGroupBox("⚠  Privacy Disclosure")
        pb_layout = QVBoxLayout(privacy_box)
        privacy_lbl = QLabel(
            "To analyze threats, ClickShield takes periodic <b>screenshots</b> of "
            "your screen and sends them to <b>Alibaba Cloud (DashScope)</b> for "
            "AI analysis using Qwen 3.7-plus.<br><br>"
            "Screenshots are <b>not stored</b> on ClickShield servers. "
            "They are processed by Alibaba Cloud per their "
            "<a href='https://www.alibabacloud.com/help/en/model-studio/'>privacy policy</a>.<br><br>"
            "By continuing, you acknowledge and accept this."
        )
        privacy_lbl.setWordWrap(True)
        privacy_lbl.setOpenExternalLinks(True)
        pb_layout.addWidget(privacy_lbl)
        layout.addWidget(privacy_box)

        ack_cb = QCheckBox("I understand and accept the privacy disclosure")
        self.registerField("ack_privacy*", ack_cb)  # * = required
        layout.addWidget(ack_cb)


class _ApiKeyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("DashScope API Key")
        self.setSubTitle(
            "ClickShield uses Qwen 3.7-plus on Alibaba Cloud DashScope. "
            "Get a free API key at dashscope-intl.aliyuncs.com."
        )
        self._valid = False

        layout = QVBoxLayout(self)

        get_key_btn = QPushButton("Get a free API key →")
        get_key_btn.setFlat(True)
        get_key_btn.setStyleSheet("color: #1976d2; text-decoration: underline;")
        get_key_btn.clicked.connect(self._open_dashscope)
        layout.addWidget(get_key_btn)

        form = QFormLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("sk-...")
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.textChanged.connect(self._on_key_changed)
        self.registerField("api_key*", self._key_edit)
        form.addRow("API Key:", self._key_edit)
        layout.addLayout(form)

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.setEnabled(False)
        self._test_btn.clicked.connect(self._on_test)
        layout.addWidget(self._test_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)

        # Pre-fill if key already exists
        existing = load_api_key()
        if existing:
            self._key_edit.setText(existing)

    def initializePage(self) -> None:
        existing = load_api_key()
        if existing:
            self._key_edit.setText(existing)

    def _on_key_changed(self, text: str) -> None:
        self._test_btn.setEnabled(len(text.strip()) > 10)
        self._status_lbl.clear()

    def _on_test(self) -> None:
        key = self._key_edit.text().strip()
        self._test_btn.setEnabled(False)
        self._status_lbl.setText("Testing connection…")
        self._worker = _TestConnectionWorker(key)
        self._worker.result.connect(self._on_test_result)
        self._worker.start()

    def _on_test_result(self, ok: bool, msg: str) -> None:
        self._test_btn.setEnabled(True)
        if ok:
            self._status_lbl.setText("✓ Connection successful!")
            self._status_lbl.setStyleSheet("color: green;")
        else:
            self._status_lbl.setText(f"✗ {msg}")
            self._status_lbl.setStyleSheet("color: red;")

    @staticmethod
    def _open_dashscope() -> None:
        import webbrowser
        webbrowser.open("https://dashscope-intl.aliyuncs.com/")


class _ConfigPage(QWizardPage):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings
        self.setTitle("Configuration")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Scan interval
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(["15 seconds", "30 seconds (default)", "1 minute", "5 minutes"])
        self._interval_combo.setCurrentIndex(1)
        form.addRow("Scan interval:", self._interval_combo)

        # Sound
        self._sound_cb = QCheckBox("Enable alert sounds")
        self._sound_cb.setChecked(settings.sound_enabled)
        form.addRow("Sound:", self._sound_cb)

        # Clipboard
        self._clipboard_cb = QCheckBox("Monitor clipboard for suspicious URLs")
        self._clipboard_cb.setChecked(settings.monitor_clipboard)
        form.addRow("Clipboard:", self._clipboard_cb)

        # Autostart
        self._autostart_cb = QCheckBox("Start ClickShield when Windows starts")
        self._autostart_cb.setChecked(settings.autostart)
        form.addRow("Autostart:", self._autostart_cb)

        layout.addLayout(form)

    def apply_to(self, settings: AppSettings) -> None:
        intervals = [15, 30, 60, 300]
        settings.scan_interval_seconds = intervals[self._interval_combo.currentIndex()]
        settings.sound_enabled = self._sound_cb.isChecked()
        settings.monitor_clipboard = self._clipboard_cb.isChecked()
        settings.autostart = self._autostart_cb.isChecked()


class _TestConnectionWorker(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, api_key: str):
        super().__init__()
        self._key = api_key

    def run(self) -> None:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self._key,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                timeout=10,
            )
            client.models.list()
            self.result.emit(True, "")
        except Exception as exc:
            self.result.emit(False, str(exc))


# ---------------------------------------------------------------------------
# Settings dialog (re-opened from tray menu)
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """Simple settings dialog for changing config post-setup."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("ClickShield Settings")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # API key
        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        existing = load_api_key()
        if existing:
            self._key_edit.setText(existing)
        self._key_edit.setPlaceholderText("sk-...")
        form.addRow("DashScope API Key:", self._key_edit)

        # Provider
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["DashScope (Alibaba Cloud)", "OpenRouter"])
        idx = 1 if self._settings.model_provider == "openrouter" else 0
        self._provider_combo.setCurrentIndex(idx)
        form.addRow("Provider:", self._provider_combo)

        # Scan interval
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(["15 seconds", "30 seconds", "1 minute", "5 minutes"])
        interval_map = {15: 0, 30: 1, 60: 2, 300: 3}
        self._interval_combo.setCurrentIndex(interval_map.get(self._settings.scan_interval_seconds, 1))
        form.addRow("Scan interval:", self._interval_combo)

        # Sound
        self._sound_cb = QCheckBox()
        self._sound_cb.setChecked(self._settings.sound_enabled)
        form.addRow("Sound alerts:", self._sound_cb)

        # Clipboard
        self._clipboard_cb = QCheckBox()
        self._clipboard_cb.setChecked(self._settings.monitor_clipboard)
        form.addRow("Monitor clipboard:", self._clipboard_cb)

        # Autostart
        self._autostart_cb = QCheckBox()
        self._autostart_cb.setChecked(self._settings.autostart)
        form.addRow("Start with Windows:", self._autostart_cb)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        key = self._key_edit.text().strip()
        if key:
            save_api_key(key)

        providers = ["dashscope", "openrouter"]
        self._settings.model_provider = providers[self._provider_combo.currentIndex()]

        intervals = [15, 30, 60, 300]
        self._settings.scan_interval_seconds = intervals[self._interval_combo.currentIndex()]
        self._settings.sound_enabled = self._sound_cb.isChecked()
        self._settings.monitor_clipboard = self._clipboard_cb.isChecked()

        new_autostart = self._autostart_cb.isChecked()
        if new_autostart != self._settings.autostart:
            self._settings.autostart = new_autostart
            if new_autostart:
                enable_autostart()
            else:
                disable_autostart()

        self.accept()
