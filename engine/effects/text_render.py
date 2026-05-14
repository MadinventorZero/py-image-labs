import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from engine.models import TaglineConfig

GOTHIC_FONT_CACHE = Path(".gothic_font_cache/UnifrakturMaguntia.ttf")
GOTHIC_FONT_URL = (
    "https://fonts.gstatic.com/s/unifrakturmaguntia/v22/"
    "WWXPlieVYwiGNomYU-ciRLRvEmK7oaVunw.ttf"
)


def _fetch_gothic_font() -> "Path | None":
    if GOTHIC_FONT_CACHE.exists():
        return GOTHIC_FONT_CACHE
    try:
        GOTHIC_FONT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        print("  Downloading gothic font (first run only)...")
        urllib.request.urlretrieve(GOTHIC_FONT_URL, GOTHIC_FONT_CACHE)
        return GOTHIC_FONT_CACHE
    except Exception as e:
        print(f"  Warning: could not download gothic font ({e}), falling back.")
        return None


def get_font(size: int) -> ImageFont.FreeTypeFont:
    gothic_candidates = [
        str(GOTHIC_FONT_CACHE),
        "/Library/Fonts/OldLondon.ttf",
        "/Library/Fonts/Canterbury.ttf",
        "/Windows/Fonts/OLDENGL.TTF",
        "/usr/share/fonts/truetype/unifraktur-maguntia/UnifrakturMaguntia.ttf",
    ]
    system_fallbacks = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Windows/Fonts/impact.ttf",
    ]
    for path in gothic_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    fetched = _fetch_gothic_font()
    if fetched:
        try:
            return ImageFont.truetype(str(fetched), size)
        except (IOError, OSError):
            pass
    for path in system_fallbacks:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _draw_word(
    draw: ImageDraw.Draw,
    word: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    text_color: tuple[int, int, int],
    shadow_color: tuple[int, int, int],
    shadow: bool = True,
    glow: bool = True,
) -> None:
    if shadow:
        draw.text((x + 4, y + 5), word, font=font, fill=shadow_color + (220,))
    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((x + ox, y + oy), word, font=font, fill=(0, 0, 0, 200))
    if glow:
        draw.text((x, y), word, font=font, fill=(255, 200, 80, 80))
    draw.text((x, y), word, font=font, fill=text_color + (255,))


def compute_text_anchor_y(
    tag: TaglineConfig,
    canvas_h: int,
    subject_ly: int,
    subject_lh: int,
) -> int:
    if tag.anchor == "top":
        base_y = int(canvas_h * 0.06)
    elif tag.anchor == "bottom":
        base_y = canvas_h - int(canvas_h * 0.22)
    else:
        base_y = subject_ly + subject_lh // 2
    return base_y + int(canvas_h * tag.offset_y)


def build_word_layout(
    tag: TaglineConfig,
    font: ImageFont.FreeTypeFont,
    canvas_w: int,
    canvas_h: int,
    subject_ly: int,
    subject_lh: int,
    font_size: int,
) -> list[tuple[int, int, str]]:
    words     = tag.text.split()
    line_h    = int(font_size * 1.30)
    stack_h   = len(words) * line_h
    anchor_y  = compute_text_anchor_y(tag, canvas_h, subject_ly, subject_lh)
    stack_top = anchor_y - stack_h // 2
    probe     = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    layout    = []
    for idx, word in enumerate(words):
        bb = probe.textbbox((0, 0), word, font=font)
        ww = bb[2] - bb[0]
        if tag.align == "left":
            wx = int(canvas_w * 0.05)
        elif tag.align == "right":
            wx = canvas_w - int(canvas_w * 0.05) - ww
        else:
            wx = (canvas_w - ww) // 2
        wy = stack_top + idx * line_h
        layout.append((wx, wy, word))
    return layout
