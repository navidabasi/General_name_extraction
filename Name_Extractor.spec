# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # IMPORTANT: do NOT include "dist" or "build" here.
        # Add only your runtime files/folders, e.g.:
        # ('config', 'config'),
        # ('assets', 'assets'),
    ],
    hiddenimports=[
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.skiplist',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'openpyxl',
        'openpyxl.cell._writer',
        'fitz',
        'fitz.fitz',
        'unidecode',
        'Unidecode',
        'tabulate',
        'requests',
        'urllib3',
        'charset_normalizer',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,     # ✅ key fix on mac builds
    name='Name_Extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=True,
    icon='CT.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,               # ✅ include zipfiles too
    a.datas,
    strip=False,
    upx=False,
    name='Name_Extractor',
)

app = BUNDLE(
    coll,
    name='Name_Extractor.app',
    icon='CT.icns',
    bundle_identifier='com.crowntours.nameextractor',
)
