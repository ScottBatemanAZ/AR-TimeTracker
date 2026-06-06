# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AR Time Tracker
# Build with: pyinstaller AR-TimeTracker.spec

import os

block_cipher = None

# Static assets to bundle alongside the executable
bundled_assets = [
    ('index.html',            '.'),
    ('filament-library.json', '.'),
    ('resin-library.json',    '.'),
    ('ARLogo-FullTrans.png',  '.'),
    ('ARSymbol.png',          '.'),
    ('ARSymbol.ico',          '.'),
    ('icon-design.svg',       '.'),
    ('icon-fdm.svg',          '.'),
    ('icon-resin.svg',        '.'),
]

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=bundled_assets,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AR-TimeTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # Keep console window — startup logs are useful
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ARSymbol.ico',
)
