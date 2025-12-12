"""
GUI Application Launcher for NamesGen.

Run this file to start the graphical user interface:
    python gui_app.py
"""

import sys
import logging

# PyQt6 imports - installed via: pip install PyQt6
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError as e:
    print(f"Error: PyQt6 not installed. Install with: pip install PyQt6")
    print(f"Details: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('namesgen_gui.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for GUI application."""
    logger.info("=" * 80)
    logger.info("NamesGen GUI - Starting")
    logger.info("=" * 80)
    
    # Windows-specific fixes
    if sys.platform == 'win32':
        # Enable high DPI scaling for Windows
        try:
            import ctypes
            # Windows 8.1+
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            # Windows 8 or earlier
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Name Extractor")
    app.setOrganizationName("Name Extractor")
    
    # Set application font (use system default if specific font not available)
    font = app.font()
    if sys.platform == 'win32':
        font.setFamily("Segoe UI")
        font.setPointSize(9)  # Set explicit font size for Windows
    # macOS will use system default font automatically
    app.setFont(font)
    
    # Create and show main window
    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    logger.info("GUI window opened")
    
    # Run application
    exit_code = app.exec()
    
    logger.info("=" * 80)
    logger.info("NamesGen GUI - Exiting")
    logger.info("=" * 80)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

