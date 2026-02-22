# PhotoWatermark Pro

A professional, fully offline desktop application for batch watermarking photos.
Built with **Python + PyQt5 + Pillow**.

---

## Stack Choice

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.10+** | Pillow ecosystem, rapid development, easy packaging |
| GUI | **PyQt5** | Native Windows look, drag-and-drop, rich widget set |
| Image processing | **Pillow** | Industry-standard, runs fully offline, no network calls |
| Packaging | **PyInstaller** | One-command `.exe` with no Python installation required |
| Future web migration | **Flask / FastAPI ready** | `WatermarkEngine.process()` is stateless — wrap in a route, done |

---

## Project Structure

```
watermark_app/
├── src/
│   ├── main.py                  # Entry point
│   ├── core/
│   │   ├── constants.py         # All magic values & defaults
│   │   ├── watermark_engine.py  # Stateless watermark processing (Pillow)
│   │   ├── image_processor.py   # File I/O, resize, format conversion
│   │   └── profile_manager.py   # JSON profile persistence
│   └── ui/
│       └── main_window.py       # Full PyQt5 UI + batch worker thread
├── profiles/                    # Created at runtime — saved profiles
├── requirements.txt
├── README.md
├── run.bat                      # Quick dev launcher
└── build.bat                    # Package as .exe
```

---

## Installation

### Prerequisites
- Windows 10/11
- Python 3.10 or later — https://www.python.org/downloads/

### Steps

```bat
# 1. Open a Command Prompt in the watermark_app folder
cd path\to\watermark_app

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python src\main.py
```

Or double-click **`run.bat`** after installing dependencies.

---

## Features

### Core Watermarking
- **Drag-and-drop** images or entire folders onto the file list
- Up to **3 lines of text** per watermark
- Font: Arial, Arial Bold, Times New Roman, Helvetica, Roboto, Verdana, Georgia, Calibri, Trebuchet MS
- Adjustable font size (8–400 pt), opacity (0–100%), line spacing
- **Colour picker** for watermark text
- **4 positions**: Lower Left, Lower Right, Center, Diagonal
- Adjustable margin padding
- Optional **shadow** and **outline** effects
- **Live preview** (auto-updates 400 ms after last change)
- **Batch processing** via background thread (UI stays responsive)
- Output saved to `~/watermarked_output/` (configurable)
- Originals are **never modified**

### Real Estate Mode
- 5 quick presets: Subtle Floor Style, Corner Professional, Center Promo, SOLD Badge, NEW LISTING Badge
- Auto-include agent name, PRC licence number, contact number, and date stamp

### Logo Support
- Upload a **PNG with transparency**
- Combine logo + text in one pass
- Adjustable logo size (5–50% of image width) and position

### Image Options
- Output format: **JPG, PNG, WebP**
- Quality slider (10–100)
- Optional **resize before watermarking** (max dimensions)
- **Smart opacity** — auto-boosts on bright images, softens on dark ones

### Profiles
- Save and load named watermark profiles (JSON)
- Settings auto-saved on close and restored on next launch
- Prefix / suffix naming for output files

---

## Packaging as a Standalone .exe

Double-click **`build.bat`** or run:

```bat
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "PhotoWatermark Pro" --add-data "profiles;profiles" src\main.py
```

The output is in `dist\PhotoWatermark Pro\`.
Share the entire folder — the `.exe` inside needs the supporting files.

> **Single-file build** (larger, slower startup):
> Add `--onefile` to the PyInstaller command above.

---

## Future Extension Points

The architecture is designed for easy migration:

### Web API (Flask / FastAPI)
```python
from core.watermark_engine import WatermarkEngine
from core.image_processor  import ImageProcessor

engine = WatermarkEngine()

@app.post("/watermark")
def watermark(file: UploadFile, config: WatermarkConfig):
    image  = ImageProcessor.load(file.file)
    result = engine.process(image, config.dict())
    # ... return result as file response
```

### Cloud Storage
Replace `ImageProcessor.load()` / `.save()` with S3 / GCS calls —
the engine code is unchanged.

### Authentication / Usage Tracking
Add middleware to the API layer without touching the core engine.

---

## Output Directory

By default, watermarked images are saved to:
```
C:\Users\<YourName>\watermarked_output\
```
Change this in the **Image Options** tab or via the `📂 Open Output` button.
