# PyInstaller spec for ClickShield — compatible with PyInstaller 6.x
from pathlib import Path

# Collect uiautomation data if installed
uia_datas = []
try:
    import uiautomation
    uia_path = Path(uiautomation.__file__).parent
    uia_datas = [(str(uia_path / 'uia_data'), 'uiautomation/uia_data')]
except ImportError:
    pass

a = Analysis(
    ['../clickshield/__main__.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../clickshield/resources', 'clickshield/resources'),
    ] + uia_datas,
    hiddenimports=[
        'win32timezone',
        'win32cred',
        'win32clipboard',
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'clickshield.core.scoring',
        'clickshield.core.analyzer',
        'clickshield.core.capture',
        'clickshield.core.history',
        'clickshield.core.monitor',
        'clickshield.ui.tray',
        'clickshield.ui.toast',
        'clickshield.ui.overlay_dialog',
        'clickshield.ui.blocking_overlay',
        'clickshield.ui.setup_wizard',
        'clickshield.ui.dashboard',
        'clickshield.config.settings',
        'clickshield.config.defaults',
        'clickshield.utils.keystore',
        'clickshield.utils.autostart',
        'clickshield.utils.audio',
        'clickshield.utils.logger',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'matplotlib',
        'numpy',
        'scipy',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClickShield',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    uac_admin=False,
    icon='../clickshield/resources/icons/tray_normal.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClickShield',
)
