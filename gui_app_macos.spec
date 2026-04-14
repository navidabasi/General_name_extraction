# -*- mode: python ; coding: utf-8 -*-
# Lean macOS build spec for Name Extractor.
#
# Build command (using the environment that has dependencies):
#   python -m PyInstaller --clean gui_app_macos.spec

import glob
import importlib.util
import os
import re

from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

project_root = os.path.abspath(os.path.dirname(SPEC))
icon_path = os.path.join(project_root, "CT.icns")
runtime_hook = os.path.join(project_root, "pyi_rth_macos.py")


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
            "  python -m PyInstaller --clean gui_app_macos.spec"
        )


def _read_app_version():
    updater_path = os.path.join(project_root, "utils", "updater.py")
    fallback = "1.0.0"
    try:
        with open(updater_path, "r", encoding="utf-8") as f:
            text = f.read()
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else fallback
    except OSError:
        return fallback


_ensure_required_build_packages()
app_version = _read_app_version()

# Bundle only required local assets (SVG icons) and cert bundle for HTTPS checks.
svg_dir = os.path.join(project_root, "gui", "resources")
svg_files = glob.glob(os.path.join(svg_dir, "*.svg"))
local_resource_datas = [(path, os.path.join("gui", "resources")) for path in svg_files]
certifi_datas = collect_data_files("certifi")
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all("openpyxl")
et_xmlfile_datas, et_xmlfile_binaries, et_xmlfile_hiddenimports = collect_all("et_xmlfile")

a = Analysis(
    ["gui_app.py"],
    pathex=[project_root],
    binaries=openpyxl_binaries + et_xmlfile_binaries,
    datas=certifi_datas + local_resource_datas + openpyxl_datas + et_xmlfile_datas,
    hiddenimports=[
        "gui.main_window",
        "gui.worker",
        "gui.widgets.advanced_column_selector",
        "gui.services.excel_headers",
        "utils.updater",
        "openpyxl",
        "et_xmlfile",
    ] + openpyxl_hiddenimports + et_xmlfile_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[runtime_hook] if os.path.exists(runtime_hook) else [],
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
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Name_Extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name="Name_Extractor",
)

app = BUNDLE(
    coll,
    name="Name_Extractor.app",
    icon=icon_path if os.path.exists(icon_path) else None,
    bundle_identifier="com.crowntours.nameextractor",
    version=app_version,
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": "True",
        "LSMinimumSystemVersion": "10.13",
        "NSHumanReadableCopyright": "Copyright © 2025 Crown Tours",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": app_version,
    },
)
