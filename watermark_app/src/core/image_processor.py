"""
image_processor.py — File I/O, format conversion, and resize helpers.

Kept separate from watermark_engine so image loading/saving can be swapped
independently (e.g., replaced with cloud-storage reads/writes later).
"""

import os
from PIL import Image

from .constants import FORMAT_PIL_NAMES, FORMAT_EXTENSIONS


class ImageProcessor:
    """
    Handles all disk I/O for images.

    All methods are static so they can be called without an instance,
    making them trivially usable from a CLI or API handler.
    """

    # ── Loading ───────────────────────────────────────────────────────────────

    @staticmethod
    def load(path: str) -> Image.Image:
        """
        Open an image from *path* and normalise it to RGBA.
        Raises IOError / FileNotFoundError on failure — callers should handle.
        """
        return Image.open(path).convert("RGBA")

    # ── Resizing ──────────────────────────────────────────────────────────────

    @staticmethod
    def resize(image: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """
        Resize *image* so it fits within max_w × max_h, preserving aspect ratio.
        Uses thumbnail() which modifies in place and returns None,
        so we return the mutated image for chaining convenience.
        """
        image.thumbnail((max_w, max_h), Image.LANCZOS)
        return image

    # ── Saving ────────────────────────────────────────────────────────────────

    @staticmethod
    def save(
        image:    Image.Image,
        out_path: str,
        fmt:      str = "JPG",
        quality:  int = 90,
    ) -> None:
        """
        Save *image* to *out_path* in the requested format.

        • Ensures the output directory exists.
        • Handles mode conversion (RGBA → RGB for JPEG).
        • Passes quality/optimize kwargs only where relevant.
        """
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        pil_fmt = FORMAT_PIL_NAMES.get(fmt.upper(), "JPEG")

        # JPEG cannot store alpha — flatten over white background
        if pil_fmt == "JPEG" and image.mode == "RGBA":
            bg = Image.new("RGB", image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[3])
            image = bg
        elif pil_fmt in ("PNG", "WEBP") and image.mode not in ("RGBA", "RGB"):
            image = image.convert("RGBA")
        elif image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        kwargs = {"format": pil_fmt}
        if pil_fmt in ("JPEG", "WEBP"):
            kwargs["quality"]   = quality
            kwargs["optimize"]  = True
        elif pil_fmt == "PNG":
            # PNG compression level: Pillow's compress_level is 0-9
            # We map the quality slider (10-100) to compress_level (9-0)
            level = max(0, min(9, 9 - round(quality / 11)))
            kwargs["compress_level"] = level
            kwargs["optimize"] = True

        image.save(out_path, **kwargs)

    # ── Output path builder ───────────────────────────────────────────────────

    @staticmethod
    def build_output_path(
        input_path: str,
        output_dir: str,
        prefix:     str,
        suffix:     str,
        fmt:        str,
    ) -> str:
        """
        Construct the output file path from components.

        Example:
          input_path = /photos/house.jpg
          prefix     = ""
          suffix     = "_watermarked"
          fmt        = "JPG"
          → /output/house_watermarked.jpg
        """
        base = os.path.splitext(os.path.basename(input_path))[0]
        ext  = FORMAT_EXTENSIONS.get(fmt.upper(), ".jpg")
        name = f"{prefix}{base}{suffix}{ext}"
        return os.path.join(output_dir, name)

    # ── Supported extensions ──────────────────────────────────────────────────

    SUPPORTED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".webp",
        ".bmp", ".tiff", ".tif", ".gif",
    }

    @classmethod
    def is_supported(cls, path: str) -> bool:
        """Return True if the file extension is a supported image format."""
        return os.path.splitext(path)[1].lower() in cls.SUPPORTED_EXTENSIONS
