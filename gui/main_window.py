"""
Main application window for NamesGen GUI.
"""

import os
import sys
import platform
import subprocess
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QProgressBar, QFileDialog,
                              QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QCursor

from gui.widgets import FileInputWidget
from gui.worker import ExtractionWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.worker = None
        self.output_file = None
        self._pending_update_info = None
        
        self._init_ui()
        self._connect_signals()
        
        # Check for updates after window is shown (delay to not block startup)
        QTimer.singleShot(1000, self._check_for_updates_on_startup)
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Name Extractor")
        self.setMinimumSize(QSize(520, 630))
        self.resize(520, 630)  # Default size, but resizable
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main panel (File inputs)
        main_panel = self._create_main_panel()
        main_layout.addWidget(main_panel)
        
        central_widget.setLayout(main_layout)
        
        # Apply global stylesheet - Windows compatible
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F0F2F5;
            }
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #212529;
                font-size: 13px;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: 2px solid #5B5FC7;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
                font-size: 13px;
                font-weight: bold;
            }
            QMessageBox QPushButton:hover {
                background-color: #4A4FB5;
                border-color: #4A4FB5;
            }
            QMessageBox QPushButton:pressed {
                background-color: #3A3F95;
                border-color: #3A3F95;
            }
        """)
    
    def _create_main_panel(self) -> QWidget:
        """Create the main panel with file inputs and progress bar."""
        panel = QWidget()
        panel.setObjectName("mainPanel")
        panel.setAutoFillBackground(True)
        panel.setStyleSheet("""
            QWidget#mainPanel {
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Name Extractor")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #212529;
                background-color: transparent;
            }
        """)
        layout.addWidget(title)
        
        # File inputs with card design - use stretch for responsiveness
        self.ventrata_input = FileInputWidget("Ventrata File", required=True)
        self.ventrata_input.setSizePolicy(
            self.ventrata_input.sizePolicy().horizontalPolicy(),
            self.ventrata_input.sizePolicy().verticalPolicy()
        )
        layout.addWidget(self.ventrata_input)
        
        self.monday_input = FileInputWidget("Monday File", required=False)
        layout.addWidget(self.monday_input)
        
        self.update_input = FileInputWidget("Update File", required=False)
        layout.addWidget(self.update_input)
        
        layout.addSpacing(8)
        
        # Extract button (centered)
        button_container = QHBoxLayout()
        button_container.addStretch()
        
        self.extract_btn = QPushButton("Extract")
        self.extract_btn.setFixedSize(160, 42)
        self.extract_btn.setEnabled(False)  # Disabled by default
        self.extract_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: 2px solid #5B5FC7;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
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
                color: #6C757D;
            }
        """)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        button_container.addWidget(self.extract_btn)
        
        button_container.addStretch()
        layout.addLayout(button_container)
        
        # Check for Updates link (centered, under Extract button)
        update_container = QHBoxLayout()
        update_container.addStretch()
        
        self.update_link = QLabel("Check for Updates")
        self.update_link.setStyleSheet("""
            QLabel {
                color: #5B5FC7;
                font-size: 12px;
                text-decoration: underline;
                background-color: transparent;
            }
            QLabel:hover {
                color: #4A4FB5;
            }
        """)
        self.update_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_link.mousePressEvent = lambda e: self._on_check_updates_clicked()
        update_container.addWidget(self.update_link)
        
        update_container.addStretch()
        layout.addLayout(update_container)
        
        # Version number (centered, light gray)
        version_container = QHBoxLayout()
        version_container.addStretch()
        
        from utils.updater import APP_VERSION
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 10px;
                background-color: transparent;
            }
        """)
        version_container.addWidget(self.version_label)
        
        version_container.addStretch()
        layout.addLayout(version_container)
        
        # Progress section (under Extract button)
        layout.addSpacing(8)
        
        # Progress bar - always visible to keep layout stable
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #DEE2E6;
                border-radius: 10px;
                background-color: #F8F9FA;
            }
            QProgressBar::chunk {
                background-color: #CDFB93;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Progress text - always visible to keep layout stable
        self.progress_label = QLabel(" ")  # Space to reserve height
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6C757D;
                padding-left: 4px;
                background-color: transparent;
            }
        """)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.progress_label)
        
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # File input signals
        self.ventrata_input.file_selected.connect(self._on_file_changed)
        self.ventrata_input.file_cleared.connect(self._on_file_changed)
        self.monday_input.file_selected.connect(self._on_file_changed)
        self.monday_input.file_cleared.connect(self._on_file_changed)
        self.update_input.file_selected.connect(self._on_file_changed)
        self.update_input.file_cleared.connect(self._on_file_changed)
    
    def _on_file_changed(self):
        """Handle file selection changes."""
        # Enable extract button only if Ventrata file is selected
        has_ventrata = self.ventrata_input.has_file()
        self.extract_btn.setEnabled(has_ventrata and not self._is_processing())
    
    def _is_processing(self) -> bool:
        """Check if processing is in progress."""
        return self.worker is not None and self.worker.isRunning()
    
    def _on_extract_clicked(self):
        """Handle extract button click."""
        # Validate inputs
        if not self.ventrata_input.has_file():
            QMessageBox.warning(
                self,
                "Missing File",
                "Please select a Ventrata file."
            )
            return
        
        # Ask for output directory - use native dialog on Windows
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",  # Start in current directory
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not output_dir:
            # User cancelled
            return
        
        # Start extraction
        self._start_extraction(output_dir)
    
    def _start_extraction(self, output_dir: str):
        """
        Start the extraction process.
        
        Args:
            output_dir: Output directory path
        """
        # Reset UI
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting extraction...")
        
        # Disable inputs
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("Processing...")
        self.ventrata_input.setEnabled(False)
        self.monday_input.setEnabled(False)
        self.update_input.setEnabled(False)
        
        # Get file paths
        ventrata_file = self.ventrata_input.get_file_path()
        monday_file = self.monday_input.get_file_path()
        update_file = self.update_input.get_file_path()
        
        # Create and start worker thread
        self.worker = ExtractionWorker(ventrata_file, monday_file, update_file, output_dir)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.warning_added.connect(self._on_warning_added)
        self.worker.finished.connect(self._on_extraction_finished)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.start()
    
    def _on_progress_updated(self, step: str, state: str, details: str):
        """
        Handle progress updates from worker.
        
        Args:
            step: Step name
            state: State ('pending', 'loading', 'complete')
            details: Details text
        """
        # Update progress bar
        progress_map = {
            'import': 25,
            'merge': 50,
            'verify': 75,
            'export': 100
        }
        
        if state == 'loading':
            # Show loading state
            step_display = step.capitalize()
            self.progress_label.setText(f"Processing: {step_display}...")
        elif state == 'complete' and step in progress_map:
            self.progress_bar.setValue(progress_map[step])
            step_display = step.capitalize()
            self.progress_label.setText(f"✓ Completed: {step_display}")
    
    def _on_warning_added(self, warning: str):
        """
        Handle warning addition.
        
        Args:
            warning: Warning message
        """
        # Warnings are now handled in the completion message
        pass
    
    def _on_extraction_finished(self, success: bool, message: str, output_file: str):
        """
        Handle extraction completion.
        
        Args:
            success: Whether extraction succeeded
            message: Result message
            output_file: Path to output file
        """
        # Re-enable inputs
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("Extract")
        self.ventrata_input.setEnabled(True)
        self.monday_input.setEnabled(True)
        self.update_input.setEnabled(True)
        
        if success:
            self.output_file = output_file
            self.progress_bar.setValue(100)
            self.progress_label.setText(f"✓ Extraction complete!")
            
            # Show success dialog with option to open file
            reply = QMessageBox.question(
                self,
                "Extraction Complete",
                f"{message}\n\nWould you like to open the output file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._open_output_file(output_file)
            
            # Clear progress after a moment
            self.progress_bar.setValue(0)
            self.progress_label.setText(" ")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"✗ {message}")
            QMessageBox.critical(
                self,
                "Extraction Failed",
                f"Extraction failed:\n\n{message}"
            )
    
    def _on_error_occurred(self, error_message: str):
        """
        Handle error during extraction.
        
        Args:
            error_message: Error message
        """
        self.progress_label.setText(f"✗ Error: {error_message}")
    
    def _open_output_file(self, file_path: str):
        """
        Open the output file in default application.
        
        Args:
            file_path: Path to file
        """
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            elif platform.system() == 'Windows':
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Cannot Open File",
                f"Could not open file automatically:\n{str(e)}\n\nFile location: {file_path}"
            )
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self._is_processing():
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "Extraction is still in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Stop worker thread
                if self.worker:
                    self.worker.stop()
                    self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    # =========================================================================
    # UPDATE FUNCTIONALITY
    # =========================================================================
    
    def _check_for_updates_on_startup(self):
        """Check for updates when the app starts (in background)."""
        try:
            from utils.updater import check_for_updates_async, should_show_update
            
            def on_update_check_complete(available, version_info):
                if available and version_info and should_show_update(version_info):
                    # Store the update info and show dialog on main thread
                    self._pending_update_info = version_info
                    QTimer.singleShot(0, self._show_update_dialog)
            
            check_for_updates_async(on_update_check_complete)
            
        except ImportError as e:
            logger.warning(f"Could not import updater module: {e}")
        except Exception as e:
            logger.warning(f"Error checking for updates on startup: {e}")
    
    def _on_check_updates_clicked(self):
        """Handle click on 'Check for Updates' link."""
        try:
            from utils.updater import UpdateChecker, UpdateDialog, clear_skipped_version, APP_VERSION
            
            # Clear any skipped version when manually checking
            clear_skipped_version()
            
            # Show checking message
            self.update_link.setText("Checking...")
            self.update_link.setStyleSheet("""
                QLabel {
                    color: #6C757D;
                    font-size: 12px;
                }
            """)
            
            # Force UI update
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Check for updates
            checker = UpdateChecker()
            available, version, info = checker.check_for_updates()
            
            # Restore link style
            self.update_link.setText("Check for Updates")
            self.update_link.setStyleSheet("""
                QLabel {
                    color: #5B5FC7;
                    font-size: 12px;
                    text-decoration: underline;
                }
                QLabel:hover {
                    color: #4A4FB5;
                }
            """)
            
            if available is None:
                # Error checking for updates - show specific error message
                error_info = info if isinstance(info, dict) else {}
                error_type = error_info.get('type', 'unknown')
                error_message = error_info.get('message', 'Could not check for updates.')
                
                # Choose appropriate title based on error type
                if error_type == 'connection':
                    title = "No Connection"
                elif error_type == 'timeout':
                    title = "Connection Timeout"
                elif error_type == 'server':
                    title = "Server Unavailable"
                elif error_type == 'auth':
                    title = "Authentication Error"
                else:
                    title = "Update Check Failed"
                
                QMessageBox.warning(
                    self,
                    title,
                    error_message
                )
            elif available:
                # Update available - show dialog
                self._pending_update_info = info
                self._show_update_dialog()
            else:
                # No update available - user is on latest version
                QMessageBox.information(
                    self,
                    "You're Up to Date!",
                    f"You are running the latest version (v{APP_VERSION}).\n\nNo updates are available at this time."
                )
                
        except ImportError as e:
            logger.warning(f"Could not import updater module: {e}")
            QMessageBox.warning(
                self,
                "Update Check Failed",
                "Update functionality is not available.\n\nPlease install the 'requests' package."
            )
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            QMessageBox.warning(
                self,
                "Update Check Failed",
                f"An error occurred while checking for updates:\n\n{str(e)}"
            )
    
    def _show_update_dialog(self):
        """Show the update dialog with pending update info."""
        if not self._pending_update_info:
            return
        
        try:
            from utils.updater import UpdateDialog
            
            dialog = UpdateDialog(self, self._pending_update_info)
            dialog.exec()
            
            # Clear pending info after showing
            self._pending_update_info = None
            
        except Exception as e:
            logger.error(f"Error showing update dialog: {e}")

