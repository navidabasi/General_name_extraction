# -*- mode: python ; coding: utf-8 -*-
# Windows Build Specification for Name Extractor
# 
# Build command: pyinstaller gui_app_windows.spec
# 
# This spec file creates a SINGLE-FILE Windows executable (.exe)
# that bundles all dependencies including Python runtime.
#
# Prerequisites:
#   1. Install dependencies: pip install pyinstaller PyQt6 pandas openpyxl requests unidecode
#   2. Make sure CT.ico exists (Windows icon) or remove icon= parameter
#
# Build: pyinstaller gui_app_windows.spec
# Output: dist/Name_Extractor.exe (single file, ~80-150MB)

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Get the project root directory
project_root = os.path.abspath(os.path.dirname(SPEC))

# Collect all data files and binaries for problematic packages
pandas_datas, pandas_binaries, pandas_hiddenimports = collect_all('pandas')
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')

# Collect PyQt6 submodules and data (Qt plugins, translations, etc.)
pyqt6_hiddenimports = collect_submodules('PyQt6')
pyqt6_datas, pyqt6_binaries, _ = collect_all('PyQt6')

# Collect certifi certificate bundle for HTTPS requests
certifi_datas = collect_data_files('certifi')

# ============================================================================
# LOCAL APPLICATION DATA FILES
# These are the resource files (SVG icons, etc.) that must be bundled
# Format: (source_path, destination_folder_in_bundle)
# ============================================================================
import glob

# Collect all SVG files from the resources directory
svg_dir = os.path.join(project_root, 'gui', 'resources')
svg_files = glob.glob(os.path.join(svg_dir, '*.svg'))
dest_folder = os.path.join('gui', 'resources')

# Create list of (source, dest) tuples for each SVG file
local_datas = [(svg_file, dest_folder) for svg_file in svg_files]

# If no SVG files found, print a warning
if not local_datas:
    print(f"WARNING: No SVG files found in {svg_dir}")
    print("         Icon resources may not be bundled correctly.")
else:
    print(f"Found {len(local_datas)} SVG files to bundle from {svg_dir}")

a = Analysis(
    ['gui_app.py'],
    pathex=[project_root],
    binaries=pandas_binaries + numpy_binaries + openpyxl_binaries + pyqt6_binaries,
    datas=pandas_datas + numpy_datas + openpyxl_datas + pyqt6_datas + certifi_datas + local_datas,
    hiddenimports=[
        # ============================================================
        # LOCAL APPLICATION MODULES
        # These are your project's own modules - must be explicitly listed
        # ============================================================
        'config',
        'processor',
        'data_loader',
        'main',
        # GUI modules
        'gui',
        'gui.main_window',
        'gui.worker',
        'gui.widgets',
        'gui.widgets.file_input',
        'gui.widgets.status_panel',
        'gui.resources',
        'gui.resources.icons',
        # Extractors
        'extractors',
        'extractors.base_extractor',
        'extractors.gyg_mda',
        'extractors.gyg_standard',
        'extractors.non_gyg',
        # Validators
        'validators',
        'validators.duplicate_validator',
        'validators.name_validator',
        'validators.unit_validator',
        'validators.youth_validator',
        # Utils
        'utils',
        'utils.age_calculator',
        'utils.normalization',
        'utils.private_notes_parser',
        'utils.reseller_dob_extractors',
        'utils.scenario_handler',
        'utils.tag_definitions',
        'utils.tix_nom_generator',
        'utils.updater',
        
        # ============================================================
        # PANDAS AND ITS DEPENDENCIES
        # ============================================================
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.parsing',
        'pandas._libs.skiplist',
        'pandas._libs.lib',
        'pandas._libs.hashtable',
        'pandas._libs.join',
        'pandas._libs.index',
        'pandas._libs.interval',
        'pandas._libs.sparse',
        'pandas._libs.parsers',
        'pandas._libs.writers',
        'pandas.io.formats.style',
        'pandas.core.arrays.sparse',
        
        # ============================================================
        # NUMPY
        # ============================================================
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.core._dtype_ctypes',
        'numpy.lib',
        'numpy.lib.format',
        'numpy.random',
        'numpy.random.common',
        'numpy.random.bounded_integers',
        'numpy.random.entropy',
        
        # ============================================================
        # OPENPYXL (Excel file support)
        # ============================================================
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.cell._writer',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'openpyxl.worksheet._reader',
        'openpyxl.worksheet._writer',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.utils.cell',
        'openpyxl.utils.datetime',
        'openpyxl.reader',
        'openpyxl.reader.excel',
        'openpyxl.writer',
        'openpyxl.writer.excel',
        
        # ============================================================
        # PYQT6 (GUI Framework)
        # ============================================================
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.sip',
        
        # ============================================================
        # NETWORK/HTTP (for auto-updater and web requests)
        # ============================================================
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.structures',
        'urllib3',
        'urllib3.util',
        'urllib3.util.ssl_',
        'urllib3.util.retry',
        'urllib3.util.timeout',
        'urllib3.poolmanager',
        'urllib3.connectionpool',
        'charset_normalizer',
        'certifi',
        'idna',
        'ssl',
        
        # ============================================================
        # TEXT PROCESSING
        # ============================================================
        'unidecode',
        'Unidecode',
        
        # ============================================================
        # WINDOWS-SPECIFIC (for DPI awareness in gui_app.py)
        # ============================================================
        'ctypes',
        'ctypes.wintypes',
        
        # ============================================================
        # STANDARD LIBRARY (commonly missed by PyInstaller)
        # ============================================================
        'logging',
        'logging.handlers',
        'json',
        're',
        'datetime',
        'pathlib',
        'typing',
        'collections',
        'collections.abc',
        'functools',
        'itertools',
        'operator',
        'copy',
        'io',
        'os',
        'sys',
        'traceback',
        'tempfile',
        'shutil',
        'subprocess',
        'threading',
        'queue',
        'hashlib',
        'zipfile',
        'tarfile',
        'stat',
        
        # ============================================================
        # ENCODINGS (for international character support)
        # ============================================================
        'encodings',
        'encodings.utf_8',
        'encodings.utf_16',
        'encodings.ascii',
        'encodings.latin_1',
        'encodings.cp1252',
        'encodings.idna',
        'encodings.mbcs',  # Windows-specific
        
    ] + pandas_hiddenimports + numpy_hiddenimports + openpyxl_hiddenimports + pyqt6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused heavy packages to reduce exe size
        'matplotlib',
        'tkinter',
        'scipy',
        'PIL',
        'Pillow',
        'cv2',
        'opencv',
        'tensorflow',
        'torch',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
        'sphinx',
        'docutils',
        # Exclude test modules
        'test',
        'tests',
        'unittest',
        '_pytest',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ============================================================================
# SINGLE-FILE EXECUTABLE (onefile mode)
# All dependencies are bundled inside the .exe
# The resulting executable is self-contained and portable
# ============================================================================

# Check for Windows icon file (optional)
icon_file = os.path.join(project_root, 'CT.ico')
if not os.path.exists(icon_file):
    print(f"WARNING: Icon file not found: {icon_file}")
    print("         The executable will be built without a custom icon.")
    print("         To add an icon, create CT.ico or convert CT.icns to .ico format.")
    icon_file = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,       # Include binaries in the exe (required for onefile)
    a.datas,          # Include data files in the exe (required for onefile)
    [],
    name='Name_Extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,      # Don't strip symbols (can cause issues on Windows)
    upx=False,        # Disable UPX compression - can cause antivirus false positives
    upx_exclude=[],
    runtime_tmpdir=None,  # Use system temp directory for extraction
    console=False,    # No console window (GUI app) - set True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,   # Windows icon file (optional)
    version=None,     # Can add version info file if needed
    
    # Windows-specific options
    uac_admin=False,       # Don't require admin privileges
    uac_uiaccess=False,    # Don't require UI access
)
