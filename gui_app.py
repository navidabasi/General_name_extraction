"""
GUI Application Launcher for NamesGen.

Run this file to start the graphical user interface:
    python gui_app.py
"""

import sys
import os
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
# Write logs to Documents folder to avoid permission issues on macOS
documents_path = os.path.join(os.path.expanduser('~'), 'Documents')
log_file_path = os.path.join(documents_path, 'namesgen_gui.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for GUI application."""
    try:
        logger.info("=" * 80)
        logger.info("NamesGen GUI - Starting")
        logger.info("=" * 80)
    except Exception as e:
        print(f"Error initializing logger: {e}")
        import traceback
        traceback.print_exc()
    
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
    
    # macOS-specific: Prevent app from quitting when last window closes
    # This ensures the app stays running even if window is closed
    if sys.platform == 'darwin':
        app.setQuitOnLastWindowClosed(True)  # Keep True for normal behavior
    
    # Set application font (use system default if specific font not available)
    font = app.font()
    if sys.platform == 'win32':
        font.setFamily("Segoe UI")
        font.setPointSize(9)  # Set explicit font size for Windows
    # macOS will use system default font automatically
    app.setFont(font)
    
    # Create and show main window
    try:
        from gui.main_window import MainWindow
        window = MainWindow()
        window.show()
        
        logger.info("GUI window opened")
    except Exception as e:
        error_msg = f"Error creating main window: {e}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        
        # Show error dialog if possible
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Startup Error")
            msg.setText("Failed to start application")
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
        except:
            print(error_msg)
            traceback.print_exc()
        
        sys.exit(1)
    
    # Run application
    try:
        exit_code = app.exec()
        
        logger.info("=" * 80)
        logger.info("NamesGen GUI - Exiting")
        logger.info("=" * 80)
        
        sys.exit(exit_code)
    except Exception as e:
        error_msg = f"Error running application: {e}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        print(error_msg)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

