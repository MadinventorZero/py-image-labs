# Brand Image Generator — How-To Guide

## What It Does

Generates up to three animated GIF brand assets from a single source photo via a desktop GUI:

| Output file | Size | Use |
|---|---|---|
| `brand_youtube_thumbnail.gif` | 1280×720 | YouTube thumbnail |
| `brand_channel_art.gif` | 2560×1440 | YouTube channel banner |
| `brand_podcast_square.gif` | 3000×3000 | Podcast cover art |

Each GIF composites the isolated subject over a dark background with any combination of: animated smoke/mist, distant lightning strike, and gothic gold text.

---

## Requirements

Python 3.10+ with the following packages:

```bash
pip install rembg pillow numpy PySimpleGUI onnxruntime
```

> **Note:** `rembg` pulls in `onnxruntime` (a large download on first install). This is normal.

---

## Quick Start

1. Run the script:
   ```bash
   python brand_image_gen.py
   ```
2. The GUI opens. Work through the four sections top to bottom.
3. Click **Review & Confirm ›** to preview your selections, then **Run** to render.
4. On first run, the gothic font (UnifrakturMaguntia) is downloaded automatically and cached in `.gothic_font_cache/`. Subsequent runs skip the download.
5. Output GIFs appear in the folder you selected.

---

## GUI Walkthrough

```
┌─────────────────────────────────────────────────────┐
│  Brand Image Generator                              │
├─────────────────────────────────────────────────────┤
│  Input File      [Browse…]  path/to/photo.jpg       │
│  Output Folder   [Browse…]  path/to/output/         │
├─────────────────────────────────────────────────────┤
│  Asset Sizes  (all checked by default)              │
│     ☑ YouTube Thumbnail  1280 × 720                 │
│     ☑ Channel Art        2560 × 1440                │
│     ☑ Podcast Square     3000 × 3000                │
├─────────────────────────────────────────────────────┤
│  Processing Layers                                  │
│     ☑ Remove background (rembg)                     │
│     ☑ Smoke / mist animation                        │
│     ☑ Lightning strike                              │
│     ☑ Gothic text overlay                           │
│        Tagline: [Thunder Road Rails          ]      │
│        (field disabled when checkbox is off)        │
├─────────────────────────────────────────────────────┤
│  [ Cancel ]              [ Review & Confirm › ]     │
└─────────────────────────────────────────────────────┘
```

The **Review & Confirm** dialog shows a full summary of all selections. **‹ Back** returns to the main form without losing any values; **Run** starts processing.

---

## Configuration

Most settings are controlled through the GUI. Advanced defaults live in the `RenderConfig` dataclass at the top of `brand_image_gen.py`:

| Field | Default | Description |
|---|---|---|
| `bg_color` | `(10, 8, 14)` | Background RGB — near-black warm tint |
| `smoke_tint` | `(180, 185, 200)` | Smoke particle color |
| `text_color` | `(220, 190, 120)` | Main text color — antique gold |
| `shadow_color` | `(0, 0, 0)` | Text drop-shadow color |
| `frames` | `48` | Animation frames per loop |
| `frame_ms` | `60` | Milliseconds per frame (~16 fps) |

### Making the animation faster or slower

Edit the defaults in `RenderConfig`:
- Fewer frames → smaller file, choppier motion: `frames: int = 24`
- Slower playback: `frame_ms: int = 100`  (100 ms = 10 fps)

### Adjusting text color

`text_color` is an RGB tuple. Examples:

```python
text_color: tuple = (255, 255, 255)   # white
text_color: tuple = (220, 190, 120)   # antique gold (default)
text_color: tuple = (200, 50, 50)     # blood red
```

---

## Font Behavior

The script tries fonts in this order:

1. **Cached gothic font** — `.gothic_font_cache/UnifrakturMaguntia.ttf` (downloaded once)
2. **Locally installed gothic fonts** — OldLondon, Canterbury, Old English (if present in system font library)
3. **Auto-download** — fetches UnifrakturMaguntia from Google Fonts on first run
4. **System fallbacks** — Impact, Helvetica, DejaVu Sans Bold
5. **PIL default** — always available, no TrueType styling

To use your own font, drop the `.ttf` file into the project folder and add its path to the `gothic_candidates` list in `get_font()`.

---

## How the Pipeline Works

```
Source photo
    │
    ▼
[rembg] background removal
    │
    ▼
Rotate + tight-crop to subject
    │
    ▼
For each output size:
    ├── Scale lantern to canvas
    ├── For each frame:
    │       ├── Dark background
    │       ├── Animated smoke layer (Perlin-approximated particles)
    │       ├── Lantern composite
    │       └── Gothic text with outline + glow
    └── Save as animated GIF
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'PySimpleGUI'`**
Run `pip install PySimpleGUI onnxruntime rembg pillow numpy` and try again.

**Font looks plain / not gothic**
The gothic font download may have failed (check network access). You can manually place any blackletter `.ttf` file at `.gothic_font_cache/UnifrakturMaguntia.ttf`.

**GIF files are very large**
Reduce `FRAMES` (e.g. `24`) or lower the canvas size by editing the `SIZES` dictionary.

**Image appears rotated**
The script applies a `-90°` rotation correction for the default source photo. If your photo is already upright, remove or adjust `img.rotate(-90, expand=True)` in `isolate_lantern()`.
