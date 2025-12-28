"""
Custom file input widget with validation and clear functionality.
"""

import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QPushButton,
                              QLabel, QVBoxLayout, QFileDialog, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont
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
        self.label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #212529;
                background-color: transparent;
            }
        """)
        label_layout.addWidget(self.label)
        
        # Required badge (only if required)
        if self.required:
            self.badge = QLabel("Required")
            self.badge.setFixedHeight(20)
            self.badge.setStyleSheet("""
                QLabel {
                font-size: 11px;
                color: #DC3545;
                padding: 2px 6px;
                background-color: #FFE5E5;
                    border: 1px solid #FFCCCC;
                border-radius: 4px;
                }
            """)
            label_layout.addWidget(self.badge)
        
        label_layout.addStretch()
        
        layout.addLayout(label_layout)
        
        # Card container for input row
        card_container = QWidget()
        card_container.setObjectName("cardContainer")
        card_container.setStyleSheet("""
            QWidget#cardContainer {
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
        self.file_input.setMinimumHeight(28)
        self.file_input.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                background-color: #F8F9FA;
                font-size: 13px;
                color: #495057;
            }
        """)
        input_layout.addWidget(self.file_input, stretch=1)
        
        # Validation icon removed - just show filename
        
        # Clear button (text)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedSize(60, 28)
        self.clear_btn.setToolTip("Clear selection")
        self.clear_btn.setFlat(True)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                background-color: #F8F9FA;
                color: #6C757D;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #DC3545;
                background-color: #FFE5E5;
                border-color: #DC3545;
            }
            QPushButton:pressed {
                color: #B02A37;
                background-color: #FFCCCC;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_file)
        self.clear_btn.setVisible(False)
        input_layout.addWidget(self.clear_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # Browse button
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedSize(90, 30)
        self.browse_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_browse_btn_style(enabled=True)
        self.browse_btn.clicked.connect(self._browse_file)
        input_layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        card_container.setLayout(input_layout)
        layout.addWidget(card_container)
        
        # Error message label (hidden by default)
        self.error_label = QLabel()  
        self.error_label.setStyleSheet("""
            QLabel {
            color: #DC3545;
            font-size: 12px;
            padding-left: 4px;
                background-color: transparent;
            }
        """)
        self.error_label.setWordWrap(True)  # Allow text wrapping
        self.error_label.setMinimumHeight(20)  # Ensure minimum height
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        self.setLayout(layout)
    
    def _apply_browse_btn_style(self, enabled: bool = True):
        """Apply style to browse button based on enabled state."""
        if enabled:
            self.browse_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5B5FC7;
                    color: white;
                    border: 2px solid #5B5FC7;
                    border-radius: 6px;
                    padding: 6px 12px;
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
            """)
        else:
            self.browse_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ADB5BD;
                    color: #6C757D;
                    border: 2px solid #ADB5BD;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
    
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
        self._apply_browse_btn_style(enabled)

