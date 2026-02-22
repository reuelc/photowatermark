"""
drop_list.py — Shared drag-and-drop file list widget.
Imported by both main_window.py (Advanced Mode) and easy_panel.py (Easy Mode).
"""

import os
from PyQt5.QtWidgets import QListWidget, QAbstractItemView
from PyQt5.QtCore    import pyqtSignal

from core.image_processor import ImageProcessor


class DropListWidget(QListWidget):
    """QListWidget that accepts image files dragged from Windows Explorer."""

    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSpacing(2)
        self.setToolTip("Drag and drop image files or folders here")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if os.path.isfile(local) and ImageProcessor.is_supported(local):
                paths.append(local)
            elif os.path.isdir(local):
                for fname in os.listdir(local):
                    fp = os.path.join(local, fname)
                    if os.path.isfile(fp) and ImageProcessor.is_supported(fp):
                        paths.append(fp)
        if paths:
            self.files_dropped.emit(paths)
