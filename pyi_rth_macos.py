"""
PyInstaller runtime hook for macOS.
This ensures proper initialization on macOS.
"""

import sys
import os

# Fix for macOS: ensure we can find resources
if getattr(sys, 'frozen', False):
    # Running as a bundled app
    if sys.platform == 'darwin':
        # Set the working directory to the app bundle's Resources folder
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)

