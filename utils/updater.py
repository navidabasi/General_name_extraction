"""
Auto-update functionality for Name Extractor.

Checks for updates from WebDAV server and handles download/install process.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path
from threading import Thread

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QProgressBar, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

logger = logging.getLogger(__name__)

# =============================================================================
# VERSION AND UPDATE CONFIGURATION
# =============================================================================

APP_VERSION = "1.0.2"

# WebDAV credentials (same as Crown Report)
WEBDAV_USER = "u442456-sub1"
WEBDAV_PASS = "6rp9dciVvVN92wzi"

# Update URLs for Name Extractor
VERSION_CHECK_URL = "https://u442456-sub1.your-storagebox.de/Updates/Name_Extractor/Version.json"
DOWNLOAD_URL = "https://u442456-sub1.your-storagebox.de/Updates/Name_Extractor/Name_Extractor.exe"

# Settings file for storing skipped version
SETTINGS_FILE = Path.home() / ".name_extractor_settings.json"


# =============================================================================
# SETTINGS MANAGEMENT
# =============================================================================

def load_settings():
    """Load settings from file."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load settings: {e}")
    return {}


def save_settings(settings):
    """Save settings to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save settings: {e}")


def get_skipped_version():
    """Get the version that user chose to skip."""
    settings = load_settings()
    return settings.get('skipped_version', None)


def set_skipped_version(version):
    """Set the version to skip."""
    settings = load_settings()
    settings['skipped_version'] = version
    save_settings(settings)


def clear_skipped_version():
    """Clear the skipped version (used when manually checking for updates)."""
    settings = load_settings()
    settings.pop('skipped_version', None)
    save_settings(settings)


# =============================================================================
# UPDATE CHECKER CLASS
# =============================================================================

class UpdateChecker:
    """Checks for and handles application updates."""
    
    def __init__(self, current_version=APP_VERSION, check_url=VERSION_CHECK_URL, download_url=DOWNLOAD_URL):
        self.current_version = current_version
        self.check_url = check_url
        self.download_url = download_url
        self.latest_version_info = None
    
    def check_for_updates(self):
        """
        Check if a newer version is available on WebDAV.
        
        Returns:
            tuple: (update_available, latest_version, version_info)
                   Returns (None, None, None) on error
        """
        try:
            import requests
            
            logger.info("Checking for updates...")
            response = requests.get(
                self.check_url, 
                timeout=10, 
                auth=(WEBDAV_USER, WEBDAV_PASS)
            )
            response.raise_for_status()
            
            # Parse version info (JSON format)
            self.latest_version_info = json.loads(response.text)
            latest_version = self.latest_version_info.get('version', '0.0.0')
            
            # Compare versions
            if self._is_newer_version(latest_version, self.current_version):
                logger.info(f"New version available: {latest_version} (current: {self.current_version})")
                return True, latest_version, self.latest_version_info
            else:
                logger.info(f"Current version {self.current_version} is up to date")
                return False, self.current_version, None
                
        except Exception as e:
            logger.warning(f"Could not check for updates: {e}")
            return None, None, None
    
    def _is_newer_version(self, latest, current):
        """Compare version strings (semantic versioning)."""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad with zeros if lengths differ
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
        except (ValueError, AttributeError):
            return False
    
    def download_update(self, progress_callback=None):
        """
        Download the update file from WebDAV server.
        
        Args:
            progress_callback: Function to call with download progress (0-100)
            
        Returns:
            str: Path to downloaded file, or None on error
        """
        try:
            import requests
            
            # Use download_url from JSON if present, else fallback to self.download_url
            url = self.latest_version_info.get('download_url', self.download_url) if self.latest_version_info else self.download_url
            
            response = requests.get(
                url, 
                stream=True, 
                timeout=60, 
                auth=(WEBDAV_USER, WEBDAV_PASS)
            )
            response.raise_for_status()
            
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "name_extractor_update.exe")
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(progress)
            
            logger.info(f"Update downloaded to: {temp_file}")
            return temp_file
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return None
    
    def install_update(self, update_file_path):
        """
        Install the downloaded update using a Windows-safe batch updater.
        
        Args:
            update_file_path: Path to the downloaded update file
            
        Returns:
            bool: True if installation started successfully
        """
        try:
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                # Running as script - can't auto-update
                logger.warning("Cannot auto-update when running as script")
                return False
            
            exe_dir = os.path.dirname(current_exe)
            exe_name = os.path.basename(current_exe)
            new_exe_path = os.path.join(exe_dir, "Name_Extractor_new.exe")
            
            # Copy the downloaded update to the new_exe_path
            shutil.copy2(update_file_path, new_exe_path)
            
            # Check file size (minimum 5MB for a PyQt app)
            expected_min_size = 5 * 1024 * 1024
            actual_size = os.path.getsize(new_exe_path)
            if actual_size < expected_min_size:
                logger.error(f"Downloaded update is too small ({actual_size} bytes). Aborting update.")
                os.remove(new_exe_path)
                return False
            
            # Create the batch script for Windows update and restart
            batch_script = os.path.join(exe_dir, "update_and_restart.bat")
            vbs_script = os.path.join(exe_dir, "update_launcher.vbs")
            
            # Use proper escaping for batch file paths
            current_exe_escaped = current_exe.replace('"', '""')
            new_exe_escaped = new_exe_path.replace('"', '""')
            
            with open(batch_script, "w") as f:
                f.write(f'''@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "CURRENT_EXE={current_exe_escaped}"
set "NEW_EXE={new_exe_escaped}"
set "EXE_NAME={exe_name}"
set "VBS_SCRIPT={vbs_script}"

:: Wait for application to close (silently)
:waitloop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq %EXE_NAME%" 2>NUL | find /I "%EXE_NAME%" >NUL
if not errorlevel 1 goto waitloop

:: Extra wait to ensure file handles are released
timeout /t 2 /nobreak >nul

:: Try to delete old exe (retry if locked)
set RETRY=0
:deleteloop
if exist "%CURRENT_EXE%" (
    del /F /Q "%CURRENT_EXE%" 2>nul
    if exist "%CURRENT_EXE%" (
        set /a RETRY+=1
        if !RETRY! LSS 15 (
            timeout /t 1 /nobreak >nul
            goto deleteloop
        ) else (
            exit /b 1
        )
    )
)

:: Rename new exe to current exe name
move /Y "%NEW_EXE%" "%CURRENT_EXE%"
if errorlevel 1 exit /b 1

:: Start the updated application
start "" "%CURRENT_EXE%"

:: Clean up VBS launcher and this batch file
if exist "%VBS_SCRIPT%" del /F /Q "%VBS_SCRIPT%"
(goto) 2>nul & del "%~f0"
''')
            
            # Create VBScript to run batch file completely hidden
            with open(vbs_script, "w") as f:
                f.write(f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "{batch_script}" & chr(34), 0, False
Set WshShell = Nothing
''')
            
            # Start the update process (runs independently and hidden)
            if sys.platform == 'win32':
                os.startfile(vbs_script)
            else:
                subprocess.Popen(['sh', batch_script])
            
            logger.info("Update script started (hidden). Exiting application...")
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            import traceback
            traceback.print_exc()
            return False


# =============================================================================
# UPDATE SIGNAL HELPER (for thread-safe UI updates)
# =============================================================================

class UpdateSignals(QObject):
    """Signals for update process communication with UI."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)


# =============================================================================
# UPDATE DIALOG (PyQt6)
# =============================================================================

class UpdateDialog(QDialog):
    """Dialog for showing update information and handling the update process."""
    
    def __init__(self, parent, version_info):
        super().__init__(parent)
        self.version_info = version_info
        self.result = None
        self.signals = UpdateSignals()
        
        self.setWindowTitle("Update Available")
        self.setMinimumSize(500, 400)
        self.resize(500, 450)
        self.setModal(True)
        
        # Windows-compatible styling for dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                background-color: transparent;
                color: #212529;
            }
        """)
        
        self._create_widgets()
        self._connect_signals()
    
    def _create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🎉 Update Available!")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #5B5FC7;
                background-color: transparent;
            }
        """)
        layout.addWidget(title)
        
        # Version info
        current_version = APP_VERSION
        new_version = self.version_info.get('version', 'Unknown')
        
        version_label = QLabel(
            f"<b>Current Version:</b> {current_version}<br>"
            f"<b>New Version:</b> {new_version}"
        )
        version_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #212529;
                background-color: transparent;
            }
        """)
        layout.addWidget(version_label)
        
        # Release notes
        notes_label = QLabel("What's New:")
        notes_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #212529;
                background-color: transparent;
            }
        """)
        layout.addWidget(notes_label)
        
        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlainText(
            self.version_info.get('release_notes', 'No release notes available.')
        )
        self.notes_text.setStyleSheet("""
            QTextEdit {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.notes_text)
        
        # Progress bar (initially hidden)
        self.progress_container = QVBoxLayout()
        self.progress_label = QLabel("Downloading...")
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6C757D;
                background-color: transparent;
            }
        """)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                background-color: #F8F9FA;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #5B5FC7;
                border-radius: 5px;
            }
        """)
        self.progress_container.addWidget(self.progress_label)
        self.progress_container.addWidget(self.progress_bar)
        
        progress_widget = QLabel()  # Placeholder
        progress_widget.setLayout(self.progress_container)
        progress_widget.hide()
        self.progress_widget = progress_widget
        layout.addWidget(self.progress_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.skip_btn = QPushButton("Skip This Version")
        self.skip_btn.setFixedHeight(36)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                color: #6C757D;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
                border-color: #CED4DA;
            }
            QPushButton:pressed {
                background-color: #DEE2E6;
            }
        """)
        self.skip_btn.clicked.connect(self._skip_version)
        button_layout.addWidget(self.skip_btn)
        
        button_layout.addStretch()
        
        self.later_btn = QPushButton("Later")
        self.later_btn.setFixedHeight(36)
        self.later_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                color: #495057;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
                border-color: #CED4DA;
            }
            QPushButton:pressed {
                background-color: #DEE2E6;
            }
        """)
        self.later_btn.clicked.connect(self._update_later)
        button_layout.addWidget(self.later_btn)
        
        self.update_btn = QPushButton("Update Now")
        self.update_btn.setFixedHeight(36)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: 2px solid #5B5FC7;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A4FB5;
                border-color: #4A4FB5;
            }
            QPushButton:pressed {
                background-color: #3A3F95;
                border-color: #3A3F95;
            }
            QPushButton:disabled {
                background-color: #ADB5BD;
                border-color: #ADB5BD;
            }
        """)
        self.update_btn.clicked.connect(self._start_update)
        button_layout.addWidget(self.update_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        self.signals.progress.connect(self._update_progress)
        self.signals.finished.connect(self._update_finished)
        self.signals.error.connect(self._show_error)
    
    def _skip_version(self):
        """Skip this version and don't ask again."""
        new_version = self.version_info.get('version')
        if new_version:
            set_skipped_version(new_version)
            logger.info(f"User chose to skip version {new_version}")
        self.result = "skip"
        self.accept()
    
    def _update_later(self):
        """Remind later (just close the dialog)."""
        self.result = "later"
        self.accept()
    
    def _start_update(self):
        """Start the update process."""
        self.result = "update"
        
        # Disable buttons and show progress
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_widget.show()
        
        # Start update in separate thread
        update_thread = Thread(target=self._perform_update, daemon=True)
        update_thread.start()
    
    def _perform_update(self):
        """Perform the actual update process in background thread."""
        try:
            checker = UpdateChecker()
            
            # Download update
            def progress_callback(progress):
                self.signals.progress.emit(int(progress))
            
            update_file = checker.download_update(progress_callback)
            if not update_file:
                self.signals.error.emit("Failed to download update")
                return
            
            # Confirm installation
            self.signals.progress.emit(100)
            
            # Ask for confirmation on main thread
            new_version = self.version_info.get('version', 'the new version')
            
            # Note: We need to do this on the main thread
            # For simplicity, we'll just proceed with install
            if checker.install_update(update_file):
                self.signals.finished.emit(True, "Update installed successfully!")
                # Exit the application
                import os
                os._exit(0)
            else:
                self.signals.error.emit("Failed to install update")
                
        except Exception as e:
            logger.error(f"Update process failed: {e}")
            self.signals.error.emit(str(e))
    
    def _update_progress(self, value):
        """Update progress bar."""
        self.progress_bar.setValue(value)
        if value >= 100:
            self.progress_label.setText("Installing...")
    
    def _update_finished(self, success, message):
        """Handle update completion."""
        if success:
            QMessageBox.information(self, "Update Complete", message)
        self.accept()
    
    def _show_error(self, message):
        """Show error message."""
        QMessageBox.critical(self, "Update Error", message)
        # Re-enable buttons
        self.update_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.progress_widget.hide()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def check_for_updates_async(callback):
    """
    Check for updates in background thread.
    
    Args:
        callback: Function to call with (update_available, version_info) or (None, None) on error
    """
    def _check():
        checker = UpdateChecker()
        available, version, info = checker.check_for_updates()
        callback(available, info)
    
    thread = Thread(target=_check, daemon=True)
    thread.start()


def should_show_update(version_info):
    """
    Check if we should show the update dialog.
    
    Returns False if user has skipped this version.
    """
    if not version_info:
        return False
    
    new_version = version_info.get('version')
    skipped_version = get_skipped_version()
    
    if skipped_version and skipped_version == new_version:
        logger.info(f"Skipping update notification for version {new_version} (user preference)")
        return False
    
    return True

