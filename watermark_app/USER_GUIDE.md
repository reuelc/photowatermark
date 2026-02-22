# PhotoWatermark Pro — User Guide

> **Version 1.0** · Fully offline · Windows 10/11

---

## Table of Contents

1. [Installation](#1-installation)
2. [Quick Start (First 5 Minutes)](#2-quick-start-first-5-minutes)
3. [Easy Mode — Step by Step](#3-easy-mode--step-by-step)
4. [Advanced Mode — Full Reference](#4-advanced-mode--full-reference)
5. [Real Estate Mode](#5-real-estate-mode)
6. [Logo Watermarks](#6-logo-watermarks)
7. [Profiles — Save Your Settings](#7-profiles--save-your-settings)
8. [Output & File Naming](#8-output--file-naming)
9. [Packaging as a Standalone .exe](#9-packaging-as-a-standalone-exe)
10. [Troubleshooting](#10-troubleshooting)
11. [Keyboard Tips](#11-keyboard-tips)

---

## 1. Installation

### Step 1 — Install Python
Download Python **3.10 or later** from https://www.python.org/downloads/

> ⚠️ **Important:** During installation, check **"Add Python to PATH"**

### Step 2 — Run the Installer
Double-click **`install.bat`** inside the `watermark_app` folder.

What it does automatically:
- Creates an isolated virtual environment (`venv/`)
- Installs PyQt5 and Pillow
- Creates a **Desktop shortcut** and **Start Menu entry**
- Offers to launch the app immediately

### Step 3 — Launch
Use any of these options:
| Method | How |
|---|---|
| Desktop shortcut | Double-click **PhotoWatermark Pro** on your Desktop |
| Start Menu | Start → type "PhotoWatermark" |
| Batch file | Double-click **`run.bat`** in the app folder |
| Command line | `python src\main.py` (from inside `watermark_app\`) |

### Uninstalling
Double-click **`uninstall.bat`**. Your output photos and saved profiles are **never deleted**.

---

## 2. Quick Start (First 5 Minutes)

The fastest way to see the app working:

1. **Launch** the app → it opens in **Easy Mode** automatically
2. Click **⚡ Quick Start Demo** (no photos needed!)
   - The app generates a sample property photo
   - Applies your watermark instantly
   - Saves `quick_start_demo.jpg` to your output folder
   - Shows a success message with the file path
3. Open `C:\Users\YourName\watermarked_output\` to see the result
4. Adjust the text, size, and colour — click **⚡ Quick Start Demo** again to update

> 💡 The demo creates a synthetic house photo so you can preview your exact watermark style before touching your real photos.

---

## 3. Easy Mode — Step by Step

Easy Mode is the default. It shows three simple numbered steps:

```
┌───────────────────┬──────────────────────────┬──────────────┐
│ ① Add Your Photos │ ② Set Your Watermark     │ ③ Preview    │
│                   │                          │              │
│  Drop Zone        │  Watermark Text: [___]   │  [image]     │
│  [file list]      │  Font Size:  [slider]    │              │
│                   │  Opacity:    [slider]    │              │
│  [+ Add Images]   │  Colour:     [btn][■]    │              │
│  [Clear List]     │  Position:   ○○○○        │  [Refresh]   │
│                   │  Quick Presets:          │              │
│                   │  [Subtle][Pro][SOLD][NEW] │              │
│                   │                          │              │
│                   │  [⚡ Quick Start Demo]   │              │
│                   │  [▶ Watermark All Files] │              │
└───────────────────┴──────────────────────────┴──────────────┘
```

### Step ① — Add Your Photos
| Action | Result |
|---|---|
| Drag a **folder** from Explorer onto the file list | Adds all images in that folder |
| Drag individual **files** onto the list | Adds only those files |
| Click **＋ Add Images** | Opens a file picker dialog |
| Click **✕ Clear List** | Removes all files from the queue |

Supported formats: JPG, JPEG, PNG, WebP, BMP, TIFF

### Step ② — Set Your Watermark

| Control | What it does |
|---|---|
| **Watermark Text** | The text that appears on your photos. Use your brand, name, or copyright notice. |
| **Font Size** | Drag the slider left (smaller) or right (larger). Range: 12–120 pt. |
| **Opacity** | 10% = nearly invisible. 100% = fully solid. 60% is a good starting point. |
| **Colour** | Click "Pick Colour" to open a colour picker. The swatch shows your current colour. |
| **Position** | Lower Right (default), Lower Left, Center, or Diagonal across the image. |

### Quick Presets (one click to apply a full style)
| Preset | Best for |
|---|---|
| **Subtle** | Quiet branding, floor plans, low-key watermarks |
| **Professional** | Standard professional real estate photos |
| **Center Promo** | Promotional images, marketing materials |
| **SOLD** | Mark sold properties (large bold red text) |
| **NEW LISTING** | New listing announcements (bold gold text) |

### Step ③ — Preview
- Click any file in the list on the left → preview updates automatically
- Click **🔄 Refresh Preview** at any time
- The preview is a thumbnail — actual output is full resolution

### Watermark All Files
Click **▶ Watermark All Files** to process everything in the list.
- A progress bar appears at the bottom
- Original files are **never modified**
- Output saved to `C:\Users\YourName\watermarked_output\`
- A summary dialog shows how many succeeded/failed

---

## 4. Advanced Mode — Full Reference

Click **⚙ Advanced** in the top toolbar to switch to Advanced Mode.

> 💡 Advanced Mode remembers your last-used settings and restores them on next launch.

### Toolbar (Advanced Mode)
| Button | Function |
|---|---|
| **＋ Add Files** | Open file picker |
| **✕ Clear All** | Remove all queued files |
| **📂 Open Output** | Open the output folder in Explorer |
| **👁 Preview** | Force-refresh the preview |
| **▶ Batch Watermark** | Process all files |

### ✏ Watermark Tab

#### Text Lines
Up to **3 independent text lines** on the watermark. Leave Line 2 and Line 3 empty if you only need one line.

#### Font Settings
| Setting | Options |
|---|---|
| Font | Arial, Arial Bold, Times New Roman, Helvetica, Roboto, Verdana, Georgia, Calibri, Trebuchet MS |
| Size | 8–400 pt |
| Colour | Full colour picker (any hex colour) |
| Opacity | 0–100% |
| Line Spacing | 1.0x (tight) to 3.0x (very loose) |

#### Position
| Position | Where it appears |
|---|---|
| Lower Right | Bottom-right corner — most common for professional photos |
| Lower Left | Bottom-left corner |
| Center | Centered on the image |
| Diagonal | 45° diagonal across the full image |

#### Margin
Extra padding from the edge of the image. 20 px is the default.

#### Effects
| Effect | Description |
|---|---|
| **Shadow** | Adds a dark semi-transparent shadow behind the text for readability on light images |
| **Outline** | Draws a thin dark border around each letter — useful on busy backgrounds |

### 🏠 Real Estate Tab
See [Section 5 — Real Estate Mode](#5-real-estate-mode) below.

### 🖼 Logo Tab
See [Section 6 — Logo Watermarks](#6-logo-watermarks) below.

### 🔧 Image Options Tab

| Setting | Description |
|---|---|
| **Format** | JPG (smallest file), PNG (lossless, supports transparency), WebP (modern, great quality/size) |
| **Quality** | 10–100. JPG/WebP: lower = smaller file, more compression. PNG: affects compression level. |
| **Resize Before Watermark** | Shrink photos to max dimensions before watermarking. Useful for web delivery. |
| **Smart Opacity** | Automatically increases opacity on bright images and decreases on dark images so the watermark is always readable. |
| **Output Directory** | Where watermarked files are saved. Default: `~/watermarked_output/` |
| **Prefix** | Text added before the filename. Example: `wm_` → `wm_photo1.jpg` |
| **Suffix** | Text added after the filename. Default: `_watermarked` → `photo1_watermarked.jpg` |

### 💾 Profiles Tab
See [Section 7 — Profiles](#7-profiles--save-your-settings) below.

---

## 5. Real Estate Mode

Switch to **Advanced Mode** → click the **🏠 Real Estate** tab.

### Quick Presets

| Preset | Style Description |
|---|---|
| **Subtle Floor Style** | Small semi-transparent text at lower-left. Minimal, classy. |
| **Corner Professional** | Medium white text at lower-right with shadow. Industry standard. |
| **Center Promo** | Large outlined text centered on the image. Great for marketing. |
| **SOLD Badge Mode** | Huge bold red "SOLD" centered on the image with outline. |
| **NEW LISTING Badge Mode** | Bold gold "NEW LISTING" at lower-left. High visibility. |

> Clicking a preset updates all font, size, opacity, colour and position settings at once. You can then fine-tune individual settings.

### Agent Information Fields
These fields auto-add extra lines to your watermark:

| Field | Example Output |
|---|---|
| Agent Name | `Maria Santos` |
| PRC Licence # | `PRC #0012345` |
| Contact Number | `+63 917 123 4567` |
| Date Stamp | `February 22, 2026` |

Leave a field empty to skip it. Combine with Line 1–3 text as needed.

---

## 6. Logo Watermarks

Advanced Mode → **🖼 Logo** tab.

1. Click **📂 Browse…** → select a **PNG file with a transparent background**
2. Set the **Logo Size** (5–50% of image width). 20% is a good default.
3. Choose the **Logo Position** (Lower Left, Lower Right, Center, Diagonal)
4. The logo uses the same **Opacity** setting as the text watermark
5. Logo and text watermarks are both applied in a single pass
6. Click **✕ Remove Logo** to disable logo watermarking

> 💡 **Tip:** Export your logo from any design app as PNG-24 with transparency for best results.

---

## 7. Profiles — Save Your Settings

Advanced Mode → **💾 Profiles** tab.

### Saving a Profile
1. Adjust all your watermark settings as desired
2. Type a name in the "Profile name…" field (e.g. `My Brand`, `Real Estate PH`)
3. Click **💾 Save**

### Loading a Profile
1. Click the profile name in the list
2. Click **📂 Load**
3. All settings are restored instantly

### Deleting a Profile
1. Select the profile in the list
2. Click **🗑 Delete** → confirm

### Auto-save
Your settings are **automatically saved** when you close the app and **restored** on next launch — even without manually saving a profile.

### Profile Files
Profiles are stored as readable JSON files in:
```
watermark_app\profiles\
```
You can copy these files to share settings between computers.

---

## 8. Output & File Naming

### Where files are saved
By default: `C:\Users\YourName\watermarked_output\`

Change it in Advanced Mode → **🔧 Image Options** → Output Dir.

### File naming
| Setting | Example | Result |
|---|---|---|
| Suffix `_watermarked` (default) | `photo1.jpg` | `photo1_watermarked.jpg` |
| Prefix `wm_`, no suffix | `photo1.jpg` | `wm_photo1.jpg` |
| Prefix `approved_`, Suffix `_v2` | `photo1.jpg` | `approved_photo1_v2.jpg` |

### Original files
**Original images are never touched.** The app always reads from the source and writes to the output folder.

---

## 9. Packaging as a Standalone .exe

Share the app with anyone — no Python installation needed on their machine.

### Build the .exe
Double-click **`build.bat`** or run:
```bat
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "PhotoWatermark Pro" --add-data "profiles;profiles" src\main.py
```

Output: `dist\PhotoWatermark Pro\PhotoWatermark Pro.exe`

### Share it
Zip and share the entire `dist\PhotoWatermark Pro\` folder.
The `.exe` inside needs all the companion files in that folder.

### Single-file build (optional)
Add `--onefile` for a single portable `.exe` (slower to start, but easier to share):
```bat
pyinstaller --onefile --windowed --name "PhotoWatermark Pro" src\main.py
```

---

## 10. Troubleshooting

### App won't start
```
"python is not recognized..."
```
**Fix:** Re-run the Python installer, check "Add Python to PATH", then restart your PC.

---

```
ImportError: No module named 'PyQt5'
```
**Fix:** Run `pip install PyQt5 Pillow` or re-run `install.bat`.

---

### Preview shows "Preview error"
- The selected file may be corrupted or in an unsupported format
- Try selecting a different file

### Watermark text not visible
- Increase **Opacity** (try 70–80%)
- Enable **Shadow** or **Outline** effects
- Change the colour to contrast with your photos (white on dark, dark on light)
- Enable **Smart Opacity** (Advanced → Image Options) to auto-adjust

### Font looks wrong / fallback used
Some fonts (Roboto, Helvetica) may not be installed on your system.
- **Fix:** Install the font via Windows Settings → Fonts
- Fallback: Arial is always used if the requested font isn't found

### Output folder not opening
The output folder is created automatically on first use at:
`C:\Users\YourName\watermarked_output\`

### Files processed but output folder is empty
Check that the **Output Dir** path exists. In Advanced Mode → Image Options → Output Dir. Click **📂 Open Output** to verify.

---

## 11. Keyboard Tips

| Key | Action |
|---|---|
| `Ctrl+A` | Select all files in the file list |
| `Delete` | Remove selected file from list (Advanced Mode) |
| `Tab` | Move between input fields |
| `Enter` | Confirm a text field and move to next |

---

## Support

- **Output folder:** `C:\Users\YourName\watermarked_output\`
- **Profiles folder:** `watermark_app\profiles\`
- **Logs:** Check the status bar at the bottom of the app window for per-file results

---

*PhotoWatermark Pro v1.0 — Built with Python, PyQt5, and Pillow*
