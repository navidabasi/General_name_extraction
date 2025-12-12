# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Name Extractor application.

To build the executable:
    pyinstaller Name_Extractor.spec

Or with uv:
    uv run pyinstaller Name_Extractor.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Get the directory containing the spec file
SPEC_DIR = Path(SPECPATH)

# Collect all data files (SVG icons, etc.)
datas = [
    # GUI resources (SVG icons)
    (str(SPEC_DIR / 'gui' / 'resources' / '*.svg'), 'gui/resources'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # PyQt6 modules
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    
    # Pandas and dependencies
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    
    # OpenPyXL
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.worksheet.datavalidation',
    
    # Standard library that might be missed
    'logging',
    'json',
    'datetime',
    're',
    'pathlib',
    
    # App modules
    'config',
    'data_loader',
    'processor',
    'main',
    
    # Extractors
    'extractors',
    'extractors.base_extractor',
    'extractors.gyg_mda',
    'extractors.gyg_standard',
    'extractors.non_gyg',
    
    # GUI
    'gui',
    'gui.main_window',
    'gui.worker',
    'gui.widgets',
    'gui.widgets.file_input',
    'gui.widgets.status_panel',
    'gui.resources',
    'gui.resources.icons',
    
    # Utils
    'utils',
    'utils.age_calculator',
    'utils.normalization',
    'utils.private_notes_parser',
    'utils.scenario_handler',
    'utils.tag_definitions',
    'utils.tix_nom_generator',
    'utils.updater',
    
    # Validators
    'validators',
    'validators.duplicate_validator',
    'validators.name_validator',
    'validators.unit_validator',
    'validators.youth_validator',
]

a = Analysis(
    ['gui_app.py'],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'scipy',
        'numpy.testing',
        'tkinter',
        'test',
        'unittest',
        'spacy',  # Not needed in production
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
    name='Name_Extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=CT.ico,  # Add icon path here if you have one, e.g., 'icon.ico'
)

