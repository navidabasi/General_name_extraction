"""
Status panel widget with progress tracking and collapsible warnings.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QPixmap, QMovie
from gui.resources.icons import Icons
from pathlib import Path


class StatusItem(QWidget):
    """Individual status item with icon and label."""
    
    def __init__(self, icon_svg: str, text: str):
        super().__init__()
        
        self.icon_svg = icon_svg
        self.text = text
        self.state = 'pending'  # pending, loading, complete
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI with card styling."""
        # Card style
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E9ECEF;
                padding: 12px;
            }
            QWidget:hover {
                border-color: #CED4DA;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setStyleSheet("background-color: transparent; border: none;")
        self.set_icon(self.icon_svg)
        layout.addWidget(self.icon_label)
        
        # Text
        self.text_label = QLabel(self.text)
        self.text_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
        self.text_label.setWordWrap(True)  # Allow text wrapping
        self.text_label.setStyleSheet("""
            font-size: 14px;
            color: #495057;
            background-color: transparent;
            border: none;
            line-height: 1.4;
        """)
        layout.addWidget(self.text_label)
        
        layout.addStretch()
        
        # Status icon (check, loading, etc.) - always visible to reserve space
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setStyleSheet("background-color: transparent; border: none;")
        layout.addWidget(self.status_icon)
        
        self.setLayout(layout)
        self.set_state('pending')
    
    def set_icon(self, icon_path_or_svg):
        """Set the main icon."""
        pixmap = Icons.get_pixmap(icon_path_or_svg, 24)
        self.icon_label.setPixmap(pixmap)
    
    def set_state(self, state: str, details: str = ""):
        """
        Set the state of this status item.
        
        Args:
            state: 'pending', 'loading', or 'complete'
            details: Optional details text
        """
        self.state = state
        
        if details:
            self.text_label.setText(f"{self.text}<br><span style='font-size: 11px; color: #6C757D; margin: 10px;'>{details}</span>")
        else:
            self.text_label.setText(self.text)
        
        if state == 'complete':
            pixmap = Icons.get_pixmap(Icons.CHECK, 20)
            self.status_icon.setPixmap(pixmap)
        elif state == 'loading':
            pixmap = Icons.get_pixmap(Icons.LOADING, 20)
            self.status_icon.setPixmap(pixmap)
        else:  # pending - clear but keep space reserved
            self.status_icon.clear()


class WarningsPanel(QWidget):
    """Collapsible warnings panel."""
    
    def __init__(self):
        super().__init__()
        
        self.is_expanded = False
        self.warnings = []
        
        self._init_ui()
        self.setVisible(False)  # Hidden by default
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (clickable to expand/collapse)
        self.header = QPushButton()
        self.header.setStyleSheet("""
            QPushButton {
                background-color: #FFF3CD;
                border: 1px solid #FFC107;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
                color: #856404;
            }
            QPushButton:hover {
                background-color: #FFE69C;
            }
        """)
        self.header.clicked.connect(self._toggle_expand)
        layout.addWidget(self.header)
        
        # Content area (warnings list)
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setMaximumHeight(0)  # Start collapsed
        self.content.setMinimumHeight(0)
        self.content.setStyleSheet("""
            QTextEdit {
                background-color: #FFF9E6;
                border: 1px solid #FFC107;
                border-top: none;
                border-radius: 0 0 6px 6px;
                padding: 8px 12px;
                font-size: 12px;
                color: #856404;
            }
        """)
        layout.addWidget(self.content)
        
        self.setLayout(layout)
    
    def set_warnings(self, warnings: list):
        """
        Set warnings to display.
        
        Args:
            warnings: List of warning message strings
        """
        self.warnings = warnings
        
        if not warnings:
            self.setVisible(False)
            return
        
        # Update header
        count = len(warnings)
        chevron = "▼" if self.is_expanded else "▶"
        self.header.setText(f"{chevron} ⚠ Warnings ({count})")
        
        # Update content
        content_html = "<ul style='margin: 0; padding-left: 20px;'>"
        for warning in warnings:
            content_html += f"<li>{warning}</li>"
        content_html += "</ul>"
        self.content.setHtml(content_html)
        
        self.setVisible(True)
    
    def _toggle_expand(self):
        """Toggle expanded/collapsed state."""
        self.is_expanded = not self.is_expanded
        
        # Update chevron
        count = len(self.warnings)
        chevron = "▼" if self.is_expanded else "▶"
        self.header.setText(f"{chevron} ⚠ Warnings ({count})")
        
        # Set content height safely
        if self.is_expanded:
            # Calculate content height safely
            try:
                doc_height = self.content.document().size().height()
                target_height = int(min(150, max(50, doc_height + 20)))
            except Exception:
                target_height = 100  # Fallback height
            self.content.setMaximumHeight(target_height)
            self.content.setMinimumHeight(0)
        else:
            self.content.setMaximumHeight(0)
            self.content.setMinimumHeight(0)


class StatusPanel(QWidget):
    """
    Status panel showing processing steps and warnings.
    """
    
    def __init__(self):
        super().__init__()
        
        self.status_items = {}
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI - no separate white card, integrated into right panel."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Status items (each as a card)
        self.status_items['import'] = StatusItem(Icons.PAPERCLIP, "Import Files")
        layout.addWidget(self.status_items['import'])
        
        self.status_items['merge'] = StatusItem(Icons.LINK, "Merge Lists")
        layout.addWidget(self.status_items['merge'])
        
        self.status_items['verify'] = StatusItem(Icons.REFRESH, "Verify Names")
        layout.addWidget(self.status_items['verify'])
        
        self.status_items['export'] = StatusItem(Icons.DOWNLOAD, "Export List")
        layout.addWidget(self.status_items['export'])
        
        # Warnings panel (collapsible) - will show above progress bar
        self.warnings_panel = WarningsPanel()
        self.warnings_panel.setVisible(False)  # Hidden by default
        layout.addWidget(self.warnings_panel)
        
        self.setLayout(layout)
    
    def set_status(self, step: str, state: str, details: str = ""):
        """
        Update status of a step.
        
        Args:
            step: Step name ('import', 'merge', 'verify', 'export')
            state: 'pending', 'loading', or 'complete'
            details: Optional details text
        """
        if step in self.status_items:
            self.status_items[step].set_state(state, details)
    
    def set_warnings(self, warnings: list):
        """
        Set warnings to display.
        
        Args:
            warnings: List of warning messages
        """
        self.warnings_panel.set_warnings(warnings)
    
    def reset(self):
        """Reset all status items to pending."""
        for item in self.status_items.values():
            item.set_state('pending')
        self.warnings_panel.set_warnings([])

