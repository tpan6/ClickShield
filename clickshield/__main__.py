"""Entry point: python -m clickshield  or  ClickShield.exe"""
from __future__ import annotations

import sys


def main() -> None:
    # Parse CLI args before importing Qt (avoids PyQt consuming --help etc.)
    first_run = "--first-run" in sys.argv
    minimized = "--minimized" in sys.argv

    from clickshield.config.settings import AppSettings
    from clickshield.utils.logger import setup_logging

    settings = AppSettings.load()
    setup_logging(settings.log_file)

    # Show first-run wizard if no API key exists yet
    from clickshield.utils.keystore import has_api_key
    needs_setup = first_run or not has_api_key()

    from PyQt6.QtWidgets import QApplication

    # Create app early so wizard can show
    _app_check = QApplication.instance()
    if _app_check is None:
        _app_check = QApplication(sys.argv)

    if needs_setup:
        from clickshield.ui.setup_wizard import FirstRunWizard
        wizard = FirstRunWizard(settings)
        result = wizard.exec()
        if result == 0:
            # User cancelled wizard — exit
            sys.exit(0)
        # Reload settings after wizard saved them
        settings = AppSettings.load()

    from clickshield.ui.tray import TrayApp
    app = TrayApp(settings, sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
