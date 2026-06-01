"""Entry point: python -m clickshield  or  ClickShield.exe"""
from __future__ import annotations

import sys


def main() -> None:
    # Parse CLI args before importing Qt (avoids PyQt consuming --help etc.)
    first_run = "--first-run" in sys.argv

    from clickshield.config.settings import AppSettings
    from clickshield.utils.logger import setup_logging

    settings = AppSettings.load()
    setup_logging(settings.log_file)

    from clickshield.utils.keystore import has_api_key
    needs_setup = first_run or not has_api_key()

    # TrayApp IS the QApplication — create it once here so there is exactly one.
    from clickshield.ui.tray import TrayApp
    app = TrayApp(settings, sys.argv)

    if needs_setup:
        from clickshield.ui.setup_wizard import FirstRunWizard
        wizard = FirstRunWizard(settings)
        result = wizard.exec()
        if result == 0:
            # User cancelled — exit
            sys.exit(0)
        # Reload settings and restart monitor with the new API key
        settings = AppSettings.load()
        app._settings = settings
        if app._monitor:
            app._monitor.stop()
            app._monitor.wait(3000)
        app._start_monitor()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
