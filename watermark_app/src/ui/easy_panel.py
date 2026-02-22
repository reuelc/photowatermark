"""
easy_panel.py — Simplified "Easy Mode" UI panel for PhotoWatermark Pro.

Designed for first-time or casual users who just want to:
  1. Drop photos in
  2. Type a watermark
  3. Click a button

All advanced options are available by switching to Advanced Mode via the toolbar.
"""

import io
import os

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QRadioButton, QButtonGroup,
    QFileDialog, QSizePolicy, QColorDialog, QMessageBox, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui  import QPixmap, QColor, QPainter, QBrush, QLinearGradient, QFont

from PIL import Image, ImageDraw

from core.constants        import (
    REALESTATE_PRESETS,
    POSITION_LOWER_RIGHT, POSITION_LOWER_LEFT,
    POSITION_CENTER,      POSITION_DIAGONAL,
    OUTPUT_DIR,
)
from core.watermark_engine import WatermarkEngine
from core.image_processor  import ImageProcessor

# Re-use the drag-and-drop list from main_window
from ui.drop_list import DropListWidget


# ──────────────────────────────────────────────────────────────────────────────

class EasyModePanel(QWidget):
    """
    One-screen simplified interface.

    Signals
    -------
    process_requested(list, dict)   : user clicked Watermark — carries (files, config)
    files_changed(list)             : file list was updated (for syncing with Advanced)
    """

    process_requested = pyqtSignal(list, dict)
    files_changed     = pyqtSignal(list)

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self, engine: WatermarkEngine, processor: ImageProcessor):
        super().__init__()
        self.engine    = engine
        self.processor = processor
        self._color    = "#FFFFFF"
        self.files     = []

        self._build_ui()
        self._apply_styles()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        root.addWidget(self._build_file_column(),     0)   # fixed width
        root.addWidget(self._build_settings_column(), 1)   # stretches
        root.addWidget(self._build_preview_column(),  0)   # fixed width

    # ── Column 1: File Drop ───────────────────────────────────────────────────

    def _build_file_column(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(260)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        hdr = QLabel("① Add Your Photos")
        hdr.setObjectName("step_header")
        v.addWidget(hdr)

        hint = QLabel("Drag & drop images here\nor click Add Images below")
        hint.setAlignment(Qt.AlignCenter)
        hint.setObjectName("hint_label")
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.file_list = DropListWidget()
        self.file_list.files_dropped.connect(self._on_dropped)
        self.file_list.itemSelectionChanged.connect(self._schedule_preview)
        v.addWidget(self.file_list, 1)

        self.lbl_count = QLabel("0 files added")
        self.lbl_count.setAlignment(Qt.AlignCenter)
        self.lbl_count.setObjectName("count_label")
        v.addWidget(self.lbl_count)

        btn_add = QPushButton("＋  Add Images")
        btn_add.setObjectName("add_btn")
        btn_add.clicked.connect(self._browse_files)
        v.addWidget(btn_add)

        btn_clear = QPushButton("✕  Clear List")
        btn_clear.clicked.connect(self._clear_files)
        v.addWidget(btn_clear)

        return w

    # ── Column 2: Settings ────────────────────────────────────────────────────

    def _build_settings_column(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # ── Section header
        hdr = QLabel("② Set Your Watermark")
        hdr.setObjectName("step_header")
        v.addWidget(hdr)

        # ── Form controls
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Watermark text
        self.txt_text = QLineEdit()
        self.txt_text.setPlaceholderText("e.g.  © My Brand  |  Your Name  |  CONFIDENTIAL")
        self.txt_text.setObjectName("easy_text")
        form.addRow("Watermark Text:", self.txt_text)

        # Font size
        self.sld_size    = self._make_slider(12, 120, 36)
        self.lbl_size_v  = QLabel("36 pt")
        self.lbl_size_v.setFixedWidth(48)
        self.sld_size.valueChanged.connect(lambda v: self.lbl_size_v.setText(f"{v} pt"))
        form.addRow("Font Size:", self._hrow(self.sld_size, self.lbl_size_v))

        # Opacity
        self.sld_opacity   = self._make_slider(10, 100, 60)
        self.lbl_opacity_v = QLabel("60%")
        self.lbl_opacity_v.setFixedWidth(48)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity_v.setText(f"{v}%"))
        form.addRow("Opacity:", self._hrow(self.sld_opacity, self.lbl_opacity_v))

        # Colour
        clr_h = QHBoxLayout()
        self.btn_color  = QPushButton("🎨  Pick Colour")
        self.lbl_swatch = QLabel()
        self.lbl_swatch.setFixedSize(40, 24)
        self.lbl_swatch.setObjectName("easy_swatch")
        self._refresh_swatch()
        clr_h.addWidget(self.btn_color)
        clr_h.addWidget(self.lbl_swatch)
        clr_h.addStretch()
        form.addRow("Colour:", self._wrap(clr_h))
        self.btn_color.clicked.connect(self._pick_color)

        # Position
        pos_h = QHBoxLayout()
        pos_h.setSpacing(12)
        self._pos_group = QButtonGroup(self)
        self._pos_btns  = {}
        for label, key in [
            ("Lower Right", POSITION_LOWER_RIGHT),
            ("Lower Left",  POSITION_LOWER_LEFT),
            ("Center",       POSITION_CENTER),
            ("Diagonal",     POSITION_DIAGONAL),
        ]:
            rb = QRadioButton(label)
            self._pos_group.addButton(rb)
            pos_h.addWidget(rb)
            self._pos_btns[key] = rb
        self._pos_btns[POSITION_LOWER_RIGHT].setChecked(True)
        form.addRow("Position:", self._wrap(pos_h))

        v.addLayout(form)

        # ── Divider
        v.addWidget(self._divider())

        # ── Quick presets
        preset_hdr = QLabel("⚡  Quick Presets  — one click to apply a full style")
        preset_hdr.setObjectName("step_header")
        v.addWidget(preset_hdr)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        quick = [
            ("Subtle",       "Subtle Floor Style"),
            ("Professional", "Corner Professional"),
            ("Center Promo", "Center Promo"),
            ("SOLD",         "SOLD Badge Mode"),
            ("NEW LISTING",  "NEW LISTING Badge Mode"),
        ]
        for short, full in quick:
            btn = QPushButton(short)
            btn.setObjectName("easy_preset_btn")
            btn.clicked.connect(lambda _, n=full: self._apply_preset(n))
            presets_row.addWidget(btn)
        v.addLayout(presets_row)

        # ── Divider
        v.addWidget(self._divider())
        v.addStretch()

        # ── Action buttons
        self.btn_demo = QPushButton("⚡  Quick Start Demo  (no files needed)")
        self.btn_demo.setObjectName("demo_btn")
        self.btn_demo.setToolTip(
            "Generates a sample image so you can see your watermark style instantly"
        )
        self.btn_demo.clicked.connect(self._quick_start_demo)
        v.addWidget(self.btn_demo)

        self.btn_process = QPushButton("▶   Watermark All Files")
        self.btn_process.setObjectName("primary_btn")
        self.btn_process.clicked.connect(self._on_process)
        v.addWidget(self.btn_process)

        # ── Wire live preview
        for widget in (self.txt_text,):
            widget.textChanged.connect(self._schedule_preview)
        for s in (self.sld_size, self.sld_opacity):
            s.valueChanged.connect(self._schedule_preview)
        for rb in self._pos_btns.values():
            rb.toggled.connect(self._schedule_preview)

        return w

    # ── Column 3: Preview ─────────────────────────────────────────────────────

    def _build_preview_column(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(300)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        hdr = QLabel("③ Preview")
        hdr.setObjectName("step_header")
        v.addWidget(hdr)

        self.lbl_preview = QLabel(
            "Select a file in the list\nor click ⚡ Quick Start Demo"
        )
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setObjectName("easy_preview")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(self.lbl_preview, 1)

        self.lbl_preview_meta = QLabel("")
        self.lbl_preview_meta.setAlignment(Qt.AlignCenter)
        self.lbl_preview_meta.setObjectName("count_label")
        v.addWidget(self.lbl_preview_meta)

        btn_refresh = QPushButton("🔄  Refresh Preview")
        btn_refresh.clicked.connect(self._update_preview)
        v.addWidget(btn_refresh)

        return w

    # ──────────────────────── File management ─────────────────────────────────

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        )
        self._add_paths(paths)

    def _on_dropped(self, paths: list):
        self._add_paths(paths)

    def _add_paths(self, paths: list):
        existing = set(self.files)
        for p in paths:
            if p not in existing:
                self.files.append(p)
                self.file_list.addItem(os.path.basename(p))
        self._update_count()
        self.files_changed.emit(self.files)

    def _clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self._update_count()
        self.lbl_preview.setText(
            "Select a file in the list\nor click ⚡ Quick Start Demo"
        )
        self.lbl_preview_meta.clear()
        self.files_changed.emit(self.files)

    def _update_count(self):
        n = len(self.files)
        self.lbl_count.setText(f"{n} file{'s' if n != 1 else ''} added")

    def sync_files(self, files: list):
        """Called by MainWindow when syncing files from Advanced → Easy."""
        self.files = list(files)
        self.file_list.clear()
        for p in self.files:
            self.file_list.addItem(os.path.basename(p))
        self._update_count()

    # ──────────────────────── Config ──────────────────────────────────────────

    def get_config(self) -> dict:
        """Build and return a config dict from the easy mode widgets."""
        position = POSITION_LOWER_RIGHT
        for key, rb in self._pos_btns.items():
            if rb.isChecked():
                position = key
                break
        return {
            "text_line1":     self.txt_text.text(),
            "text_line2":     "",
            "text_line3":     "",
            "font_name":      "Arial",
            "font_size":      self.sld_size.value(),
            "color":          self._color,
            "opacity":        self.sld_opacity.value(),
            "line_spacing":   1.2,
            "position":       position,
            "margin":         20,
            "shadow":         True,
            "outline":        False,
            "re_agent_name":  "",
            "re_license":     "",
            "re_contact":     "",
            "re_date_stamp":  False,
            "logo_path":      "",
            "logo_size":      20,
            "logo_position":  POSITION_LOWER_LEFT,
            "output_format":  "JPG",
            "quality":        90,
            "resize_enabled": False,
            "resize_width":   1920,
            "resize_height":  1080,
            "smart_opacity":  False,
            "prefix":         "",
            "suffix":         "_watermarked",
        }

    def apply_config(self, config: dict):
        """Push an advanced config dict into the easy mode widgets."""
        self.txt_text.setText(config.get("text_line1", ""))
        self.sld_size.setValue(config.get("font_size", 36))
        self.sld_opacity.setValue(config.get("opacity", 60))
        self._color = config.get("color", "#FFFFFF")
        self._refresh_swatch()
        pos = config.get("position", POSITION_LOWER_RIGHT)
        if pos in self._pos_btns:
            self._pos_btns[pos].setChecked(True)

    # ──────────────────────── Quick presets ───────────────────────────────────

    def _apply_preset(self, name: str):
        preset = REALESTATE_PRESETS.get(name, {})
        if "font_size"  in preset: self.sld_size.setValue(preset["font_size"])
        if "opacity"    in preset: self.sld_opacity.setValue(preset["opacity"])
        if "color"      in preset:
            self._color = preset["color"]
            self._refresh_swatch()
        if "position"   in preset:
            key = preset["position"]
            if key in self._pos_btns:
                self._pos_btns[key].setChecked(True)
        if "badge_text" in preset:
            self.txt_text.setText(preset["badge_text"])
        self._schedule_preview()

    # ──────────────────────── Quick Start Demo ────────────────────────────────

    def _quick_start_demo(self):
        """
        Generate a synthetic 'property photo' and apply the current watermark.
        No real images needed — great for first-time users.
        """
        # Build a 900×600 gradient image that looks like a sky + ground
        img = Image.new("RGB", (900, 600))
        for y in range(600):
            # Sky gradient (top): deep blue → light blue
            if y < 350:
                ratio = y / 350
                r = int(30  + ratio * 120)
                g = int(100 + ratio * 100)
                b = int(200 + ratio * 55)
            else:
                # Ground gradient (bottom): green → darker green
                ratio = (y - 350) / 250
                r = int(60  - ratio * 20)
                g = int(140 - ratio * 40)
                b = int(60  - ratio * 20)
            for x in range(900):
                img.putpixel((x, y), (r, g, b))

        d = ImageDraw.Draw(img)
        # Simple house silhouette
        d.rectangle([300, 280, 600, 450], fill=(210, 190, 160))   # walls
        d.polygon(  [(270, 280), (630, 280), (450, 150)], fill=(150, 80, 60))  # roof
        d.rectangle([390, 350, 480, 450], fill=(100, 70, 50))     # door
        d.rectangle([310, 320, 370, 370], fill=(180, 220, 240))   # window L
        d.rectangle([530, 320, 590, 370], fill=(180, 220, 240))   # window R
        d.rectangle([0,   440, 900, 600], fill=(70, 130, 60))     # lawn

        # Apply current watermark
        config = self.get_config()
        if not config["text_line1"].strip():
            config["text_line1"] = "Your Watermark Here"

        result = self.engine.process(img.convert("RGBA"), config)

        # Show in preview
        self._display_pil_image(result, "Demo  900 × 600")

        # Save demo file
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        demo_path = os.path.join(OUTPUT_DIR, "quick_start_demo.jpg")
        ImageProcessor.save(result, demo_path, "JPG", 90)

        QMessageBox.information(
            self, "Quick Start Demo",
            "A sample watermarked image has been saved to:\n\n"
            f"{demo_path}\n\n"
            "This shows exactly how your watermark will look on real photos.\n"
            "Adjust the settings and click again to update the demo!"
        )

    # ──────────────────────── Process ─────────────────────────────────────────

    def _on_process(self):
        if not self.files:
            QMessageBox.warning(
                self, "No Files",
                "Please add some images first.\n\n"
                "Tip: Drag and drop a folder of photos onto the list!"
            )
            return
        self.process_requested.emit(self.files, self.get_config())

    # ──────────────────────── Preview ─────────────────────────────────────────

    def _schedule_preview(self, *_args):
        if not hasattr(self, "_timer"):
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._update_preview)
        self._timer.start(400)

    def _update_preview(self):
        selected = self.file_list.selectedItems()
        if not selected or not self.files:
            return
        row  = self.file_list.row(selected[0])
        if row >= len(self.files):
            return
        path = self.files[row]
        try:
            image = self.processor.load(path)
            orig_w, orig_h = image.size

            thumb = image.copy()
            thumb.thumbnail((480, 340), Image.LANCZOS)
            tw = thumb.width

            scale  = tw / max(orig_w, 1)
            p_cfg  = dict(self.get_config())
            p_cfg["font_size"] = max(6, int(p_cfg["font_size"] * scale))
            p_cfg["margin"]    = max(2, int(p_cfg["margin"]    * scale))

            result = self.engine.process(thumb, p_cfg)
            self._display_pil_image(result, f"{orig_w}×{orig_h}  •  {os.path.basename(path)}")
        except Exception as exc:
            self.lbl_preview.setText(f"Preview error:\n{exc}")

    def _display_pil_image(self, pil_img: Image.Image, meta: str = ""):
        buf = io.BytesIO()
        fmt = "PNG" if pil_img.mode == "RGBA" else "JPEG"
        pil_img.save(buf, format=fmt)
        buf.seek(0)
        pix = QPixmap()
        pix.loadFromData(buf.read())
        scaled = pix.scaled(
            self.lbl_preview.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lbl_preview.setPixmap(scaled)
        if meta:
            self.lbl_preview_meta.setText(meta)

    # ──────────────────────── Colour ──────────────────────────────────────────

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self, "Watermark Colour")
        if color.isValid():
            self._color = color.name()
            self._refresh_swatch()
            self._schedule_preview()

    def _refresh_swatch(self):
        self.lbl_swatch.setStyleSheet(
            f"background:{self._color}; border:1px solid #94A3B8; border-radius:3px;"
        )

    # ──────────────────────── UI helpers ──────────────────────────────────────

    @staticmethod
    def _make_slider(lo, hi, val) -> QSlider:
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    @staticmethod
    def _hrow(slider, label) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(slider, 1)
        h.addWidget(label)
        return w

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)
        return w

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("divider")
        return line

    # ──────────────────────── Stylesheet ──────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            #step_header {
                font-size: 14px;
                font-weight: bold;
                color: #1E293B;
                padding-bottom: 4px;
            }
            #hint_label {
                color: #94A3B8;
                font-size: 12px;
                background: #F8FAFC;
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
                padding: 10px;
            }
            #count_label {
                color: #64748B;
                font-size: 12px;
            }
            #add_btn {
                background: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                padding: 8px;
                font-weight: bold;
                border-radius: 5px;
            }
            #add_btn:hover { background: #DBEAFE; }
            #easy_text {
                font-size: 14px;
                padding: 8px 12px;
                border: 2px solid #CBD5E1;
                border-radius: 6px;
                min-height: 36px;
            }
            #easy_text:focus { border-color: #93C5FD; }
            #easy_swatch {
                border: 1px solid #94A3B8;
                border-radius: 3px;
            }
            #easy_preset_btn {
                background: #F0FDF4;
                color: #166534;
                border: 1px solid #BBF7D0;
                padding: 8px 6px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            #easy_preset_btn:hover { background: #DCFCE7; }
            #demo_btn {
                background: #FFFBEB;
                color: #92400E;
                border: 1px solid #FDE68A;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            #demo_btn:hover { background: #FEF3C7; }
            #primary_btn {
                background: #2563EB;
                color: white;
                border: none;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            #primary_btn:hover  { background: #1D4ED8; }
            #primary_btn:pressed{ background: #1E40AF; }
            #easy_preview {
                background: #0F172A;
                border-radius: 8px;
                color: #475569;
                font-size: 13px;
            }
            #divider { color: #E2E8F0; }
            QSlider::groove:horizontal {
                height: 5px;
                background: #CBD5E1;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2563EB;
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #93C5FD;
                border-radius: 3px;
            }
        """)
