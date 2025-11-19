"""
Main application window for NamesGen GUI.
"""

import os
import sys
import platform
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QProgressBar, QFileDialog,
                              QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from gui.widgets import FileInputWidget
from gui.worker import ExtractionWorker


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.worker = None
        self.output_file = None
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Name Extractor")
        self.setMinimumSize(QSize(520, 520))
        self.setFixedSize(QSize(520, 520))  # Not resizable
        
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
        
        # Apply global stylesheet with card design
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F0F2F5;
            }
            QWidget {
                background-color: transparent;
            }
        """)
    
    def _create_main_panel(self) -> QWidget:
        """Create the main panel with file inputs and progress bar."""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Name Extractor")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: #212529;
        """)
        layout.addWidget(title)
        
        # File inputs with card design
        self.ventrata_input = FileInputWidget("Ventrata File", required=True)
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
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover:enabled {
                background-color: #4A4FB5;
            }
            QPushButton:pressed {
                background-color: #3A3F95;
            }
            QPushButton:disabled {
                background-color: #ADB5BD;
                color: #6C757D;
            }
        """)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        button_container.addWidget(self.extract_btn)
        
        button_container.addStretch()
        layout.addLayout(button_container)
        
        # Progress section (under Extract button)
        layout.addSpacing(16)
        
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
            font-size: 12px;
            color: #6C757D;
            padding-left: 4px;
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
        
        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
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

