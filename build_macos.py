#!/usr/bin/env python3
"""
Complete build script for macOS - builds app and creates DMG in one go.

Usage: python3 build_macos.py
"""

import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

APP_NAME = "Name_Extractor"
SPEC_FILE = "gui_app_macos.spec"
APP_PATH = Path("dist") / f"{APP_NAME}.app"
DMG_NAME = f"{APP_NAME}.dmg"
DMG_PATH = Path("dist") / DMG_NAME


def run_pyinstaller():
    """Step 1: Build the .app bundle using PyInstaller."""
    print("=" * 60)
    print("Step 1: Building application with PyInstaller...")
    print("=" * 60)
    
    if not Path(SPEC_FILE).exists():
        print(f"Error: {SPEC_FILE} not found!")
        sys.exit(1)
    
    cmd = ["pyinstaller", "--clean", SPEC_FILE]
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("Error: PyInstaller build failed!")
        sys.exit(1)
    
    if not APP_PATH.exists():
        print(f"Error: {APP_PATH} was not created!")
        sys.exit(1)
    
    print(f"✅ App built successfully: {APP_PATH}")
    return True


def create_dmg():
    """Step 2: Create DMG file from .app bundle."""
    print()
    print("=" * 60)
    print("Step 2: Creating DMG file...")
    print("=" * 60)
    
    if not APP_PATH.exists():
        print(f"Error: {APP_PATH} not found!")
        print("Please build the app first.")
        sys.exit(1)
    
    # Remove old DMG if it exists
    if DMG_PATH.exists():
        print("Removing old DMG file...")
        DMG_PATH.unlink()
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Temporary directory: {temp_dir}")
    
    try:
        # Copy .app to temp directory
        print("Copying .app bundle...")
        shutil.copytree(APP_PATH, temp_dir / f"{APP_NAME}.app")
        
        # Create Applications symlink
        print("Creating Applications symlink...")
        os.symlink("/Applications", temp_dir / "Applications")
        
        # Create DMG
        print("Creating DMG (this may take a moment)...")
        cmd = [
            "hdiutil", "create",
            "-volname", APP_NAME,
            "-srcfolder", str(temp_dir),
            "-ov",
            "-format", "UDZO",
            str(DMG_PATH)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error creating DMG: {result.stderr}")
            sys.exit(1)
        
        # Get file size
        size_mb = DMG_PATH.stat().st_size / (1024 * 1024)
        
        print()
        print("=" * 60)
        print("✅ DMG created successfully!")
        print("=" * 60)
        print(f"Location: {DMG_PATH.absolute()}")
        print(f"Size: {size_mb:.1f} MB")
        print()
        print("Next steps:")
        print("1. Upload this DMG to your WebDAV server")
        print("2. Update Version.json with the new version")
        print("=" * 60)
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run complete build process."""
    if sys.platform != 'darwin':
        print("Error: This script only works on macOS")
        sys.exit(1)
    
    # Step 1: Build app
    if not run_pyinstaller():
        sys.exit(1)
    
    # Step 2: Create DMG
    create_dmg()
    
    print()
    print("🎉 Build complete! Ready for distribution.")


if __name__ == "__main__":
    main()

