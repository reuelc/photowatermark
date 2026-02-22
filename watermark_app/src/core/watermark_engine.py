"""
watermark_engine.py — Core image-watermarking logic for PhotoWatermark Pro.

Design principles
─────────────────
• Stateless:  WatermarkEngine.process() accepts (image, config) → image.
              No UI state is stored here, making it trivially reusable
              from a CLI, Flask/FastAPI endpoint, or Celery worker.
• Pure Pillow: No Qt dependency; swap the image transport layer freely.
• Commented:  Every non-obvious decision is explained inline.
"""

import os
from datetime import date as _date
from PIL import Image, ImageDraw, ImageFont

from .constants import (
    FONT_MAP,
    WINDOWS_FONT_DIRS,
    FORMAT_PIL_NAMES,
    POSITION_LOWER_LEFT,
    POSITION_LOWER_RIGHT,
    POSITION_CENTER,
    POSITION_DIAGONAL,
)


# ──────────────────────────────────────────────────────────────────────────────
# Font helpers
# ──────────────────────────────────────────────────────────────────────────────

def find_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """
    Locate and load a TrueType font by logical name.

    Search order:
      1. Absolute paths (used when user drops a .ttf into profiles/).
      2. Windows system font directories.
      3. Direct name (works if the font is on the system PATH / current dir).
      4. Pillow's built-in bitmap fallback (always succeeds, no size control).
    """
    candidates = FONT_MAP.get(font_name, ["arial.ttf"])

    for filename in candidates:
        # 1. Absolute path provided directly
        if os.path.isabs(filename) and os.path.exists(filename):
            try:
                return ImageFont.truetype(filename, size)
            except (IOError, OSError):
                continue

        # 2. Windows font directories
        for font_dir in WINDOWS_FONT_DIRS:
            full = os.path.join(font_dir, filename)
            if os.path.exists(full):
                try:
                    return ImageFont.truetype(full, size)
                except (IOError, OSError):
                    continue

        # 3. Let Pillow / OS resolve via PATH or current directory
        try:
            return ImageFont.truetype(filename, size)
        except (IOError, OSError):
            continue

    # 4. Absolute last resort — Pillow bitmap default (tiny, but never crashes)
    return ImageFont.load_default()


# ──────────────────────────────────────────────────────────────────────────────
# Colour / opacity helpers
# ──────────────────────────────────────────────────────────────────────────────

def hex_to_rgba(hex_color: str, opacity_pct: int) -> tuple:
    """
    Convert a CSS hex colour (#RRGGBB) and a 0-100 opacity percentage
    to an RGBA tuple suitable for Pillow.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(opacity_pct / 100 * 255)
    return (r, g, b, a)


def calc_brightness(image: Image.Image) -> float:
    """
    Return the average luminance of an image as a float in [0.0, 1.0].
    0.0 = solid black, 1.0 = solid white.
    """
    gray   = image.convert("L")
    pixels = list(gray.getdata())
    return sum(pixels) / (len(pixels) * 255.0)


def smart_opacity(opacity: int, brightness: float) -> int:
    """
    Nudge opacity so the watermark stays readable on both bright and dark images.

    • Bright image (> 0.65) → boost opacity by +20 so text isn't washed out.
    • Dark image  (< 0.30) → drop opacity by -10 so text isn't harsh.
    • Mid range          → unchanged.
    Result is always clamped to [10, 100].
    """
    if brightness > 0.65:
        opacity = opacity + 20
    elif brightness < 0.30:
        opacity = opacity - 10
    return max(10, min(100, opacity))


# ──────────────────────────────────────────────────────────────────────────────
# Main engine
# ──────────────────────────────────────────────────────────────────────────────

class WatermarkEngine:
    """
    Stateless watermark processor.

    Usage (also valid from a Flask/FastAPI handler):
        engine = WatermarkEngine()
        result = engine.process(pil_image, config_dict)
        result.save("out.jpg")
    """

    # ── Public entry-point ────────────────────────────────────────────────────

    def process(self, image: Image.Image, config: dict) -> Image.Image:
        """
        Apply all watermark layers to *image* and return a new image.
        The original image object is never modified.

        Pipeline:
          1. Convert to RGBA working copy.
          2. Optionally adjust opacity for image brightness.
          3. Composite logo layer (if configured).
          4. Composite text layer (if any text exists).
          5. Flatten to RGB for JPG output, or keep RGBA for PNG/WebP.
        """
        result = image.copy().convert("RGBA")

        # ── Smart opacity ──────────────────────────────────────────────────
        opacity = int(config.get("opacity", 60))
        if config.get("smart_opacity", False):
            brightness = calc_brightness(image)
            opacity    = smart_opacity(opacity, brightness)

        # ── Logo layer ────────────────────────────────────────────────────
        logo_path = config.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            result = self._apply_logo(result, config, opacity)

        # ── Text layer ────────────────────────────────────────────────────
        text_lines = self._build_text_lines(config)
        if any(t.strip() for t in text_lines):
            result = self._apply_text(result, text_lines, config, opacity)

        # ── Flatten for JPG (no alpha channel) ───────────────────────────
        out_fmt = config.get("output_format", "JPG").upper()
        if out_fmt == "JPG":
            bg = Image.new("RGB", result.size, (255, 255, 255))
            bg.paste(result, mask=result.split()[3])
            return bg

        return result  # PNG / WebP keep transparency

    # ── Text watermark ────────────────────────────────────────────────────────

    def _build_text_lines(self, config: dict) -> list:
        """
        Assemble the list of text lines from the three user text fields
        plus any real-estate agent data fields.
        """
        lines = []

        # Main text inputs (up to 3 lines)
        for key in ("text_line1", "text_line2", "text_line3"):
            val = config.get(key, "").strip()
            if val:
                lines.append(val)

        # Real-estate auto-include fields
        agent = config.get("re_agent_name", "").strip()
        lic   = config.get("re_license",    "").strip()
        phone = config.get("re_contact",    "").strip()
        stamp = config.get("re_date_stamp", False)

        if agent:
            lines.append(agent)
        if lic:
            lines.append(f"PRC #{lic}")
        if phone:
            lines.append(phone)
        if stamp:
            lines.append(_date.today().strftime("%B %d, %Y"))

        return lines

    def _apply_text(
        self,
        image:    Image.Image,
        lines:    list,
        config:   dict,
        opacity:  int,
    ) -> Image.Image:
        """
        Render multi-line text onto a transparent overlay and composite
        it over *image*.  Returns a new RGBA image.
        """
        font_name    = config.get("font_name",    "Arial")
        font_size    = int(config.get("font_size",    36))
        color        = config.get("color",        "#FFFFFF")
        line_spacing = float(config.get("line_spacing", 1.2))
        position     = config.get("position",     POSITION_LOWER_RIGHT)
        margin       = int(config.get("margin",       20))
        use_shadow   = config.get("shadow",       True)
        use_outline  = config.get("outline",      False)

        font  = find_font(font_name, font_size)
        rgba  = hex_to_rgba(color, opacity)
        img_w, img_h = image.size

        # Diagonal is rendered on its own path (rotated canvas)
        if position == POSITION_DIAGONAL:
            return self._render_diagonal(
                image, lines, font, rgba, font_size, line_spacing,
                use_shadow, use_outline
            )

        # ── Measure each line ─────────────────────────────────────────────
        overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        line_sizes = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw   = bbox[2] - bbox[0]
            lh   = bbox[3] - bbox[1]
            line_sizes.append((lw, lh))

        gap      = int(font_size * max(0.0, line_spacing - 1.0))
        total_h  = sum(h for _, h in line_sizes) + gap * max(0, len(lines) - 1)
        max_w    = max((w for w, _ in line_sizes), default=0)

        # ── Block origin ──────────────────────────────────────────────────
        bx, by = self._block_origin(img_w, img_h, max_w, total_h, position, margin)

        # ── Draw each line ────────────────────────────────────────────────
        cursor_y = by
        for i, (line, (lw, lh)) in enumerate(zip(lines, line_sizes)):
            # Horizontal alignment within the bounding box
            if position == POSITION_LOWER_LEFT:
                lx = bx
            elif position == POSITION_LOWER_RIGHT:
                lx = bx + (max_w - lw)
            else:  # center
                lx = bx + (max_w - lw) // 2

            # Shadow: a semi-transparent copy shifted 2 px down-right
            if use_shadow:
                sha = (0, 0, 0, rgba[3] // 2)
                draw.text((lx + 2, cursor_y + 2), line, font=font, fill=sha)

            # Outline: draw text in 8 offset directions with black colour
            if use_outline:
                out = (0, 0, 0, min(255, int(rgba[3] * 1.2)))
                for ox, oy in [(-2, -2), (-2, 0), (-2, 2),
                                ( 0, -2),           ( 0, 2),
                                ( 2, -2), ( 2, 0), ( 2, 2)]:
                    draw.text((lx + ox, cursor_y + oy), line, font=font, fill=out)

            # Main text
            draw.text((lx, cursor_y), line, font=font, fill=rgba)
            cursor_y += lh + gap

        return Image.alpha_composite(image, overlay)

    def _block_origin(
        self,
        img_w: int, img_h: int,
        block_w: int, block_h: int,
        position: str,
        margin: int,
    ) -> tuple:
        """Return the (x, y) top-left of the watermark block."""
        if position == POSITION_LOWER_LEFT:
            return margin, img_h - block_h - margin
        if position == POSITION_LOWER_RIGHT:
            return img_w - block_w - margin, img_h - block_h - margin
        if position == POSITION_CENTER:
            return (img_w - block_w) // 2, (img_h - block_h) // 2
        # Default fallback
        return margin, img_h - block_h - margin

    def _render_diagonal(
        self,
        image:        Image.Image,
        lines:        list,
        font:         ImageFont.FreeTypeFont,
        rgba:         tuple,
        font_size:    int,
        line_spacing: float,
        use_shadow:   bool,
        use_outline:  bool,
    ) -> Image.Image:
        """
        Render watermark text at a 45° diagonal across the image.

        Strategy:
          • Draw all text on a 2× canvas centred at that canvas's midpoint.
          • Rotate 45° (no expansion, keeps canvas size).
          • Crop back to original image dimensions from the canvas centre.
          • Alpha-composite onto the source image.
        """
        img_w, img_h = image.size
        angle        = 45
        spacing      = int(font_size * max(0.0, line_spacing - 1.0))
        text         = "\n".join(lines)

        # 2× canvas so rotation doesn't clip corners
        canvas = Image.new("RGBA", (img_w * 2, img_h * 2), (0, 0, 0, 0))
        d      = ImageDraw.Draw(canvas)

        # Measure text block
        bbox = d.textbbox((0, 0), text, font=font, spacing=spacing)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Centre the text on the large canvas
        tx = img_w  - tw // 2
        ty = img_h  - th // 2

        if use_shadow:
            sha = (0, 0, 0, rgba[3] // 2)
            d.text((tx + 2, ty + 2), text, font=font, fill=sha, spacing=spacing)

        if use_outline:
            out = (0, 0, 0, min(255, int(rgba[3] * 1.2)))
            for ox, oy in [(-2, -2), (-2, 0), (-2, 2),
                            ( 0, -2),           ( 0, 2),
                            ( 2, -2), ( 2, 0), ( 2, 2)]:
                d.text((tx + ox, ty + oy), text, font=font, fill=out, spacing=spacing)

        d.text((tx, ty), text, font=font, fill=rgba, spacing=spacing)

        # Rotate on the big canvas (expand=False keeps size)
        rotated = canvas.rotate(angle, expand=False)

        # Crop the centre img_w × img_h region
        x_off   = (rotated.width  - img_w) // 2
        y_off   = (rotated.height - img_h) // 2
        cropped = rotated.crop((x_off, y_off, x_off + img_w, y_off + img_h))

        return Image.alpha_composite(image, cropped)

    # ── Logo watermark ────────────────────────────────────────────────────────

    def _apply_logo(
        self,
        image:   Image.Image,
        config:  dict,
        opacity: int,
    ) -> Image.Image:
        """
        Paste a transparent PNG logo onto the image.

        • Logo is resized to `logo_size` % of the image width.
        • Opacity from the global watermark opacity slider is applied.
        • Position follows the same four-point scheme as text.
        """
        logo_path    = config.get("logo_path", "")
        logo_pct     = int(config.get("logo_size", 20))
        logo_pos     = config.get("logo_position", POSITION_LOWER_LEFT)
        margin       = int(config.get("margin", 20))

        try:
            logo = Image.open(logo_path).convert("RGBA")
        except Exception:
            return image  # Silently skip if logo can't be loaded

        # Scale logo to requested % of image width
        img_w, img_h = image.size
        target_w     = max(1, int(img_w * logo_pct / 100))
        ratio        = target_w / max(1, logo.width)
        target_h     = max(1, int(logo.height * ratio))
        logo         = logo.resize((target_w, target_h), Image.LANCZOS)

        # Apply global opacity to the logo's alpha channel
        if opacity < 100:
            r, g, b, a = logo.split()
            a    = a.point(lambda p: int(p * opacity / 100))
            logo = Image.merge("RGBA", (r, g, b, a))

        # Compute paste position
        lw, lh = logo.size
        if logo_pos == POSITION_LOWER_LEFT:
            px, py = margin, img_h - lh - margin
        elif logo_pos == POSITION_LOWER_RIGHT:
            px, py = img_w - lw - margin, img_h - lh - margin
        elif logo_pos == POSITION_CENTER:
            px, py = (img_w - lw) // 2, (img_h - lh) // 2
        else:
            px, py = margin, img_h - lh - margin

        # Composite onto a transparent layer, then onto the image
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay.paste(logo, (px, py), logo)
        return Image.alpha_composite(image, overlay)
