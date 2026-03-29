# -*- mode: python ; coding: utf-8 -*-
# Lean Windows build spec for Name Extractor (single-file EXE).
#
# Build command (using the environment that has dependencies):
#   python -m PyInstaller --clean gui_app_windows.spec

import glob
import importlib.util
import os

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

project_root = os.path.abspath(os.path.dirname(SPEC))
icon_path = os.path.join(project_root, "CT.ico")


def _ensure_required_build_packages():
    required = ["PyQt6", "pandas", "numpy", "openpyxl", "requests", "unidecode"]
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        missing_csv = ", ".join(missing)
        raise SystemExit(
            "Missing build dependencies in this Python environment: "
            f"{missing_csv}\n"
            "Install with:\n"
            "  python -m pip install -r requirements.txt pyinstaller\n"
            "Then run:\n"
            "  python -m PyInstaller --clean gui_app_windows.spec"
        )


_ensure_required_build_packages()

# Bundle only required local assets (SVG icons) and cert bundle for HTTPS checks.
svg_dir = os.path.join(project_root, "gui", "resources")
svg_files = glob.glob(os.path.join(svg_dir, "*.svg"))
local_resource_datas = [(path, os.path.join("gui", "resources")) for path in svg_files]
certifi_datas = collect_data_files("certifi")

a = Analysis(
    ["gui_app.py"],
    pathex=[project_root],
    binaries=[],
    datas=certifi_datas + local_resource_datas,
    hiddenimports=[
        "gui.main_window",
        "gui.worker",
        "gui.widgets.advanced_column_selector",
        "gui.services.excel_headers",
        "utils.updater",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "tkinter",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineQuick",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtQuick3D",
        "PyQt6.QtCharts",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
        "PyQt6.QtMultimedia",
        "pytest",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Name_Extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
    version=None,
    uac_admin=False,
    uac_uiaccess=False,
)
