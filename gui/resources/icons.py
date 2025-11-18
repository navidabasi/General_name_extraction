"""
SVG icons for the GUI application.

Loads SVG icons from local files in the resources directory.
"""

import os
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QSize


class Icons:
    """SVG icon resources loaded from local files."""
    
    # Get the directory where this file is located
    _resources_dir = Path(__file__).parent
    
    # Icon file mappings
    PAPERCLIP = _resources_dir / "attach_new.svg"
    LINK = _resources_dir / "link_new.svg"
    REFRESH = _resources_dir / "transfer.svg"
    DOWNLOAD = _resources_dir / "download_new.svg"
    CHECK = _resources_dir / "Tick_purple.svg"
    LOADING = _resources_dir / "loading_new.svg"
    
    # Red X icon (inline, no file available)
    CLOSE = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#DC3545" stroke-width="3">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
    '''
    
    # Warning icon (inline, no file available)
    WARNING = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFC107" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    '''
    
    @staticmethod
    def get_icon(icon_path_or_svg: str | Path, size: int = 24) -> QIcon:
        """
        Load icon from file or SVG string.
        
        Args:
            icon_path_or_svg: Path to SVG file or SVG string
            size: Icon size in pixels
            
        Returns:
            QIcon: Icon object
        """
        pixmap = Icons.get_pixmap(icon_path_or_svg, size)
        return QIcon(pixmap)
    
    @staticmethod
    def get_pixmap(icon_path_or_svg: str | Path, size: int = 24) -> QPixmap:
        """
        Load pixmap from file or SVG string.
        
        Args:
            icon_path_or_svg: Path to SVG file or SVG string
            size: Icon size in pixels
            
        Returns:
            QPixmap: Pixmap object
        """
        # Check if it's a Path object or string path
        if isinstance(icon_path_or_svg, Path) or (isinstance(icon_path_or_svg, str) and os.path.exists(str(icon_path_or_svg))):
            # Load from file
            file_path = str(icon_path_or_svg)
            renderer = QSvgRenderer(file_path)
        else:
            # Load from SVG string
            from PyQt6.QtCore import QByteArray
            svg_bytes = QByteArray(str(icon_path_or_svg).encode('utf-8'))
            renderer = QSvgRenderer(svg_bytes)
        
        if not renderer.isValid():
            # Return empty pixmap if invalid
            return QPixmap(QSize(size, size))
        
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(0x00000000)  # Transparent background
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return pixmap
