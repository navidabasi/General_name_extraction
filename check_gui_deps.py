"""
Quick dependency checker for GUI.

Run this to verify all GUI dependencies are installed correctly.
"""

import sys

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("=" * 60)
    print("NamesGen GUI - Dependency Checker")
    print("=" * 60)
    print()
    
    required = {
        'pandas': 'Data processing',
        'openpyxl': 'Excel file operations',
        'PyQt6': 'GUI framework',
        'PyQt6.QtSvg': 'SVG icon support'
    }
    
    all_installed = True
    
    for package, description in required.items():
        try:
            __import__(package.replace('.', '/').split('/')[0])
            print(f"✅ {package:20s} - {description}")
        except ImportError:
            print(f"❌ {package:20s} - {description} [MISSING]")
            all_installed = False
    
    print()
    print("=" * 60)
    
    if all_installed:
        print("✅ All dependencies installed!")
        print()
        print("Ready to launch GUI:")
        print("  python gui_app.py")
    else:
        print("❌ Missing dependencies!")
        print()
        print("Install with:")
        print("  pip install -r requirements.txt")
    
    print("=" * 60)
    
    return all_installed


if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)

