# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# This is the project root, passed from the build script
PROJECT_ROOT = r"/mnt/62C667B5C667885D/ComputerUseAI"

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'config'), 'config'),
        # (os.path.join(PROJECT_ROOT, 'models'), 'models'),
        (os.path.join(PROJECT_ROOT, 'tools'), 'tools'),
        (os.path.join(PROJECT_ROOT, 'assets'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'data'), 'data'),
        (os.path.join(PROJECT_ROOT, 'migrations'), 'migrations'),
        (os.path.join(PROJECT_ROOT, 'src'), 'src'), # Include src for relative imports
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'mss',
        'sounddevice',
        'pytesseract',
        'sqlalchemy',
        'alembic', # Include alembic for migrations
        'alembic.config',
        'alembic.command',
        'alembic.script',
        'alembic.operations',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'transformers',
        'faster_whisper',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ComputerUseAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'assets/icon.ico') if sys.platform == 'win32' else          os.path.join(PROJECT_ROOT, 'assets/icon.icns') if sys.platform == 'darwin' else          os.path.join(PROJECT_ROOT, 'assets/icon.png'),
)
