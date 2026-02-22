"""
constants.py — Application-wide constants for PhotoWatermark Pro.

All magic values live here so the rest of the codebase stays clean.
Future-ready: these values can be loaded from a config file or env vars
without touching business logic.
"""

import os

# ─── App Identity ─────────────────────────────────────────────────────────────
APP_NAME    = "PhotoWatermark Pro"
APP_VERSION = "1.0.0"

# ─── Directory Paths ──────────────────────────────────────────────────────────
# BASE_DIR = the /watermark_app root (two levels up from this file)
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR      = os.path.join(os.path.expanduser("~"), "watermarked_output")
PROFILES_DIR    = os.path.join(BASE_DIR, "profiles")
LAST_USED_FILE  = os.path.join(PROFILES_DIR, "_last_used.json")

# ─── Watermark Position Keys ──────────────────────────────────────────────────
POSITION_LOWER_LEFT  = "lower_left"
POSITION_LOWER_RIGHT = "lower_right"
POSITION_CENTER      = "center"
POSITION_DIAGONAL    = "diagonal"

POSITION_LABELS = {
    POSITION_LOWER_LEFT:  "Lower Left",
    POSITION_LOWER_RIGHT: "Lower Right",
    POSITION_CENTER:      "Center",
    POSITION_DIAGONAL:    "Diagonal",
}

# ─── Supported Fonts (Windows TrueType names) ─────────────────────────────────
# Each key maps to a list of candidate .ttf filenames; first match wins.
FONT_MAP = {
    "Arial":           ["arial.ttf",       "Arial.ttf"],
    "Arial Bold":      ["arialbd.ttf",     "Arial Bold.ttf"],
    "Times New Roman": ["times.ttf",       "Times New Roman.ttf", "timesbd.ttf"],
    "Helvetica":       ["arial.ttf"],          # Helvetica not bundled in Windows
    "Roboto":          ["Roboto-Regular.ttf",  "roboto.ttf",   "arial.ttf"],
    "Verdana":         ["verdana.ttf",     "Verdana.ttf"],
    "Georgia":         ["georgia.ttf",     "Georgia.ttf"],
    "Calibri":         ["calibri.ttf",     "Calibri.ttf"],
    "Trebuchet MS":    ["trebuc.ttf",      "Trebuchet MS.ttf"],
}
FONT_NAMES = list(FONT_MAP.keys())

# Windows directories where .ttf files are stored
WINDOWS_FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.join(
        os.path.expanduser("~"),
        "AppData", "Local", "Microsoft", "Windows", "Fonts"
    ),
]

# ─── Output Formats ───────────────────────────────────────────────────────────
OUTPUT_FORMATS    = ["JPG", "PNG", "WebP"]
FORMAT_EXTENSIONS = {"JPG": ".jpg",  "PNG": ".png",  "WebP": ".webp"}
FORMAT_PIL_NAMES  = {"JPG": "JPEG",  "PNG": "PNG",   "WebP": "WEBP"}

# ─── Real-Estate Preset Styles ────────────────────────────────────────────────
# Each preset is a partial config dict; it overrides only the keys it defines.
REALESTATE_PRESETS = {
    "Subtle Floor Style": {
        "position":  POSITION_LOWER_LEFT,
        "opacity":   40,
        "font_size": 28,
        "font_name": "Arial",
        "color":     "#FFFFFF",
        "shadow":    True,
        "outline":   False,
        "margin":    20,
    },
    "Corner Professional": {
        "position":  POSITION_LOWER_RIGHT,
        "opacity":   70,
        "font_size": 32,
        "font_name": "Arial Bold",
        "color":     "#FFFFFF",
        "shadow":    True,
        "outline":   False,
        "margin":    15,
    },
    "Center Promo": {
        "position":  POSITION_CENTER,
        "opacity":   55,
        "font_size": 48,
        "font_name": "Arial Bold",
        "color":     "#FFFFFF",
        "shadow":    False,
        "outline":   True,
        "margin":    0,
    },
    "SOLD Badge Mode": {
        "position":  POSITION_CENTER,
        "opacity":   85,
        "font_size": 96,
        "font_name": "Arial Bold",
        "color":     "#FF0000",
        "shadow":    False,
        "outline":   True,
        "margin":    0,
        "badge_text": "SOLD",
    },
    "NEW LISTING Badge Mode": {
        "position":  POSITION_LOWER_LEFT,
        "opacity":   85,
        "font_size": 56,
        "font_name": "Arial Bold",
        "color":     "#FFD700",
        "shadow":    True,
        "outline":   True,
        "margin":    20,
        "badge_text": "NEW LISTING",
    },
}

# ─── Default Configuration ────────────────────────────────────────────────────
# Used as the base config on first run and as merge target when loading profiles
# so that newly added keys are always present.
DEFAULT_CONFIG = {
    # Text watermark
    "text_line1":     "Your Watermark",
    "text_line2":     "",
    "text_line3":     "",
    # Font
    "font_name":      "Arial",
    "font_size":      36,
    # Style
    "color":          "#FFFFFF",
    "opacity":        60,
    "line_spacing":   1.2,
    # Position
    "position":       POSITION_LOWER_RIGHT,
    "margin":         20,
    # Effects
    "shadow":         True,
    "outline":        False,
    # Real-estate agent fields
    "re_agent_name":  "",
    "re_license":     "",
    "re_contact":     "",
    "re_date_stamp":  False,
    # Logo
    "logo_path":      "",
    "logo_size":      20,           # % of image width
    "logo_position":  POSITION_LOWER_LEFT,
    # Image / output options
    "output_format":  "JPG",
    "quality":        90,
    "resize_enabled": False,
    "resize_width":   1920,
    "resize_height":  1080,
    "smart_opacity":  False,
    # Output naming
    "prefix":         "",
    "suffix":         "_watermarked",
}
