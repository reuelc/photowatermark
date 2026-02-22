"""
main_window.py — PyQt5 desktop UI for PhotoWatermark Pro.

Layout (three-panel splitter):
  ┌─────────────┬──────────────────────┬───────────────┐
  │  File List  │   Settings (Tabs)    │    Preview    │
  │  (drag+drop)│                      │               │
  └─────────────┴──────────────────────┴───────────────┘

Architecture notes
──────────────────
• All image processing happens in BatchWorker (QThread) so the UI never freezes.
• Config is collected via _collect_config() → plain dict → passed to the engine.
  This same dict can be serialised to JSON for an API request body.
• The engine/processor are completely independent of Qt.
"""

import io
import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QLabel, QPushButton, QLineEdit, QSpinBox, QSlider, QCheckBox,
    QComboBox, QRadioButton, QButtonGroup, QListWidget, QAbstractItemView,
    QTabWidget, QScrollArea, QProgressBar, QFileDialog, QMessageBox,
    QColorDialog, QSizePolicy, QApplication,
)
from PyQt5.QtCore  import Qt, QThread, pyqtSignal, QTimer, QUrl, QRect
from PyQt5.QtGui   import QPixmap, QPainter, QBrush, QColor, QPen, QFont, QIcon

from PIL import Image

from core.constants      import (
    APP_NAME, APP_VERSION, OUTPUT_DIR,
    POSITION_LABELS, POSITION_LOWER_LEFT, POSITION_LOWER_RIGHT,
    POSITION_CENTER, POSITION_DIAGONAL,
    FONT_NAMES, OUTPUT_FORMATS, REALESTATE_PRESETS,
)
from core.watermark_engine import WatermarkEngine
from core.image_processor  import ImageProcessor
from core.profile_manager  import ProfileManager


# ──────────────────────────────────────────────────────────────────────────────
#  Background worker — runs batch processing off the main thread
# ──────────────────────────────────────────────────────────────────────────────

class BatchWorker(QThread):
    """
    Processes a list of image files in the background.

    Signals
    -------
    progress(int)            : overall completion percentage 0-100
    file_done(str, bool)     : filename + success flag per file
    log_message(str)         : one-liner status update per file
    finished(int, int)       : total done + total failed counts
    """

    progress    = pyqtSignal(int)
    file_done   = pyqtSignal(str, bool)
    log_message = pyqtSignal(str)
    finished    = pyqtSignal(int, int)

    def __init__(self, file_list: list, config: dict, output_dir: str):
        super().__init__()
        self.file_list  = file_list
        self.config     = config
        self.output_dir = output_dir
        self._abort     = False

    def abort(self):
        """Signal the worker to stop after the current image."""
        self._abort = True

    def run(self):
        engine    = WatermarkEngine()
        processor = ImageProcessor()
        total     = len(self.file_list)
        done      = 0
        failed    = 0

        for i, path in enumerate(self.file_list):
            if self._abort:
                self.log_message.emit("⏹ Batch aborted by user.")
                break

            try:
                # Load
                image = processor.load(path)

                # Optional pre-resize
                if self.config.get("resize_enabled", False):
                    image = processor.resize(
                        image,
                        self.config.get("resize_width",  1920),
                        self.config.get("resize_height", 1080),
                    )

                # Watermark
                result = engine.process(image, self.config)

                # Build output path and save
                fmt      = self.config.get("output_format", "JPG")
                prefix   = self.config.get("prefix", "")
                suffix   = self.config.get("suffix", "_watermarked")
                out_path = processor.build_output_path(
                    path, self.output_dir, prefix, suffix, fmt
                )
                processor.save(result, out_path, fmt, self.config.get("quality", 90))

                self.log_message.emit(f"✓  {os.path.basename(path)}")
                self.file_done.emit(os.path.basename(path), True)
                done += 1

            except Exception as exc:
                msg = f"✗  {os.path.basename(path)}: {exc}"
                self.log_message.emit(msg)
                self.file_done.emit(os.path.basename(path), False)
                failed += 1

            self.progress.emit(int((i + 1) / total * 100))

        self.finished.emit(done, failed)


# ──────────────────────────────────────────────────────────────────────────────
#  Drag-and-drop-enabled file list
# ──────────────────────────────────────────────────────────────────────────────

class DropListWidget(QListWidget):
    """QListWidget that accepts image files dropped from Explorer."""

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
                # Accept entire folders
                for fname in os.listdir(local):
                    fp = os.path.join(local, fname)
                    if os.path.isfile(fp) and ImageProcessor.is_supported(fp):
                        paths.append(fp)
        if paths:
            self.files_dropped.emit(paths)


# ──────────────────────────────────────────────────────────────────────────────
#  Main window
# ──────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Top-level application window.

    Responsibilities:
      • Build and own the entire widget tree.
      • Translate UI state → config dict → engine calls.
      • Manage the batch worker lifecycle.
      • Persist settings on close via ProfileManager.
    """

    def __init__(self):
        super().__init__()

        # Core services
        self.engine     = WatermarkEngine()
        self.processor  = ImageProcessor()
        self.profiles   = ProfileManager()

        # State
        self.files      = []           # Absolute paths of queued images
        self.worker     = None         # Active BatchWorker (or None)
        self.output_dir = OUTPUT_DIR
        self._color     = "#FFFFFF"    # Currently selected watermark colour

        # Load last-used config
        self.config = self.profiles.load_last_used()
        self._color = self.config.get("color", "#FFFFFF")

        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.setMinimumSize(1280, 820)
        self.setWindowIcon(self._make_icon())

        self._build_ui()
        self._apply_stylesheet()
        self._load_config_to_ui()

    # ──────────────────────── App icon (programmatic) ─────────────────────────

    def _make_icon(self) -> QIcon:
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor("#2563EB")))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 32, 32, 6, 6)
        p.setPen(QPen(QColor("white"), 2))
        p.setFont(QFont("Arial", 16, QFont.Bold))
        p.drawText(QRect(0, 0, 32, 32), Qt.AlignCenter, "W")
        p.end()
        return QIcon(px)

    # ──────────────────────── Widget tree ─────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        splitter.addWidget(self._build_file_panel())
        splitter.addWidget(self._build_settings_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.setSizes([240, 540, 360])
        root.addWidget(splitter, 1)

        root.addWidget(self._build_status_bar())

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("toolbar")
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 6, 10, 6)

        title = QLabel(APP_NAME)
        title.setObjectName("app_title")
        h.addWidget(title)
        h.addStretch()

        self.btn_add     = QPushButton("＋  Add Files")
        self.btn_clear   = QPushButton("✕  Clear All")
        self.btn_openout = QPushButton("📂  Open Output")
        self.btn_preview = QPushButton("👁  Preview")
        self.btn_process = QPushButton("▶  Batch Watermark")
        self.btn_process.setObjectName("primary_btn")

        for btn in (self.btn_add, self.btn_clear, self.btn_openout,
                    self.btn_preview, self.btn_process):
            h.addWidget(btn)

        self.btn_add.clicked.connect(self._add_files_dialog)
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_openout.clicked.connect(self._open_output_folder)
        self.btn_preview.clicked.connect(self._update_preview)
        self.btn_process.clicked.connect(self._start_batch)
        return w

    # ── File panel ────────────────────────────────────────────────────────────

    def _build_file_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 4, 0)
        v.setSpacing(4)

        lbl = QLabel("📁  Files  (drag & drop here)")
        lbl.setObjectName("panel_label")
        v.addWidget(lbl)

        self.file_list = DropListWidget()
        self.file_list.files_dropped.connect(self._on_files_dropped)
        self.file_list.itemSelectionChanged.connect(self._on_file_selected)
        v.addWidget(self.file_list, 1)

        self.lbl_count = QLabel("0 files")
        self.lbl_count.setAlignment(Qt.AlignRight)
        self.lbl_count.setObjectName("dim_label")
        v.addWidget(self.lbl_count)

        btn_rm = QPushButton("Remove Selected")
        btn_rm.clicked.connect(self._remove_selected)
        v.addWidget(btn_rm)
        return w

    # ── Settings panel (tabbed) ───────────────────────────────────────────────

    def _build_settings_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 0, 4, 0)
        v.setSpacing(4)

        lbl = QLabel("⚙  Settings")
        lbl.setObjectName("panel_label")
        v.addWidget(lbl)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_watermark(),    "✏  Watermark")
        self.tabs.addTab(self._tab_realestate(),   "🏠  Real Estate")
        self.tabs.addTab(self._tab_logo(),         "🖼  Logo")
        self.tabs.addTab(self._tab_image_options(), "🔧  Image Options")
        self.tabs.addTab(self._tab_profiles(),     "💾  Profiles")
        v.addWidget(self.tabs, 1)
        return w

    # ── Watermark tab ─────────────────────────────────────────────────────────

    def _tab_watermark(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        form  = QFormLayout(inner)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ── Text lines ────────────────────────────────────────────────────
        form.addRow(self._section("Text Lines"))
        self.txt_line1 = QLineEdit(); self.txt_line1.setPlaceholderText("e.g. © My Brand")
        self.txt_line2 = QLineEdit(); self.txt_line2.setPlaceholderText("Optional line 2")
        self.txt_line3 = QLineEdit(); self.txt_line3.setPlaceholderText("Optional line 3")
        form.addRow("Line 1:", self.txt_line1)
        form.addRow("Line 2:", self.txt_line2)
        form.addRow("Line 3:", self.txt_line3)

        # ── Font ──────────────────────────────────────────────────────────
        form.addRow(self._section("Font"))
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(FONT_NAMES)
        form.addRow("Font:", self.cmb_font)

        self.spn_font_size = QSpinBox()
        self.spn_font_size.setRange(8, 400)
        self.spn_font_size.setSuffix("  pt")
        form.addRow("Size:", self.spn_font_size)

        # Colour row: button + swatch preview
        color_row = QHBoxLayout()
        self.btn_color        = QPushButton("Pick Colour…")
        self.lbl_color_swatch = QLabel()
        self.lbl_color_swatch.setFixedSize(48, 22)
        self.lbl_color_swatch.setObjectName("color_swatch")
        color_row.addWidget(self.btn_color)
        color_row.addWidget(self.lbl_color_swatch)
        color_row.addStretch()
        form.addRow("Colour:", self._wrap(color_row))
        self.btn_color.clicked.connect(self._pick_color)

        # ── Style ─────────────────────────────────────────────────────────
        form.addRow(self._section("Style"))
        self.sld_opacity,     self.lbl_opacity_val     = self._make_slider(0, 100,  1,  "%")
        self.sld_line_spacing,self.lbl_spacing_val     = self._make_slider(100, 300, 120, "x", divisor=100, decimals=1)
        form.addRow("Opacity:",      self._slider_row(self.sld_opacity,      self.lbl_opacity_val))
        form.addRow("Line Spacing:", self._slider_row(self.sld_line_spacing, self.lbl_spacing_val))

        # ── Position ──────────────────────────────────────────────────────
        form.addRow(self._section("Position"))
        self._pos_group = QButtonGroup(self)
        pos_layout = QHBoxLayout()
        self._pos_btns = {}
        for key, label in POSITION_LABELS.items():
            rb = QRadioButton(label)
            self._pos_group.addButton(rb)
            pos_layout.addWidget(rb)
            self._pos_btns[key] = rb
        form.addRow("", self._wrap(pos_layout))

        self.spn_margin = QSpinBox()
        self.spn_margin.setRange(0, 300)
        self.spn_margin.setSuffix("  px")
        form.addRow("Margin:", self.spn_margin)

        # ── Effects ───────────────────────────────────────────────────────
        form.addRow(self._section("Effects"))
        eff_layout = QHBoxLayout()
        self.chk_shadow  = QCheckBox("Shadow")
        self.chk_outline = QCheckBox("Outline")
        eff_layout.addWidget(self.chk_shadow)
        eff_layout.addWidget(self.chk_outline)
        eff_layout.addStretch()
        form.addRow("Effects:", self._wrap(eff_layout))

        # ── Live-preview signal wiring ─────────────────────────────────────
        for widget in (self.txt_line1, self.txt_line2, self.txt_line3):
            widget.textChanged.connect(self._schedule_preview)
        self.cmb_font.currentTextChanged.connect(self._schedule_preview)
        self.spn_font_size.valueChanged.connect(self._schedule_preview)
        self.sld_opacity.valueChanged.connect(self._schedule_preview)
        self.sld_line_spacing.valueChanged.connect(self._schedule_preview)
        for rb in self._pos_btns.values():
            rb.toggled.connect(self._schedule_preview)
        self.spn_margin.valueChanged.connect(self._schedule_preview)
        self.chk_shadow.stateChanged.connect(self._schedule_preview)
        self.chk_outline.stateChanged.connect(self._schedule_preview)

        scroll.setWidget(inner)
        return scroll

    # ── Real Estate tab ───────────────────────────────────────────────────────

    def _tab_realestate(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        v.addWidget(self._section("Quick Presets"))

        grid = QGridLayout()
        grid.setSpacing(6)
        for idx, name in enumerate(REALESTATE_PRESETS):
            btn = QPushButton(name)
            btn.setObjectName("preset_btn")
            btn.clicked.connect(lambda _, n=name: self._apply_re_preset(n))
            grid.addWidget(btn, idx // 2, idx % 2)
        v.addLayout(grid)

        v.addWidget(self._section("Agent Information"))

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.txt_agent     = QLineEdit(); self.txt_agent.setPlaceholderText("e.g. Maria Santos")
        self.txt_license   = QLineEdit(); self.txt_license.setPlaceholderText("PRC licence number")
        self.txt_contact   = QLineEdit(); self.txt_contact.setPlaceholderText("+63 917 123 4567")
        self.chk_datestamp = QCheckBox("Include today's date automatically")
        form.addRow("Agent Name:",    self.txt_agent)
        form.addRow("PRC Licence #:", self.txt_license)
        form.addRow("Contact:",       self.txt_contact)
        form.addRow("",               self.chk_datestamp)
        v.addLayout(form)
        v.addStretch()

        for w in (self.txt_agent, self.txt_license, self.txt_contact):
            w.textChanged.connect(self._schedule_preview)
        self.chk_datestamp.stateChanged.connect(self._schedule_preview)

        scroll.setWidget(inner)
        return scroll

    # ── Logo tab ──────────────────────────────────────────────────────────────

    def _tab_logo(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        v.addWidget(self._section("Logo File  (PNG with transparency)"))

        path_row = QHBoxLayout()
        self.btn_logo_browse = QPushButton("📂  Browse…")
        self.lbl_logo_path   = QLabel("No logo selected")
        self.lbl_logo_path.setWordWrap(True)
        path_row.addWidget(self.btn_logo_browse)
        path_row.addWidget(self.lbl_logo_path, 1)
        v.addLayout(path_row)
        self.btn_logo_browse.clicked.connect(self._browse_logo)

        self.lbl_logo_thumb = QLabel("Logo preview will appear here")
        self.lbl_logo_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_logo_thumb.setObjectName("logo_thumb")
        self.lbl_logo_thumb.setFixedHeight(90)
        v.addWidget(self.lbl_logo_thumb)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.sld_logo_size,  self.lbl_logo_size_val  = self._make_slider(5, 50, 20, "%")
        self.sld_logo_size.valueChanged.connect(self._schedule_preview)
        form.addRow("Logo Size:", self._slider_row(self.sld_logo_size, self.lbl_logo_size_val))

        self.cmb_logo_pos = QComboBox()
        for key, lbl in POSITION_LABELS.items():
            self.cmb_logo_pos.addItem(lbl, key)
        self.cmb_logo_pos.currentIndexChanged.connect(self._schedule_preview)
        form.addRow("Position:", self.cmb_logo_pos)
        v.addLayout(form)

        btn_clear = QPushButton("✕  Remove Logo")
        btn_clear.clicked.connect(self._clear_logo)
        v.addWidget(btn_clear)
        v.addStretch()

        scroll.setWidget(inner)
        return scroll

    # ── Image Options tab ─────────────────────────────────────────────────────

    def _tab_image_options(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        form  = QFormLayout(inner)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        form.addRow(self._section("Output Format"))
        self.cmb_format = QComboBox()
        self.cmb_format.addItems(OUTPUT_FORMATS)
        form.addRow("Format:", self.cmb_format)

        self.sld_quality, self.lbl_quality_val = self._make_slider(10, 100, 90, "")
        form.addRow("Quality:", self._slider_row(self.sld_quality, self.lbl_quality_val))

        form.addRow(self._section("Resize Before Watermark"))
        self.chk_resize = QCheckBox("Enable resize")
        form.addRow("", self.chk_resize)

        resize_h = QHBoxLayout()
        self.spn_rw = QSpinBox(); self.spn_rw.setRange(100, 10000); self.spn_rw.setSuffix(" px")
        self.spn_rh = QSpinBox(); self.spn_rh.setRange(100, 10000); self.spn_rh.setSuffix(" px")
        resize_h.addWidget(QLabel("Max W:")); resize_h.addWidget(self.spn_rw)
        resize_h.addWidget(QLabel("Max H:")); resize_h.addWidget(self.spn_rh)
        resize_h.addStretch()
        form.addRow("Dimensions:", self._wrap(resize_h))

        form.addRow(self._section("Smart Opacity"))
        self.chk_smart = QCheckBox("Auto-adjust opacity based on image brightness")
        form.addRow("", self.chk_smart)

        form.addRow(self._section("Output Directory & Naming"))
        dir_h = QHBoxLayout()
        self.txt_outdir     = QLineEdit()
        btn_browse_out      = QPushButton("📂")
        btn_browse_out.setFixedWidth(36)
        btn_browse_out.clicked.connect(self._browse_output_dir)
        dir_h.addWidget(self.txt_outdir, 1)
        dir_h.addWidget(btn_browse_out)
        form.addRow("Output Dir:", self._wrap(dir_h))

        self.txt_prefix = QLineEdit(); self.txt_prefix.setPlaceholderText("e.g. wm_")
        self.txt_suffix = QLineEdit(); self.txt_suffix.setPlaceholderText("e.g. _watermarked")
        form.addRow("Prefix:", self.txt_prefix)
        form.addRow("Suffix:", self.txt_suffix)

        scroll.setWidget(inner)
        return scroll

    # ── Profiles tab ──────────────────────────────────────────────────────────

    def _tab_profiles(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        v.addWidget(self._section("Saved Profiles"))

        self.lst_profiles = QListWidget()
        self._refresh_profiles()
        v.addWidget(self.lst_profiles, 1)

        self.txt_profile_name = QLineEdit()
        self.txt_profile_name.setPlaceholderText("Profile name…")
        v.addWidget(self.txt_profile_name)

        btn_h = QHBoxLayout()
        btn_save   = QPushButton("💾  Save")
        btn_load   = QPushButton("📂  Load")
        btn_delete = QPushButton("🗑  Delete")
        btn_h.addWidget(btn_save)
        btn_h.addWidget(btn_load)
        btn_h.addWidget(btn_delete)
        v.addLayout(btn_h)

        btn_save.clicked.connect(self._save_profile)
        btn_load.clicked.connect(self._load_profile)
        btn_delete.clicked.connect(self._delete_profile)
        return w

    # ── Preview panel ─────────────────────────────────────────────────────────

    def _build_preview_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 0, 0, 0)
        v.setSpacing(4)

        lbl = QLabel("👁  Live Preview")
        lbl.setObjectName("panel_label")
        v.addWidget(lbl)

        self.lbl_preview = QLabel("Add images and adjust settings\nto see a live preview here")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setObjectName("preview_box")
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_preview.setWordWrap(True)
        v.addWidget(self.lbl_preview, 1)

        self.lbl_preview_meta = QLabel("")
        self.lbl_preview_meta.setAlignment(Qt.AlignCenter)
        self.lbl_preview_meta.setObjectName("dim_label")
        v.addWidget(self.lbl_preview_meta)
        return w

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("status_bar")
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 4, 10, 4)

        self.lbl_status = QLabel("Ready")
        h.addWidget(self.lbl_status)
        h.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(260)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m")
        self.progress_bar.setVisible(False)
        h.addWidget(self.progress_bar)

        self.btn_abort = QPushButton("■  Abort")
        self.btn_abort.setObjectName("abort_btn")
        self.btn_abort.setVisible(False)
        self.btn_abort.clicked.connect(self._abort_batch)
        h.addWidget(self.btn_abort)

        self.lbl_outdir = QLabel(f"Output: {self.output_dir}")
        self.lbl_outdir.setObjectName("dim_label")
        h.addWidget(self.lbl_outdir)
        return w

    # ──────────────────────── UI helpers ──────────────────────────────────────

    @staticmethod
    def _section(title: str) -> QLabel:
        """Create a bold section-divider label for use in QFormLayout."""
        lbl = QLabel(title)
        lbl.setObjectName("section_lbl")
        return lbl

    @staticmethod
    def _wrap(layout) -> QWidget:
        """Wrap a QLayout inside a plain QWidget (needed by QFormLayout rows)."""
        w = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)
        return w

    def _make_slider(
        self, lo: int, hi: int, default: int,
        unit: str = "", divisor: int = 1, decimals: int = 0
    ):
        """
        Create a QSlider and its matching value-label, wired together.
        Returns (slider, label).
        """
        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(default)

        def _fmt(v):
            val = v / divisor
            if decimals:
                return f"{val:.{decimals}f}{unit}"
            return f"{int(val)}{unit}"

        label = QLabel(_fmt(default))
        label.setFixedWidth(52)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider.valueChanged.connect(lambda v, lbl=label: lbl.setText(_fmt(v)))
        return slider, label

    @staticmethod
    def _slider_row(slider, label) -> QWidget:
        """Pack slider + value label into a horizontal widget."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(slider, 1)
        h.addWidget(label)
        return w

    # ──────────────────────── File management ─────────────────────────────────

    def _add_files_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        )
        self._add_paths(paths)

    def _on_files_dropped(self, paths: list):
        self._add_paths(paths)

    def _add_paths(self, paths: list):
        existing = set(self.files)
        added = 0
        for p in paths:
            if p not in existing:
                self.files.append(p)
                self.file_list.addItem(os.path.basename(p))
                added += 1
        if added:
            self._update_count()

    def _clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self._update_count()
        self.lbl_preview.setText("Add images and adjust settings\nto see a live preview here")
        self.lbl_preview_meta.clear()

    def _remove_selected(self):
        # Remove in reverse order to keep indices valid
        for item in reversed(self.file_list.selectedItems()):
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            del self.files[row]
        self._update_count()

    def _update_count(self):
        n = len(self.files)
        self.lbl_count.setText(f"{n} file{'s' if n != 1 else ''}")

    def _on_file_selected(self):
        self._schedule_preview()

    # ──────────────────────── Live preview ────────────────────────────────────

    def _schedule_preview(self, *_args):
        """Debounce rapid UI changes; render preview 400 ms after last change."""
        if not hasattr(self, "_preview_timer"):
            self._preview_timer = QTimer(self)
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.start(400)

    def _update_preview(self):
        """Render a thumbnail-sized watermarked preview of the selected file."""
        selected = self.file_list.selectedItems()
        if not selected or not self.files:
            return

        row  = self.file_list.row(selected[0])
        if row >= len(self.files):
            return
        path = self.files[row]

        try:
            config = self._collect_config()

            # Load and create a small thumbnail for speed
            image = self.processor.load(path)
            orig_w, orig_h = image.size

            thumb = image.copy()
            thumb.thumbnail((580, 420), Image.LANCZOS)
            tw, th = thumb.size

            # Scale font/margin proportionally to the thumbnail size
            scale = tw / max(orig_w, 1)
            p_cfg = dict(config)
            p_cfg["font_size"] = max(6, int(config["font_size"] * scale))
            p_cfg["margin"]    = max(2, int(config["margin"]    * scale))

            result = self.engine.process(thumb, p_cfg)

            # Convert PIL image → QPixmap
            buf = io.BytesIO()
            fmt = "PNG" if result.mode == "RGBA" else "JPEG"
            result.save(buf, format=fmt)
            buf.seek(0)

            pix = QPixmap()
            pix.loadFromData(buf.read())
            scaled = pix.scaled(
                self.lbl_preview.size() - self.lbl_preview.size() * 0,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.lbl_preview.setPixmap(scaled)
            self.lbl_preview_meta.setText(
                f"{orig_w} × {orig_h} px  •  {os.path.basename(path)}"
            )

        except Exception as exc:
            self.lbl_preview.setText(f"Preview error:\n{exc}")

    # ──────────────────────── Batch processing ────────────────────────────────

    def _start_batch(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add at least one image.")
            return

        config = self._collect_config()
        # Auto-save current settings as last-used
        self.profiles.save_last_used(config)

        n = len(self.files)
        self.progress_bar.setMaximum(n)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"0 / {n}")
        self.progress_bar.setVisible(True)
        self.btn_abort.setVisible(True)
        self.btn_process.setEnabled(False)
        self.lbl_status.setText(f"Processing {n} image{'s' if n != 1 else ''}…")

        self.worker = BatchWorker(self.files, config, self.output_dir)
        self.worker.progress.connect(
            lambda pct: (
                self.progress_bar.setValue(round(pct / 100 * n)),
                self.progress_bar.setFormat(f"{round(pct/100*n)} / {n}")
            )
        )
        self.worker.log_message.connect(self._on_log)
        self.worker.finished.connect(self._on_batch_done)
        self.worker.start()

    def _abort_batch(self):
        if self.worker:
            self.worker.abort()
            self.lbl_status.setText("Aborting…")

    def _on_log(self, msg: str):
        self.lbl_status.setText(msg)

    def _on_batch_done(self, done: int, failed: int):
        self.progress_bar.setVisible(False)
        self.btn_abort.setVisible(False)
        self.btn_process.setEnabled(True)
        self.lbl_status.setText(
            f"✅  {done} watermarked"
            + (f"  ⚠ {failed} failed" if failed else "")
            + f"  →  {self.output_dir}"
        )
        icon = "✅" if not failed else "⚠"
        QMessageBox.information(
            self, "Batch Complete",
            f"{icon}  {done} image{'s' if done != 1 else ''} watermarked\n"
            + (f"⚠  {failed} file{'s' if failed != 1 else ''} failed\n\n" if failed else "\n")
            + f"Saved to:\n{self.output_dir}"
        )

    # ──────────────────────── Colour picker ───────────────────────────────────

    def _pick_color(self):
        init  = QColor(self._color)
        color = QColorDialog.getColor(init, self, "Watermark Colour")
        if color.isValid():
            self._set_color(color.name())
            self._schedule_preview()

    def _set_color(self, hex_color: str):
        self._color = hex_color
        self.lbl_color_swatch.setStyleSheet(
            f"background:{hex_color}; border:1px solid #94A3B8; border-radius:3px;"
        )

    # ──────────────────────── Logo ────────────────────────────────────────────

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo", "", "PNG Images (*.png)"
        )
        if path:
            self._color  # keep current colour intact
            self.config["logo_path"] = path
            self.lbl_logo_path.setText(os.path.basename(path))
            self._show_logo_thumb(path)
            self._schedule_preview()

    def _show_logo_thumb(self, path: str):
        pix = QPixmap(path)
        if not pix.isNull():
            self.lbl_logo_thumb.setPixmap(
                pix.scaled(200, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def _clear_logo(self):
        self.config["logo_path"] = ""
        self.lbl_logo_path.setText("No logo selected")
        self.lbl_logo_thumb.clear()
        self.lbl_logo_thumb.setText("Logo preview will appear here")
        self._schedule_preview()

    # ──────────────────────── Real-estate presets ──────────────────────────────

    def _apply_re_preset(self, name: str):
        preset = REALESTATE_PRESETS.get(name, {})

        if "font_name" in preset:
            idx = self.cmb_font.findText(preset["font_name"])
            if idx >= 0:
                self.cmb_font.setCurrentIndex(idx)

        if "font_size"  in preset: self.spn_font_size.setValue(preset["font_size"])
        if "opacity"    in preset: self.sld_opacity.setValue(preset["opacity"])
        if "margin"     in preset: self.spn_margin.setValue(preset["margin"])
        if "shadow"     in preset: self.chk_shadow.setChecked(preset["shadow"])
        if "outline"    in preset: self.chk_outline.setChecked(preset["outline"])
        if "color"      in preset: self._set_color(preset["color"])
        if "position"   in preset:
            pos = preset["position"]
            if pos in self._pos_btns:
                self._pos_btns[pos].setChecked(True)

        # Badge modes auto-populate line 1 with the badge text
        if "badge_text" in preset:
            self.txt_line1.setText(preset["badge_text"])

        self._schedule_preview()
        self.lbl_status.setText(f"Preset applied: {name}")

    # ──────────────────────── Profiles ────────────────────────────────────────

    def _save_profile(self):
        name = self.txt_profile_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Enter a profile name first.")
            return
        self.profiles.save(name, self._collect_config())
        self._refresh_profiles()
        self.lbl_status.setText(f"Profile saved: {name}")

    def _load_profile(self):
        item = self.lst_profiles.currentItem()
        if not item:
            QMessageBox.warning(self, "Select Profile", "Select a profile from the list.")
            return
        self.config = self.profiles.load(item.text())
        self._color  = self.config.get("color", "#FFFFFF")
        self._load_config_to_ui()
        self.lbl_status.setText(f"Profile loaded: {item.text()}")
        self._schedule_preview()

    def _delete_profile(self):
        item = self.lst_profiles.currentItem()
        if not item:
            return
        if QMessageBox.question(
            self, "Delete Profile",
            f"Delete profile \"{item.text()}\"?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.profiles.delete(item.text())
            self._refresh_profiles()

    def _refresh_profiles(self):
        self.lst_profiles.clear()
        for name in self.profiles.list_profiles():
            self.lst_profiles.addItem(name)

    # ──────────────────────── Output directory ────────────────────────────────

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_dir
        )
        if path:
            self.output_dir = path
            self.txt_outdir.setText(path)
            self.lbl_outdir.setText(f"Output: {path}")

    def _open_output_folder(self):
        os.makedirs(self.output_dir, exist_ok=True)
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))

    # ──────────────────────── Config collect / apply ──────────────────────────

    def _collect_config(self) -> dict:
        """
        Read all UI widgets and return a plain config dict.

        This dict is the single exchange format between the UI and the engine.
        It can be serialised to JSON for a future API endpoint.
        """
        # Active position radio button
        position = POSITION_LOWER_RIGHT
        for key, rb in self._pos_btns.items():
            if rb.isChecked():
                position = key
                break

        return {
            # Text
            "text_line1":     self.txt_line1.text(),
            "text_line2":     self.txt_line2.text(),
            "text_line3":     self.txt_line3.text(),
            # Font / style
            "font_name":      self.cmb_font.currentText(),
            "font_size":      self.spn_font_size.value(),
            "color":          self._color,
            "opacity":        self.sld_opacity.value(),
            "line_spacing":   self.sld_line_spacing.value() / 100,
            # Position
            "position":       position,
            "margin":         self.spn_margin.value(),
            # Effects
            "shadow":         self.chk_shadow.isChecked(),
            "outline":        self.chk_outline.isChecked(),
            # Real estate
            "re_agent_name":  self.txt_agent.text(),
            "re_license":     self.txt_license.text(),
            "re_contact":     self.txt_contact.text(),
            "re_date_stamp":  self.chk_datestamp.isChecked(),
            # Logo
            "logo_path":      self.config.get("logo_path", ""),
            "logo_size":      self.sld_logo_size.value(),
            "logo_position":  self.cmb_logo_pos.currentData() or POSITION_LOWER_LEFT,
            # Image options
            "output_format":  self.cmb_format.currentText(),
            "quality":        self.sld_quality.value(),
            "resize_enabled": self.chk_resize.isChecked(),
            "resize_width":   self.spn_rw.value(),
            "resize_height":  self.spn_rh.value(),
            "smart_opacity":  self.chk_smart.isChecked(),
            # Naming
            "prefix":         self.txt_prefix.text(),
            "suffix":         self.txt_suffix.text(),
        }

    def _load_config_to_ui(self):
        """Push a config dict back into all UI widgets."""
        c = self.config

        self.txt_line1.setText(c.get("text_line1", ""))
        self.txt_line2.setText(c.get("text_line2", ""))
        self.txt_line3.setText(c.get("text_line3", ""))

        idx = self.cmb_font.findText(c.get("font_name", "Arial"))
        if idx >= 0:
            self.cmb_font.setCurrentIndex(idx)

        self.spn_font_size.setValue(c.get("font_size", 36))
        self._set_color(c.get("color", "#FFFFFF"))
        self.sld_opacity.setValue(c.get("opacity", 60))
        self.sld_line_spacing.setValue(int(c.get("line_spacing", 1.2) * 100))

        pos = c.get("position", POSITION_LOWER_RIGHT)
        if pos in self._pos_btns:
            self._pos_btns[pos].setChecked(True)

        self.spn_margin.setValue(c.get("margin", 20))
        self.chk_shadow.setChecked(c.get("shadow", True))
        self.chk_outline.setChecked(c.get("outline", False))

        # Real estate
        self.txt_agent.setText(c.get("re_agent_name", ""))
        self.txt_license.setText(c.get("re_license", ""))
        self.txt_contact.setText(c.get("re_contact", ""))
        self.chk_datestamp.setChecked(c.get("re_date_stamp", False))

        # Logo
        logo = c.get("logo_path", "")
        if logo and os.path.exists(logo):
            self.lbl_logo_path.setText(os.path.basename(logo))
            self._show_logo_thumb(logo)
        self.sld_logo_size.setValue(c.get("logo_size", 20))
        logo_pos_idx = self.cmb_logo_pos.findData(
            c.get("logo_position", POSITION_LOWER_LEFT)
        )
        if logo_pos_idx >= 0:
            self.cmb_logo_pos.setCurrentIndex(logo_pos_idx)

        # Image options
        fmt_idx = self.cmb_format.findText(c.get("output_format", "JPG"))
        if fmt_idx >= 0:
            self.cmb_format.setCurrentIndex(fmt_idx)
        self.sld_quality.setValue(c.get("quality", 90))
        self.chk_resize.setChecked(c.get("resize_enabled", False))
        self.spn_rw.setValue(c.get("resize_width",  1920))
        self.spn_rh.setValue(c.get("resize_height", 1080))
        self.chk_smart.setChecked(c.get("smart_opacity", False))

        # Naming / output dir
        self.txt_outdir.setText(self.output_dir)
        self.txt_prefix.setText(c.get("prefix", ""))
        self.txt_suffix.setText(c.get("suffix", "_watermarked"))

    # ──────────────────────── Stylesheet ──────────────────────────────────────

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            /* ── Global ── */
            QMainWindow, QWidget {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                color: #1E293B;
            }

            /* ── Toolbar ── */
            #toolbar {
                background: #1E293B;
                border-radius: 6px;
                min-height: 42px;
            }
            #app_title {
                font-size: 17px;
                font-weight: bold;
                color: #60A5FA;
                padding-left: 4px;
            }
            #toolbar QPushButton {
                background: #334155;
                color: #E2E8F0;
                border: none;
                padding: 7px 16px;
                border-radius: 5px;
                font-size: 13px;
            }
            #toolbar QPushButton:hover  { background: #475569; }
            #toolbar QPushButton:pressed{ background: #1E293B; }
            #primary_btn {
                background: #2563EB !important;
                color: white !important;
                font-weight: bold;
                font-size: 13px;
            }
            #primary_btn:hover  { background: #1D4ED8 !important; }
            #primary_btn:pressed{ background: #1E40AF !important; }

            /* ── Panel labels ── */
            #panel_label {
                font-size: 11px;
                font-weight: bold;
                color: #64748B;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                padding: 4px 0 2px 0;
            }
            #section_lbl {
                font-size: 11px;
                font-weight: bold;
                color: #94A3B8;
                padding-top: 8px;
            }

            /* ── File list ── */
            QListWidget {
                background: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #DBEAFE;
                color: #1E293B;
            }
            QListWidget::item:hover:!selected {
                background: #E2E8F0;
            }

            /* ── Tabs ── */
            QTabWidget::pane {
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #2563EB;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #E2E8F0; }

            /* ── Preview area ── */
            #preview_box {
                background: #0F172A;
                border-radius: 8px;
                color: #475569;
                font-size: 14px;
            }
            #logo_thumb {
                background: #F1F5F9;
                border: 1px dashed #CBD5E1;
                border-radius: 5px;
                color: #94A3B8;
                font-size: 12px;
            }

            /* ── Colour swatch ── */
            #color_swatch {
                border: 1px solid #94A3B8;
                border-radius: 3px;
                background: #FFFFFF;
            }

            /* ── Inputs ── */
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
                min-height: 26px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #93C5FD;
                outline: none;
            }

            /* ── Buttons ── */
            QPushButton {
                background: #E2E8F0;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                min-height: 28px;
            }
            QPushButton:hover  { background: #CBD5E1; }
            QPushButton:pressed{ background: #94A3B8; color: white; }

            /* ── Real-estate preset buttons ── */
            #preset_btn {
                background: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                font-size: 12px;
                padding: 10px 6px;
                text-align: center;
            }
            #preset_btn:hover  { background: #DBEAFE; }
            #preset_btn:pressed{ background: #BFDBFE; }

            /* ── Sliders ── */
            QSlider::groove:horizontal {
                height: 4px;
                background: #CBD5E1;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2563EB;
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover { background: #1D4ED8; }
            QSlider::sub-page:horizontal {
                background: #93C5FD;
                border-radius: 2px;
            }

            /* ── Checkboxes / radios ── */
            QCheckBox::indicator, QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }

            /* ── Status bar ── */
            #status_bar {
                background: #F1F5F9;
                border-top: 1px solid #E2E8F0;
                border-radius: 4px;
                min-height: 30px;
            }
            #dim_label {
                color: #94A3B8;
                font-size: 12px;
            }

            /* ── Progress bar ── */
            QProgressBar {
                border: none;
                background: #E2E8F0;
                border-radius: 4px;
                text-align: center;
                font-size: 12px;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: #2563EB;
                border-radius: 4px;
            }

            /* ── Abort button ── */
            #abort_btn {
                background: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FECACA;
            }
            #abort_btn:hover { background: #FEE2E2; }

            /* ── Scroll areas ── */
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #F1F5F9;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

            /* ── Splitter handle ── */
            QSplitter::handle { background: #E2E8F0; }
        """)

    # ──────────────────────── Window close ────────────────────────────────────

    def closeEvent(self, event):
        """Auto-save settings when the window is closed."""
        try:
            self.profiles.save_last_used(self._collect_config())
        except Exception:
            pass  # Never block the close event
        event.accept()
