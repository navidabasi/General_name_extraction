"""
Custom file input widget with validation and clear functionality.
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QPushButton,
                              QLabel, QVBoxLayout, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from gui.resources.icons import Icons


class FileInputWidget(QWidget):
    """
    Custom file input widget.
    
    Features:
    - Placeholder text "No file selected"
    - Browse button
    - Red X button to clear selection
    - Shows only filename (not full path)
    - File validation with visual indicators
    - Optional/Required labeling
    """
    
    file_selected = pyqtSignal(str)  # Emitted when file is selected
    file_cleared = pyqtSignal()  # Emitted when file is cleared
    
    def __init__(self, label_text: str, required: bool = False, 
                 file_filter: str = "Excel Files (*.xlsx)"):
        """
        Initialize file input widget.
        
        Args:
            label_text: Label text (e.g., "Ventrata File")
            required: Whether file is required
            file_filter: File dialog filter
        """
        super().__init__()
        
        self.label_text = label_text
        self.required = required
        self.file_filter = file_filter
        self.file_path = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Label (only show Required badge, no Optional)
        label_layout = QHBoxLayout()
        label_layout.setSpacing(8)
        
        self.label = QLabel(self.label_text)
        self.label.setStyleSheet("font-size: 14px; font-weight: 500; color: #212529;")
        label_layout.addWidget(self.label)
        
        # Required badge (only if required)
        if self.required:
            badge = QLabel("Required")
            badge.setStyleSheet("""
                font-size: 11px;
                color: #DC3545;
                padding: 2px 6px;
                background-color: #FFE5E5;
                border-radius: 4px;
            """)
            label_layout.addWidget(badge)
        
        label_layout.addStretch()
        
        layout.addLayout(label_layout)
        
        # Card container for input row
        card_container = QWidget()
        card_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E9ECEF;
            }
        """)
        
        # Input row with textbox, validation icon, and buttons
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Text input
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("No file selected")
        self.file_input.setReadOnly(True)
        self.file_input.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: none;
                background-color: transparent;
                font-size: 13px;
                color: #495057;
            }
            QLineEdit::placeholder {
                color: #ADB5BD;
            }
        """)
        input_layout.addWidget(self.file_input, stretch=1)
        
        # Validation icon removed - just show filename
        
        # Clear button (text)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(24)
        self.clear_btn.setToolTip("Clear selection")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 4px;
                background-color: transparent;
                color: #ADB5BD;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #DC3545;
                background-color: rgba(220, 53, 69, 0.08);
            }
            QPushButton:pressed {
                color: #B02A37;
                background-color: rgba(220, 53, 69, 0.15);
            }
        """)
        self.clear_btn.clicked.connect(self._clear_file)
        self.clear_btn.setVisible(False)
        input_layout.addWidget(self.clear_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # Browse button
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedHeight(30)
        self.browse_btn.setMinimumWidth(90)
        self.browse_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Ensure focus works on Windows
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B5FC7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4A4FB5;
            }
            QPushButton:pressed {
                background-color: #3A3F95;
            }
            QPushButton:disabled {
                background-color: #ADB5BD;
            }
        """)
        self.browse_btn.clicked.connect(self._browse_file)
        input_layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        card_container.setLayout(input_layout)
        layout.addWidget(card_container)
        
        # Error message label (hidden by default)
        self.error_label = QLabel()  
        self.error_label.setStyleSheet("""
            color: #DC3545;
            font-size: 12px;
            padding-left: 4px;
        """)
        self.error_label.setWordWrap(True)  # Allow text wrapping
        self.error_label.setMinimumHeight(20)  # Ensure minimum height
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        self.setLayout(layout)
    
    def _browse_file(self):
        """Open file browser dialog."""
        # Ensure parent widget is properly set for Windows
        parent = self.window() if self.window() else self
        
        file_path, _ = QFileDialog.getOpenFileName(
            parent,  # Use window as parent for proper Windows dialog
            f"Select {self.label_text}",
            "",  # Start in current directory
            self.file_filter
        )
        
        if file_path:
            self.set_file(file_path)
    
    def set_file(self, file_path: str):
        """
        Set the selected file.
        
        Args:
            file_path: Full path to the file
        """
        if not file_path or not os.path.exists(file_path):
            self._show_error("File not found")
            return
        
        # Validate file extension
        if not file_path.endswith('.xlsx'):
            self._show_error("Must be .xlsx file")
            return
        
        self.file_path = file_path
        
        # Show only filename (not full path)
        filename = Path(file_path).name
        self.file_input.setText(filename)
        self.file_input.setToolTip(file_path)  # Full path in tooltip
        
        # Show clear button
        self.clear_btn.setVisible(True)
        self.error_label.setVisible(False)
        
        # Emit signal
        self.file_selected.emit(file_path)
    
    def _clear_file(self):
        """Clear the selected file."""
        self.file_path = None
        self.file_input.clear()
        self.file_input.setToolTip("")
        self.clear_btn.setVisible(False)
        self.error_label.setVisible(False)
        
        # Emit signal
        self.file_cleared.emit()
    
    def _show_error(self, message: str):
        """
        Show error message.
        
        Args:
            message: Error message text
        """
        self.error_label.setText(f"⚠ {message}")
        self.error_label.setVisible(True)
        # Force update to ensure visibility on Windows
        self.error_label.update()
        self.update()
    
    def get_file_path(self) -> str:
        """
        Get the selected file path.
        
        Returns:
            str: Full file path or None if no file selected
        """
        return self.file_path
    
    def has_file(self) -> bool:
        """
        Check if file is selected.
        
        Returns:
            bool: True if file is selected
        """
        return self.file_path is not None
    
    def clear(self):
        """Clear the file selection."""
        self._clear_file()
    
    def setEnabled(self, enabled: bool):
        """Enable or disable the widget."""
        super().setEnabled(enabled)
        self.file_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        # Update visual state
        if not enabled:
            self.browse_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ADB5BD;
                    color: #6C757D;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
            """)
        else:
            self.browse_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5B5FC7;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #4A4FB5;
                }
                QPushButton:pressed {
                    background-color: #3A3F95;
                }
                QPushButton:disabled {
                    background-color: #ADB5BD;
                }
            """)

