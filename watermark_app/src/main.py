"""
main.py — Entry point for PhotoWatermark Pro.

Run:
    python src/main.py

Package as .exe:
    See build.bat / README.md for PyInstaller instructions.
"""

import sys
import os

# Ensure the /src directory is on sys.path so relative imports resolve
# correctly whether the app is run directly or via PyInstaller.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QFont

from ui.main_window  import MainWindow
from core.constants  import APP_NAME, OUTPUT_DIR


def main():
    # ── High-DPI support (must be set before QApplication is created) ─────────
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)

    # Use Segoe UI as the default font on Windows (clean, modern look)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Ensure the default output directory exists before the window opens
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
