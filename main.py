"""
Spectrum Analyzer Application

Production-grade spectrum analysis with PySide6 GUI.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui import MainWindow
from utils import setup_logger


def main():
    """Main entry point."""
    # Set up logging
    log_file = Path("logs/spectrum_analyzer.log")
    setup_logger("spectrum_analyzer", log_file=log_file, level=20)  # INFO level
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Spectrum Analyzer")
    
    # Apply dark theme stylesheet
    stylesheet_path = Path("ui/styles/dark_theme.qss")
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r') as f:
            app.setStyleSheet(f.read())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
