# -*- mode: python ; coding: utf-8 -*-
# macOS Build Specification for Name Extractor
# 
# Build command: pyinstaller gui_app_macos.spec
# 
# This spec file creates a .app bundle that can run without code signing.
# Users may need to right-click and "Open" the first time to bypass Gatekeeper.

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include GUI resources if needed
        # ('gui/resources', 'gui/resources'),
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
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.sip',
        'requests',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'unidecode',
        'Unidecode',
        'gui',
        'gui.main_window',
        'gui.widgets',
        'gui.worker',
        'utils',
        'utils.updater',
        'utils.age_calculator',
        'extractors',
        'validators',
        'data_loader',
        'processor',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_macos.py'],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Required for macOS app bundle
    name='Name_Extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can cause issues on macOS
    console=False,  # No console window
    argv_emulation=True,  # macOS file association support
    target_arch=None,  # Auto-detect architecture
    codesign_identity=None,  # No code signing (avoids signature issues)
    entitlements_file=None,  # No entitlements needed
    icon='CT.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Name_Extractor',
)

app = BUNDLE(
    coll,
    name='Name_Extractor.app',
    icon='CT.icns',
    bundle_identifier='com.crowntours.nameextractor',
    version=None,  # Will use version from app if available
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13',  # macOS High Sierra minimum
        'NSHumanReadableCopyright': 'Copyright © 2025 Crown Tours',
        'CFBundleShortVersionString': '1.0.3',
        'CFBundleVersion': '1.0.3',
    },
)

