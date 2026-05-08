#!/usr/bin/env python3
"""
brand_image_gen.py

GUI-driven branded animated image generator.
Produces animated GIFs in up to three sizes from a single source photo.

Usage:
    python brand_image_gen.py

Requirements:
    pip install rembg[cpu] pillow numpy pywebview
"""

import io
import math
import random
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import base64
import threading
import webview

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from rembg import remove, new_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_SIZES = {
    "youtube_thumbnail": (1280, 720),
    "channel_art":       (2560, 1440),
    "podcast_square":    (3000, 3000),
}

FRAMES_OVERRIDE = {"podcast_square": 24}

GOTHIC_FONT_CACHE = Path(".gothic_font_cache/UnifrakturMaguntia.ttf")
GOTHIC_FONT_URL = (
    "https://fonts.gstatic.com/s/unifrakturmaguntia/v22/"
    "WWXPlieVYwiGNomYU-ciRLRvEmK7oaVunw.ttf"
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TaglineConfig:
    text:          str   = "Thunder Road Rails"
    anchor:        str   = "center"       # "top", "center", "bottom"
    offset_y:      float = 0.0            # fractional offset from anchor (-0.5–0.5)
    font_size_pct: float = 0.075          # fraction of canvas height
    align:         str   = "center"       # "left", "center", "right"
    orientation:   str   = "horizontal"   # "horizontal", "vertical_cw"
    text_color:    tuple = (220, 190, 120)
    shadow:        bool  = True
    glow:          bool  = True


@dataclass
class RenderConfig:
    source:     Path
    output_dir: Path
    tagline_cfg: TaglineConfig = field(default_factory=TaglineConfig)
    bg_color:   tuple = (10, 8, 14)
    smoke_tint: tuple = (45, 48, 58)
    shadow_color: tuple = (0, 0, 0)
    frames:     int   = 48
    frame_ms:   int   = 60
    # image processing
    remove_bg:    bool  = True
    crop:         bool  = True
    crop_padding: float = 0.12
    rotate:       int   = 0
    resize_pct:   int   = 100
    # animation layers
    add_smoke:          bool  = True
    add_lightning:      bool  = True
    lightning_mode:     str   = "simple"  # "simple"|"ground_strike"|"atmospheric"|"full_storm"
    n_bolts:            int   = 2         # ground strikes (ground/storm) or spines (atmospheric)
    branch_depth:       int   = 4         # recursion depth for all atmospheric modes
    fork_concentration: int   = 3         # max forks per branch junction (1–6)
    subbranch_length:   float = 0.40      # sub-branch length relative to parent (0.2–0.7)
    add_flash:          bool  = True
    add_text:      bool  = True
    add_embers:    bool  = False
    add_rain:      bool  = False
    add_vignette:  bool  = True
    add_scanlines: bool  = False
    output_static: bool  = False
    # Tone & stylization (applied to subject / full frame)
    tone_mode:    str   = "color"   # "color"|"bw"|"sepia"|"negative"|"solarize"|"historical"
    stylize_mode: str   = "none"    # "none"|"cartoon"|"watercolor"|"oil"|"sketch"
    # Optical post-processing
    add_chroma_aberration: bool  = False
    chroma_shift:          int   = 5
    add_bloom:             bool  = False
    bloom_radius:          int   = 12
    bloom_strength:        float = 0.40
    # Per-frame / animated
    add_film_grain:       bool  = False
    film_grain_intensity: float = 0.04
    add_snow:             bool  = False
    add_holo:             bool  = False   # holographic shimmer on subject
    add_bokeh:            bool  = False   # blur background layers behind subject
    bokeh_radius:         int   = 18
    sizes: dict = field(default_factory=lambda: dict(ALL_SIZES))


# ---------------------------------------------------------------------------
# pywebview GUI — web wizard
# ---------------------------------------------------------------------------

_progress_state: dict = {"progress": 0, "done": False, "error": None, "gif_b64": None}
_window = None


class Api:
    def pick_image(self):
        paths = _window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Images (*.jpg;*.jpeg;*.png;*.webp)",),
        )
        return paths[0] if paths else None

    def pick_output_dir(self):
        paths = _window.create_file_dialog(webview.FOLDER_DIALOG)
        return paths[0] if paths else None

    def get_image_preview(self, path: str):
        try:
            img = Image.open(path)
            img.thumbnail((320, 180), Image.LANCZOS)
            canvas = Image.new("RGB", (320, 180), (20, 22, 27))
            ox = (320 - img.width) // 2
            oy = (180 - img.height) // 2
            if img.mode == "RGBA":
                canvas.paste(img, (ox, oy), img)
            else:
                canvas.paste(img.convert("RGB"), (ox, oy))
            buf = io.BytesIO()
            canvas.save(buf, "JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return None

    def run_generation(self, config: dict) -> dict:
        global _progress_state
        _progress_state = {"progress": 0, "done": False, "error": None, "gif_b64": None}

        def _run():
            global _progress_state
            try:
                cfg = _build_render_config(config)
                run_pipeline(cfg, progress_cb=_set_progress)
                gif_b64 = _get_preview_gif(cfg)
                _progress_state = {"progress": 100, "done": True, "error": None, "gif_b64": gif_b64}
            except Exception as e:
                _progress_state = {"progress": 0, "done": True, "error": str(e), "gif_b64": None}

        threading.Thread(target=_run, daemon=True).start()
        return {"status": "started"}

    def get_progress(self) -> dict:
        return dict(_progress_state)


def _set_progress(n: int) -> None:
    global _progress_state
    _progress_state["progress"] = n


def _get_preview_gif(cfg: "RenderConfig"):
    try:
        first_size = next(iter(cfg.sizes))
        gif_path = cfg.output_dir / f"brand_{first_size}.gif"
        if gif_path.exists():
            img = Image.open(gif_path)
            img.thumbnail((480, 270), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass
    return None


def _build_render_config(config: dict) -> "RenderConfig":
    ip = config.get("imgProc", {})
    ly = config.get("layers", {})
    td = config.get("tagline", {})

    tag = TaglineConfig(
        text          = td.get("text", "Thunder Road Rails"),
        anchor        = td.get("anchor", "center"),
        offset_y      = float(td.get("offset_y", 0.0)),
        font_size_pct = float(td.get("font_size_pct", 0.075)),
        align         = td.get("align", "center"),
        orientation   = td.get("orientation", "horizontal"),
        text_color    = tuple(td.get("text_color", [220, 190, 120])),
        shadow        = bool(td.get("shadow", True)),
        glow          = bool(td.get("glow", True)),
    )

    sizes_flags   = config.get("sizes", {})
    selected_sizes = {k: v for k, v in ALL_SIZES.items() if sizes_flags.get(k, True)}

    lightning_mode = ly.get("lightning_mode", "simple")
    add_lightning  = lightning_mode != "off"

    return RenderConfig(
        source        = Path(config["inputPath"]),
        output_dir    = Path(config["outputDir"]),
        tagline_cfg   = tag,
        remove_bg     = bool(ip.get("remove_bg", True)),
        crop          = bool(ip.get("crop_to_subject", True)),
        crop_padding  = float(ip.get("crop_padding", 0.12)),
        rotate        = int(ip.get("rotate_degrees", 0)),
        resize_pct    = int(ip.get("resize_pct", 100)),
        add_smoke           = bool(ly.get("add_smoke", True)),
        add_lightning       = add_lightning,
        lightning_mode      = lightning_mode if add_lightning else "simple",
        n_bolts             = int(ly.get("n_bolts", 2)),
        branch_depth        = int(ly.get("branch_depth", 4)),
        fork_concentration  = int(ly.get("fork_concentration", 3)),
        subbranch_length    = float(ly.get("subbranch_length", 0.40)),
        add_flash           = bool(ly.get("add_flash", True)),
        add_text      = bool(ly.get("add_text", True)),
        add_embers    = bool(ly.get("add_embers", False)),
        add_rain      = bool(ly.get("add_rain", False)),
        add_vignette  = bool(ly.get("add_vignette", True)),
        add_scanlines = bool(ly.get("add_scanlines", False)),
        output_static = bool(config.get("output_static", False)),
        tone_mode     = ly.get("tone_mode", "color"),
        stylize_mode  = ly.get("stylize_mode", "none"),
        add_chroma_aberration = bool(ly.get("add_chroma_aberration", False)),
        add_bloom             = bool(ly.get("add_bloom", False)),
        add_film_grain        = bool(ly.get("add_film_grain", False)),
        add_snow              = bool(ly.get("add_snow", False)),
        add_holo              = bool(ly.get("add_holo", False)),
        add_bokeh             = bool(ly.get("add_bokeh", False)),
        sizes         = selected_sizes,
    )


# ---------- pipeline ----------







# ---------------------------------------------------------------------------
# Subject isolation
# ---------------------------------------------------------------------------

def _rembg_session():
    try:
        session = new_session("birefnet-general")
        print("  Using BiRefNet model for subject extraction.")
        return session
    except Exception as e:
        print(f"  BiRefNet unavailable ({e}), falling back to u2net.")
        return new_session("u2net")


def isolate_lantern(cfg: RenderConfig) -> Image.Image:
    if cfg.remove_bg:
        print(f"  Removing background from {cfg.source.name}...")
        raw     = cfg.source.read_bytes()
        session = _rembg_session()
        result  = remove(raw, session=session)
        img     = Image.open(io.BytesIO(result)).convert("RGBA")
    else:
        print(f"  Loading {cfg.source.name} (background removal skipped)...")
        img = Image.open(cfg.source).convert("RGBA")
    return img


def crop_to_subject(img: Image.Image, padding: float = 0.12) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    pw = int((r - l) * padding)
    ph = int((b - t) * padding)
    return img.crop((
        max(0, l - pw), max(0, t - ph),
        min(img.width, r + pw), min(img.height, b + ph),
    ))


def apply_image_processing(img: Image.Image, cfg: RenderConfig) -> Image.Image:
    if cfg.crop:
        img = crop_to_subject(img, padding=cfg.crop_padding)
    if cfg.rotate:
        img = img.rotate(-cfg.rotate, expand=True)
    if cfg.resize_pct != 100:
        nw = max(1, int(img.width  * cfg.resize_pct / 100))
        nh = max(1, int(img.height * cfg.resize_pct / 100))
        img = img.resize((nw, nh), Image.LANCZOS)
    if cfg.stylize_mode != "none":
        img = apply_stylize(img, cfg.stylize_mode)
    return img


# ---------------------------------------------------------------------------
# Smoke / mist
# ---------------------------------------------------------------------------

def _perlin_offset(i: int, t: float, scale: float = 1.0) -> float:
    return (
        math.sin(i * 1.3 + t * 2.1) * 0.5
        + math.sin(i * 2.7 + t * 1.4) * 0.3
        + math.sin(i * 0.9 + t * 3.3) * 0.2
    ) * scale


def make_smoke_frame(
    canvas_size: tuple[int, int],
    t: float,
    x_min: float,
    x_max: float,
    origin_y: float,
    smoke_tint: tuple[int, int, int],
    num_particles: int = 220,
) -> Image.Image:
    w, h = canvas_size
    r, g, b = smoke_tint

    rng   = random.Random(99)
    births       = [(rng.uniform(x_min, x_max), rng.random()) for _ in range(num_particles)]
    grain_births = [(rng.uniform(x_min, x_max), rng.random()) for _ in range(num_particles * 3)]

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    for i, (birth_x, phase_off) in enumerate(births):
        phase   = (t + phase_off) % 1.0
        lateral = _perlin_offset(i, t, w * 0.06) * (0.3 + phase * 0.7)
        wobble_y = _perlin_offset(i + 100, t * 0.8, h * 0.02)
        px = birth_x + lateral
        py = origin_y - phase * h * 0.70 + wobble_y
        if phase < 0.12:
            alpha = int((phase / 0.12) * 140)
        elif phase > 0.70:
            alpha = int(((1.0 - phase) / 0.30) * 140)
        else:
            alpha = 140
        alpha  = max(0, min(140, alpha))
        radius = int(w * 0.018 + phase * w * 0.048)
        draw.ellipse([px - radius, py - radius, px + radius, py + radius],
                     fill=(r, g, b, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=max(2, int(w * 0.006))))

    grain = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grain)
    for i, (birth_x, phase_off) in enumerate(grain_births):
        phase_g  = (t * 1.5 + phase_off) % 1.0
        lateral_g = _perlin_offset(i + 300, t * 1.8, w * 0.025) * (0.2 + phase_g * 0.5)
        gx = birth_x + lateral_g
        gy = origin_y - phase_g * h * 0.65 + _perlin_offset(i + 400, t * 1.2, h * 0.015)
        gr = max(1, int(w * 0.0025 + phase_g * w * 0.004))
        if phase_g < 0.10:
            ga = int((phase_g / 0.10) * 110)
        elif phase_g > 0.75:
            ga = int(((1.0 - phase_g) / 0.25) * 110)
        else:
            ga = 110
        ga = max(0, min(110, ga))
        gdraw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=(r, g, b, ga))
    grain = grain.filter(ImageFilter.GaussianBlur(radius=max(1, int(w * 0.0015))))

    return Image.alpha_composite(layer, grain)


# ---------------------------------------------------------------------------
# Flash
# ---------------------------------------------------------------------------

_FLASH_COLOR    = (200, 220, 255)
_FLASH_ENVELOPE = [1.0, 0.60, 0.30, 0.12, 0.04]


def make_flash_layer(canvas_size: tuple[int, int], alpha: float) -> Image.Image:
    if alpha <= 0:
        return Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    r, g, b = _FLASH_COLOR
    a = max(0, min(255, int(210 * alpha)))
    return Image.new("RGBA", canvas_size, (r, g, b, a))


# ---------------------------------------------------------------------------
# Lightning — simple bolt
# ---------------------------------------------------------------------------

def _subdivide_bolt(
    p0: tuple[float, float],
    p1: tuple[float, float],
    roughness: float,
    rng: random.Random,
    depth: int = 5,
) -> list[tuple[float, float]]:
    if depth == 0:
        return [p0, p1]
    mx = (p0[0] + p1[0]) / 2 + rng.gauss(0, roughness)
    my = (p0[1] + p1[1]) / 2
    left  = _subdivide_bolt(p0, (mx, my), roughness * 0.6, rng, depth - 1)
    right = _subdivide_bolt((mx, my), p1, roughness * 0.6, rng, depth - 1)
    return left[:-1] + right


def generate_lightning_bolt(
    canvas_size: tuple[int, int],
    seed: int = 42,
) -> list[list[tuple[float, float]]]:
    w, h  = canvas_size
    rng   = random.Random(seed)
    start = (w * rng.uniform(0.68, 0.80), h * rng.uniform(0.02, 0.10))
    end   = (w * rng.uniform(0.60, 0.88), h * rng.uniform(0.50, 0.65))
    roughness = w * 0.04
    main  = _subdivide_bolt(start, end, roughness, rng, depth=5)
    bolts = [main]

    n_branches = rng.randint(2, 3)
    interior   = main[3:-3]
    fork_points = rng.sample(interior, min(n_branches, len(interior)))
    for fp in fork_points:
        branch_end = (
            fp[0] + rng.uniform(-w * 0.12, w * 0.15),
            fp[1] + h * rng.uniform(0.10, 0.25),
        )
        branch = _subdivide_bolt(fp, branch_end, roughness * 0.45, rng, depth=3)
        bolts.append(branch)

    return bolts


def make_lightning_layer(
    canvas_size: tuple[int, int],
    bolts: list[list[tuple[float, float]]],
    alpha: float,
) -> Image.Image:
    w, _ = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0:
        return layer

    # Real lightning channels are a few centimetres wide — use a thin base so
    # the perceived width comes from the blurred corona halo, not stroke weight.
    base_w = max(1, int(w * 0.0015))

    for bolt_idx, points in enumerate(bolts):
        scale = 1.0 if bolt_idx == 0 else 0.45
        segs  = list(zip(points, points[1:]))

        # Outer diffuse corona — electric blue glow
        g1 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d1 = ImageDraw.Draw(g1)
        for p0, p1 in segs:
            d1.line([p0, p1],
                    fill=(60, 120, 255, int(45 * alpha * scale)),
                    width=max(1, int(base_w * 5 * scale)))
        g1 = g1.filter(ImageFilter.GaussianBlur(radius=max(4, int(w * 0.010))))
        layer = Image.alpha_composite(layer, g1)

        # Inner blue-white halo
        g2 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d2 = ImageDraw.Draw(g2)
        for p0, p1 in segs:
            d2.line([p0, p1],
                    fill=(200, 225, 255, int(130 * alpha * scale)),
                    width=max(1, int(base_w * 2 * scale)))
        g2 = g2.filter(ImageFilter.GaussianBlur(radius=max(1, int(w * 0.004))))
        layer = Image.alpha_composite(layer, g2)

        # Hair-thin white core
        core = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        dc   = ImageDraw.Draw(core)
        for p0, p1 in segs:
            dc.line([p0, p1],
                    fill=(245, 250, 255, int(255 * alpha * scale)),
                    width=max(1, int(base_w * scale)))
        layer = Image.alpha_composite(layer, core)

    return layer


# ---------------------------------------------------------------------------
# Lightning — atmospheric multi-branch tree
# ---------------------------------------------------------------------------

def generate_ground_strike(
    canvas_size: tuple[int, int],
    seed: int,
    origin_x_frac: float = 0.5,
    depth: int = 4,
    roughness_frac: float = 0.035,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], tuple[float, float]]:
    """
    Cloud-to-ground strike. Tall vertical channel reaching close to the bottom
    of the canvas with upward/lateral sub-branching.

    Returns (segments, ground_contact_point).
    level == depth is the main channel; level 1 is the finest sub-branches.
    """
    w, h      = canvas_size
    rng       = random.Random(seed)
    roughness = w * roughness_frac
    start     = (w * origin_x_frac, h * rng.uniform(0.0, 0.06))
    end       = (w * origin_x_frac + rng.uniform(-w * 0.07, w * 0.07),
                 h * rng.uniform(0.84, 0.96))   # reaches near ground
    segments: list[dict] = []

    def recurse(p0, p1, level, r):
        chain = _subdivide_bolt(p0, p1, r, rng, depth=5)
        segments.append({"path": chain, "level": level})
        if level <= 1:
            return
        # fork_concentration controls max forks; reduce at lower levels for taper
        n_forks  = max(1, min(fork_concentration,
                               rng.randint(1, fork_concentration + 1) - (depth - level)))
        guard    = max(1, len(chain) // 6)
        interior = chain[guard:-guard]
        if not interior:
            return
        fork_pts = rng.sample(interior, min(n_forks, len(interior)))
        for fp in fork_pts:
            angle      = rng.uniform(math.radians(20), math.radians(70))
            sign       = rng.choice([-1, 1])
            length     = math.dist(p0, p1) * rng.uniform(
                             subbranch_length * 0.5, subbranch_length)
            branch_end = (fp[0] + math.sin(angle) * sign * length,
                          fp[1] + math.cos(angle) * length)
            recurse(fp, branch_end, level - 1, r * 0.55)

    recurse(start, end, depth, roughness)
    return segments, end


def generate_atmospheric_intracloud(
    canvas_size: tuple[int, int],
    seed: int,
    n_spines: int = 3,
    depth: int = 4,
    roughness_frac: float = 0.042,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], list]:
    """
    Intracloud (cloud-to-cloud) discharge. Main structure is a horizontal spine
    with radial branching spreading in all directions — no downward bias, no
    ground contact. Mirrors atmo_strike_1/2 reference photos.

    Returns (segments, [])  — no ground points.
    """
    w, h      = canvas_size
    rng       = random.Random(seed)
    roughness = w * roughness_frac
    # Nexus: upper-middle portion of the frame (where storm cloud lives)
    ox = w * rng.uniform(0.32, 0.68)
    oy = h * rng.uniform(0.16, 0.40)
    origin    = (ox, oy)
    segments: list[dict] = []

    angle_step = 2 * math.pi / n_spines
    base_angle = rng.uniform(0, 2 * math.pi)

    for i in range(n_spines):
        spine_angle = base_angle + i * angle_step + rng.gauss(0, math.radians(14))
        # Spines spread horizontally; compress Y so they stay in the "sky"
        spine_len = w * rng.uniform(0.22, 0.54)
        cos_a, sin_a = math.cos(spine_angle), math.sin(spine_angle)
        end = (ox + cos_a * spine_len,
               oy + sin_a * spine_len * 0.58)

        def recurse(p0, p1, level, r, parent_angle, _rng=rng):
            chain = _subdivide_bolt(p0, p1, r, _rng, depth=5)
            segments.append({"path": chain, "level": level})
            if level <= 1:
                return
            # Intracloud: fewer forced forks at deep levels to avoid clutter
            n_forks = max(1, min(fork_concentration,
                                  _rng.randint(1, fork_concentration + 1)
                                  - max(0, depth - level - 1)))
            guard    = max(1, len(chain) // 5)
            interior = chain[guard:-guard]
            if not interior:
                return
            fork_pts = _rng.sample(interior, min(n_forks, len(interior)))
            for fp in fork_pts:
                # Wide fork angle — intracloud branches go in many directions
                fork_angle = parent_angle + _rng.choice([-1, 1]) * _rng.uniform(
                                 math.radians(38), math.radians(105))
                sub_len = math.dist(p0, p1) * _rng.uniform(
                              subbranch_length * 0.45, subbranch_length)
                branch_end = (fp[0] + math.cos(fork_angle) * sub_len,
                              fp[1] + math.sin(fork_angle) * sub_len * 0.60)
                recurse(fp, branch_end, level - 1, r * 0.60, fork_angle)

        recurse(origin, end, depth, roughness, spine_angle)

    return segments, []


def generate_full_storm(
    canvas_size: tuple[int, int],
    seed: int,
    n_ground_strikes: int = 2,
    depth: int = 4,
    roughness_frac: float = 0.037,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], list[tuple[float, float]]]:
    """
    Full thunderstorm: atmospheric intracloud discharge + cloud-to-ground strikes.
    Ground strikes originate from within the atmospheric cloud region.
    Mirrors atmo_strike_3 reference photo.

    Returns (all_segments, ground_contact_points).
    """
    w, h = canvas_size
    rng  = random.Random(seed)

    # Atmospheric (intracloud) component — n_spines = strikes + 1 for density
    n_spines = max(2, n_ground_strikes + 1)
    atm_segs, _ = generate_atmospheric_intracloud(
        canvas_size, seed=seed + 7, n_spines=n_spines, depth=depth,
        roughness_frac=roughness_frac * 1.05,
        fork_concentration=fork_concentration,
        subbranch_length=subbranch_length,
    )

    all_segs     = list(atm_segs)
    ground_pts   = []

    # Ground strikes — spread across the cloud region so they look like they
    # branch downward from the atmospheric discharge above
    for i in range(n_ground_strikes):
        ox = rng.uniform(0.22, 0.78)
        gs, gpt = generate_ground_strike(
            canvas_size, seed=seed + 100 + i * 41,
            origin_x_frac=ox, depth=max(2, depth - 1),
            roughness_frac=roughness_frac,
            fork_concentration=fork_concentration,
            subbranch_length=subbranch_length,
        )
        all_segs.extend(gs)
        ground_pts.append(gpt)

    return all_segs, ground_pts


def make_ground_contact_glow(
    canvas_size: tuple[int, int],
    ground_points: list[tuple[float, float]],
    alpha: float,
) -> Image.Image:
    """
    Bright elliptical flash at each ground contact point, simulating the
    intense luminosity of the return stroke touching ground.
    """
    w, h  = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0 or not ground_points:
        return layer

    r_base = max(10, int(w * 0.026))

    for pt in ground_points:
        x, y = int(pt[0]), int(pt[1])
        if not (-r_base * 4 < x < w + r_base * 4 and
                -r_base * 2 < y < h + r_base * 2):
            continue

        # Three concentric elliptical glow rings (wide → tight)
        for radius, color, opacity in [
            (r_base * 4, (120, 160, 255),  18),
            (r_base * 2, (200, 220, 255),  50),
            (r_base,     (240, 248, 255), 130),
        ]:
            ring = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            d    = ImageDraw.Draw(ring)
            # Ellipse flattened vertically — ground flash spreads horizontally
            ry = max(1, radius // 2)
            d.ellipse([x - radius, y - ry, x + radius, y + ry],
                      fill=color + (int(opacity * alpha),))
            ring = ring.filter(ImageFilter.GaussianBlur(radius=max(2, radius // 3)))
            layer = Image.alpha_composite(layer, ring)

        # Brilliant white core pixel cluster
        core = ImageDraw.Draw(layer)
        core.ellipse([x - 6, y - 3, x + 6, y + 3],
                     fill=(255, 255, 255, int(255 * alpha)))

    return layer


def make_atmospheric_lightning_layer(
    canvas_size: tuple[int, int],
    bolt_trees: list[dict],
    alpha: float,
    max_depth: int = 4,
) -> Image.Image:
    w, _ = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0:
        return layer

    base_w = max(1, int(w * 0.0015))
    md     = max(1, max_depth)

    for seg in bolt_trees:
        lv    = seg["level"]
        scale = lv / md
        pts   = seg["path"]
        segs  = list(zip(pts, pts[1:]))

        # Outer corona only on primary/secondary branches — keeps sub-branches crisp
        if scale > 0.5:
            g1 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            d1 = ImageDraw.Draw(g1)
            for p0, p1 in segs:
                d1.line([p0, p1],
                        fill=(80, 140, 255, int(40 * alpha * scale)),
                        width=max(1, int(base_w * 4 * scale)))
            g1 = g1.filter(ImageFilter.GaussianBlur(radius=max(3, int(w * 0.009))))
            layer = Image.alpha_composite(layer, g1)

        # Inner blue-white halo (all levels, tapers with scale)
        g2 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d2 = ImageDraw.Draw(g2)
        for p0, p1 in segs:
            d2.line([p0, p1],
                    fill=(200, 220, 255, int(100 * alpha * scale)),
                    width=max(1, int(base_w * 2 * scale)))
        g2 = g2.filter(ImageFilter.GaussianBlur(radius=max(1, int(w * 0.003))))
        layer = Image.alpha_composite(layer, g2)

        # Hair-thin white core
        core = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        dc   = ImageDraw.Draw(core)
        for p0, p1 in segs:
            dc.line([p0, p1],
                    fill=(232, 244, 255, int(220 * alpha * (0.3 + scale * 0.7))),
                    width=max(1, int(base_w * max(0.35, scale))))
        layer = Image.alpha_composite(layer, core)

    return layer


# ---------------------------------------------------------------------------
# Embers / sparks
# ---------------------------------------------------------------------------

def make_embers_frame(
    canvas_size: tuple[int, int],
    t: float,
    origin_x: float,
    origin_y: float,
    count: int = 80,
) -> Image.Image:
    w, h  = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    rng   = random.Random(42)
    births = [(rng.uniform(-1.0, 1.0), rng.random()) for _ in range(count)]

    for i, (vx_base, phase_off) in enumerate(births):
        phase = (t * 1.8 + phase_off) % 1.0
        vx    = vx_base * w * 0.18 * (0.3 + phase * 0.7)
        vy    = -phase * h * 0.55
        px    = origin_x + vx + math.sin(i * 2.1 + t * 3.0) * w * 0.012
        py    = origin_y + vy
        if not (0 <= px < w and 0 <= py < h):
            continue
        r_ch  = 255
        g_ch  = max(0, int(180 * (1.0 - phase ** 0.5)))
        a_ch  = max(0, int(220 * (1.0 - phase ** 0.7)))
        radius = max(1, int(3 * (1.0 - phase)))
        draw.ellipse([px - radius, py - radius, px + radius, py + radius],
                     fill=(r_ch, g_ch, 20, a_ch))

    return layer.filter(ImageFilter.GaussianBlur(radius=1))


# ---------------------------------------------------------------------------
# Rain / drizzle
# ---------------------------------------------------------------------------

def make_rain_frame(
    canvas_size: tuple[int, int],
    t: float,
    n_drops: int = 280,
    angle_deg: float = 12.0,
    speed: float = 0.9,
) -> Image.Image:
    w, h  = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    angle = math.radians(angle_deg)
    tan_a = math.tan(angle)
    rng   = random.Random(77)
    births = [
        (rng.uniform(0, w + h * tan_a), rng.random(),
         rng.randint(8, 26), rng.randint(30, 100))
        for _ in range(n_drops)
    ]
    for ox, phase_off, length, base_alpha in births:
        phase = (t * speed + phase_off) % 1.0
        x0    = ox - phase * h * tan_a
        y0    = phase * h
        x1    = x0 - length * math.sin(angle)
        y1    = y0 - length * math.cos(angle)
        # Soft fade at very top and bottom edges
        edge  = min(1.0, y0 / max(1, h * 0.08), (h - y0) / max(1, h * 0.08))
        a     = int(base_alpha * max(0.0, edge))
        if a > 0:
            draw.line([(x0, y0), (x1, y1)], fill=(200, 210, 230, a), width=1)
    return layer


# ---------------------------------------------------------------------------
# Vignette  (pre-computed once per canvas size)
# ---------------------------------------------------------------------------

def make_vignette(canvas_size: tuple[int, int], strength: float = 0.72) -> Image.Image:
    w, h = canvas_size
    xs   = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    ys   = np.linspace(-1.0, 1.0, h, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)
    dist   = np.sqrt(xx ** 2 + yy ** 2)
    dist   = np.clip(dist / 1.414, 0.0, 1.0)  # normalise so corners = 1.0
    alpha  = (dist ** 2.0 * strength * 255).clip(0, 255).astype(np.uint8)
    rgba   = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")


# ---------------------------------------------------------------------------
# Scan lines / CRT texture  (pre-computed once)
# ---------------------------------------------------------------------------

def make_scanlines(canvas_size: tuple[int, int], alpha: int = 20) -> Image.Image:
    w, h = canvas_size
    scan = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scan)
    for y in range(0, h, 2):
        draw.line([(0, y), (w - 1, y)], fill=(0, 0, 0, alpha))
    return scan


# ---------------------------------------------------------------------------
# Tone & color mapping — applied to the full composited frame
# ---------------------------------------------------------------------------

def apply_tone_mode(img: Image.Image, mode: str) -> Image.Image:
    """Transform color space of img. Preserves alpha if present."""
    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb   = img.convert("RGB")

    if mode == "bw":
        out = rgb.convert("L").convert("RGB")

    elif mode == "sepia":
        gray = rgb.convert("L")
        out  = Image.merge("RGB", (
            gray.point(lambda p: min(255, int(p * 1.08))),
            gray.point(lambda p: min(255, int(p * 0.87))),
            gray.point(lambda p: min(255, int(p * 0.69))),
        ))

    elif mode == "negative":
        out = ImageOps.invert(rgb)

    elif mode == "solarize":
        out = ImageOps.solarize(rgb, threshold=128)

    elif mode == "historical":
        # Faded sepia with lifted blacks + subtle edge burn
        gray = rgb.convert("L")
        out  = Image.merge("RGB", (
            gray.point(lambda p: min(255, int(p * 0.94 + 22))),
            gray.point(lambda p: min(255, int(p * 0.79 + 12))),
            gray.point(lambda p: min(255, int(p * 0.62 +  8))),
        ))
        w2, h2 = out.size
        xi = np.linspace(-1, 1, w2, dtype=np.float32)
        yi = np.linspace(-1, 1, h2, dtype=np.float32)
        X, Y  = np.meshgrid(xi, yi)
        burn  = np.clip((X ** 2 + Y ** 2) * 0.42, 0, 1)[:, :, np.newaxis]
        out   = Image.fromarray(
            (np.array(out, dtype=np.float32) * (1 - burn * 0.45)).clip(0, 255).astype(np.uint8),
            "RGB",
        )

    else:
        out = rgb  # "color" passthrough

    if alpha is not None:
        out = out.convert("RGBA")
        out.putalpha(alpha)
    return out


# ---------------------------------------------------------------------------
# Optical post-processing
# ---------------------------------------------------------------------------

def apply_chromatic_aberration(img: Image.Image, shift: int = 5) -> Image.Image:
    """Shift R channel right and B channel left — RGB fringing at edges."""
    if shift <= 0:
        return img
    alpha = img.split()[3] if img.mode == "RGBA" else None
    arr   = np.array(img.convert("RGB"), dtype=np.uint8)
    out   = np.zeros_like(arr)
    out[:, shift:,  0] = arr[:, :-shift, 0]   # R → right
    out[:, :,       1] = arr[:, :,       1]   # G unchanged
    out[:, :-shift, 2] = arr[:, shift:,  2]   # B → left
    result = Image.fromarray(out, "RGB")
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result


def apply_bloom(
    img: Image.Image,
    radius: int = 12,
    strength: float = 0.40,
) -> Image.Image:
    """Expand bright highlights — overexposed glow on light sources."""
    arr  = np.array(img.convert("RGB"), dtype=np.float32)
    lum  = arr.mean(axis=2)
    mask = np.clip((lum - 185) / 70.0, 0, 1)[:, :, np.newaxis]
    hi   = Image.fromarray((arr * mask).clip(0, 255).astype(np.uint8), "RGB")
    glow = hi.filter(ImageFilter.GaussianBlur(radius=radius))
    out  = np.clip(arr + np.array(glow, dtype=np.float32) * strength, 0, 255).astype(np.uint8)
    result = Image.fromarray(out, "RGB")
    if img.mode == "RGBA":
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


# ---------------------------------------------------------------------------
# Per-frame procedural effects
# ---------------------------------------------------------------------------

def apply_film_grain(img: Image.Image, intensity: float = 0.04, seed: int = 0) -> Image.Image:
    """Add per-frame luminance noise that changes with seed."""
    rng  = np.random.default_rng(seed)
    arr  = np.array(img.convert("RGB"), dtype=np.float32)
    arr += rng.normal(0, intensity * 255, arr.shape).astype(np.float32)
    result = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")
    if img.mode == "RGBA":
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


def make_snow_frame(
    canvas_size: tuple[int, int],
    t: float,
    n_flakes: int = 200,
) -> Image.Image:
    """Gently falling snow / hail particles."""
    w, h  = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    rng   = random.Random(42)
    flakes = [
        (rng.random(), rng.random(), rng.randint(1, 3), rng.uniform(0.4, 1.0))
        for _ in range(n_flakes)
    ]
    for x_frac, phase_off, size, brightness in flakes:
        phase = (t * 0.55 + phase_off) % 1.0
        drift = math.sin(phase * math.tau + x_frac * 10) * 0.018
        px = int(((x_frac + drift) % 1.0) * w)
        py = int(phase * h)
        draw.ellipse([px - size, py - size, px + size, py + size],
                     fill=(220, 235, 255, int(brightness * 190)))
    return layer


def make_holo_frame(
    canvas_size: tuple[int, int],
    t: float,
    subject_mask: Image.Image,
) -> Image.Image:
    """Animated rainbow shimmer confined to the subject mask.
    subject_mask is a grayscale (L) image in canvas coordinates.
    """
    w, h = canvas_size
    xi = np.linspace(0, 1, w, dtype=np.float32)
    yi = np.linspace(0, 1, h, dtype=np.float32)
    X, Y = np.meshgrid(xi, yi)

    # Scrolling hue field
    hue  = (X * 0.7 + Y * 0.2 + t * 0.45) % 1.0
    h6   = hue * 6
    sec  = np.floor(h6).astype(int) % 6
    f    = h6 - np.floor(h6)
    sat, val = 0.75, 0.90
    p, q, tv = val * (1 - sat), val * (1 - sat * f), val * (1 - sat * (1 - f))
    R = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [val,q,p,p,tv], default=val)
    G = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [tv,val,val,q,p], default=p)
    B = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [p,p,tv,val,val], default=q)

    # Shimmer wave that animates across the surface
    shimmer = np.sin(X * math.pi * 4 + t * math.tau * 1.5) * 0.5 + 0.5

    mask_img = (subject_mask.resize(canvas_size, Image.LANCZOS)
                if subject_mask.size != canvas_size else subject_mask)
    mask_arr = np.array(mask_img, dtype=np.float32) / 255.0

    alpha_arr = (shimmer * mask_arr * 90).clip(0, 255)
    out = np.stack(
        [R * 255, G * 255, B * 255, alpha_arr], axis=2
    ).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------
# Stylization (requires opencv-python — graceful fallback if absent)
# ---------------------------------------------------------------------------

def apply_stylize(img: Image.Image, mode: str) -> Image.Image:
    """Apply stylization to the subject image: cartoon / watercolor / oil / sketch.
    Returns the original image unchanged if opencv-python is not installed.
    """
    if mode == "none":
        return img
    try:
        import cv2
    except ImportError:
        print(f"  [Warning] opencv-python not installed — stylize_mode={mode!r} skipped.")
        return img

    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb   = np.array(img.convert("RGB"))
    bgr   = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    if mode == "cartoon":
        out_bgr = cv2.stylization(bgr, sigma_s=60, sigma_r=0.45)
    elif mode == "watercolor":
        out_bgr = cv2.stylization(bgr, sigma_s=60, sigma_r=0.07)
    elif mode == "oil":
        try:
            out_bgr = cv2.xphoto.oilPainting(bgr, size=4, dynRatio=1)
        except AttributeError:
            # xphoto module not compiled — fall back to heavy stylization
            out_bgr = cv2.stylization(bgr, sigma_s=40, sigma_r=0.30)
    elif mode == "sketch":
        _, sketch_gray = cv2.pencilSketch(bgr, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
        out_bgr = cv2.cvtColor(sketch_gray, cv2.COLOR_GRAY2BGR)
    else:
        return img

    result = Image.fromarray(cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB), "RGB")
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Per-frame composite
# ---------------------------------------------------------------------------

def build_frame(
    canvas_size: tuple[int, int],
    lantern: Image.Image,
    lantern_pos: tuple[int, int],
    lantern_size: tuple[int, int],
    smoke_x_min: float,
    smoke_x_max: float,
    smoke_y: float,
    frame_idx: int,
    total_frames: int,
    font: "ImageFont.FreeTypeFont | None",
    word_layout: list[tuple[int, int, str]],
    cfg: RenderConfig,
    flash_alpha: float = 0.0,
    lightning_bolts: "list | None" = None,
    bolt_trees: "list | None" = None,
    ground_points: "list | None" = None,
    lightning_alpha: float = 0.0,
    embers_origin: "tuple | None" = None,
    vignette_layer: "Image.Image | None" = None,
    scanlines_layer: "Image.Image | None" = None,
) -> Image.Image:
    t   = frame_idx / total_frames
    tag = cfg.tagline_cfg

    frame = Image.new("RGBA", canvas_size, cfg.bg_color + (255,))

    # --- L1: Atmosphere (rain / snow) — behind everything ---
    if cfg.add_rain:
        frame = Image.alpha_composite(frame, make_rain_frame(canvas_size, t))
    if cfg.add_snow:
        frame = Image.alpha_composite(frame, make_snow_frame(canvas_size, t))

    # --- L2: Lightning (behind smoke so glow illuminates mist) ---
    if cfg.add_lightning and lightning_alpha > 0:
        if cfg.lightning_mode in ("ground_strike", "atmospheric", "full_storm") and bolt_trees:
            frame = Image.alpha_composite(
                frame,
                make_atmospheric_lightning_layer(canvas_size, bolt_trees,
                                                 lightning_alpha, cfg.branch_depth),
            )
            if ground_points:
                frame = Image.alpha_composite(
                    frame,
                    make_ground_contact_glow(canvas_size, ground_points, lightning_alpha),
                )
        elif lightning_bolts:
            frame = Image.alpha_composite(
                frame, make_lightning_layer(canvas_size, lightning_bolts, lightning_alpha)
            )

    # --- L3: Smoke ---
    if cfg.add_smoke:
        frame = Image.alpha_composite(
            frame,
            make_smoke_frame(canvas_size, t * 0.5,
                             smoke_x_min, smoke_x_max, smoke_y, cfg.smoke_tint),
        )

    # --- L4: Embers (in front of smoke, behind subject) ---
    if cfg.add_embers and embers_origin:
        frame = Image.alpha_composite(
            frame, make_embers_frame(canvas_size, t, embers_origin[0], embers_origin[1])
        )

    # --- Bokeh: blur the background stack before subject paste ---
    if cfg.add_bokeh and cfg.bokeh_radius > 0:
        frame = frame.filter(ImageFilter.GaussianBlur(radius=cfg.bokeh_radius))

    # --- L5: Subject ---
    lx, ly = lantern_pos
    lw, lh = lantern_size
    scaled = lantern.resize((lw, lh), Image.LANCZOS)
    frame.paste(scaled, (lx, ly), scaled)

    # --- L6: Holographic shimmer (subject mask, animated) ---
    if cfg.add_holo:
        subj_mask = Image.new("L", canvas_size, 0)
        subj_mask.paste(scaled.split()[3], (lx, ly))
        frame = Image.alpha_composite(frame, make_holo_frame(canvas_size, t, subj_mask))

    # --- L7: Text ---
    if cfg.add_text and font and word_layout:
        n_words = len(word_layout)
        act_len = total_frames / n_words
        visible = min(n_words, int(frame_idx / act_len) + 1)
        if tag.orientation == "vertical_cw":
            text_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(text_layer)
            for wx, wy, word in word_layout[:visible]:
                _draw_word(tdraw, word, wx, wy, font,
                           tag.text_color, cfg.shadow_color, tag.shadow, tag.glow)
            text_layer = text_layer.rotate(-90, expand=False)
            frame = Image.alpha_composite(frame, text_layer)
        else:
            draw = ImageDraw.Draw(frame)
            for wx, wy, word in word_layout[:visible]:
                _draw_word(draw, word, wx, wy, font,
                           tag.text_color, cfg.shadow_color, tag.shadow, tag.glow)

    # --- L8: Flash ---
    if cfg.add_flash and flash_alpha > 0:
        frame = Image.alpha_composite(frame, make_flash_layer(canvas_size, flash_alpha))

    # --- Tone mapping (before optical effects so chroma/bloom see the toned image) ---
    if cfg.tone_mode != "color":
        frame = apply_tone_mode(frame, cfg.tone_mode)
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")

    # --- Chromatic aberration ---
    if cfg.add_chroma_aberration:
        frame = apply_chromatic_aberration(
            frame.convert("RGB"), cfg.chroma_shift
        ).convert("RGBA")

    # --- Bloom ---
    if cfg.add_bloom:
        frame = apply_bloom(
            frame.convert("RGB"), cfg.bloom_radius, cfg.bloom_strength
        ).convert("RGBA")

    # --- L9: Vignette ---
    if vignette_layer is not None:
        frame = Image.alpha_composite(frame, vignette_layer)

    # --- L10: Scan lines ---
    if scanlines_layer is not None:
        frame = Image.alpha_composite(frame, scanlines_layer)

    # --- Film grain — very last so noise sits on top of all layers ---
    rgb_out = frame.convert("RGB")
    if cfg.add_film_grain:
        rgb_out = apply_film_grain(rgb_out, cfg.film_grain_intensity, seed=frame_idx)
    return rgb_out


# ---------------------------------------------------------------------------
# Per-size orchestration
# ---------------------------------------------------------------------------

def generate_size(
    size_name: str,
    canvas_size: tuple[int, int],
    lantern: Image.Image,
    cfg: RenderConfig,
) -> None:
    w, h      = canvas_size
    tag       = cfg.tagline_cfg
    n_frames  = FRAMES_OVERRIDE.get(size_name, cfg.frames)
    print(f"  Building {size_name} ({w}×{h}, {n_frames} frames)...")

    # Fit subject within canvas
    max_lh = int(h * (0.88 if w > h else 0.80))
    max_lw = int(w * 0.94)
    scale  = min(max_lh / lantern.height, max_lw / lantern.width)
    lh = int(lantern.height * scale)
    lw = int(lantern.width  * scale)
    lx = (w - lw) // 2
    ly = max(0, (h - lh) // 2 - int(h * 0.03))

    smoke_x_min = 0.0
    smoke_x_max = float(w)
    smoke_y     = float(h)

    # Font + word layout
    font        = None
    word_layout: list[tuple[int, int, str]] = []
    if cfg.add_text and tag.text:
        font_size   = max(28, int(h * tag.font_size_pct))
        font        = get_font(font_size)
        word_layout = build_word_layout(tag, font, w, h, ly, lh, font_size)

    # Strike timing — two strikes per loop; built first so n_strikes is known
    # before geometry generation.
    strike_starts    = [int(n_frames * 0.17), int(n_frames * 0.58)]
    n_strikes        = len(strike_starts)
    flash_alphas     = [0.0] * n_frames
    lightning_alphas = [0.0] * n_frames
    frame_strike_idx = [-1]  * n_frames   # which strike is active per frame
    bolt_envelope    = [0.4, 1.0, 0.55, 0.2]
    for s_idx, sf in enumerate(strike_starts):
        if cfg.add_flash:
            for j, fa in enumerate(_FLASH_ENVELOPE):
                flash_alphas[(sf + j) % n_frames] = max(flash_alphas[(sf + j) % n_frames], fa)
        if cfg.add_lightning:
            for j, la in enumerate(bolt_envelope):
                fi = (sf + j) % n_frames
                lightning_alphas[fi] = max(lightning_alphas[fi], la)
                frame_strike_idx[fi] = s_idx

    # Pre-generate unique bolt geometry per strike so each flash shows a
    # different pattern — seeds are offset by a large coprime so results diverge.
    _s_bolts: list = [None] * n_strikes   # simple-mode path lists
    _s_trees: list = [None] * n_strikes   # atmospheric segment dicts
    _s_gpts:  list = [[]   for _ in range(n_strikes)]

    if cfg.add_lightning:
        for s in range(n_strikes):
            sseed = w * h + s * 1337
            if cfg.lightning_mode == "ground_strike":
                n = cfg.n_bolts
                origins = ([0.50] if n == 1 else
                           [0.25 + i * (0.52 / max(1, n - 1)) for i in range(n)])
                trees, gpts_s = [], []
                for i, ox in enumerate(origins):
                    segs, gpt = generate_ground_strike(
                        canvas_size, seed=sseed + i * 37,
                        origin_x_frac=ox, depth=cfg.branch_depth,
                        fork_concentration=cfg.fork_concentration,
                        subbranch_length=cfg.subbranch_length,
                    )
                    trees.extend(segs)
                    gpts_s.append(gpt)
                _s_trees[s] = trees
                _s_gpts[s]  = gpts_s

            elif cfg.lightning_mode == "atmospheric":
                trees, _ = generate_atmospheric_intracloud(
                    canvas_size, seed=sseed,
                    n_spines=cfg.n_bolts, depth=cfg.branch_depth,
                    fork_concentration=cfg.fork_concentration,
                    subbranch_length=cfg.subbranch_length,
                )
                _s_trees[s] = trees

            elif cfg.lightning_mode == "full_storm":
                trees, gpts_s = generate_full_storm(
                    canvas_size, seed=sseed,
                    n_ground_strikes=cfg.n_bolts, depth=cfg.branch_depth,
                    fork_concentration=cfg.fork_concentration,
                    subbranch_length=cfg.subbranch_length,
                )
                _s_trees[s] = trees
                _s_gpts[s]  = gpts_s

            else:  # "simple"
                _s_bolts[s] = generate_lightning_bolt(canvas_size, seed=sseed)

    # Pre-compute static layers
    vignette_layer  = make_vignette(canvas_size)  if cfg.add_vignette  else None
    scanlines_layer = make_scanlines(canvas_size) if cfg.add_scanlines else None

    # Embers origin — upper quarter of subject (heat rises from lantern top)
    embers_origin = (lx + lw // 2, ly + lh // 4) if cfg.add_embers else None

    frames: list[Image.Image] = []
    for i in range(n_frames):
        s_idx     = frame_strike_idx[i]
        cur_bolts = _s_bolts[s_idx] if s_idx >= 0 else None
        cur_trees = _s_trees[s_idx] if s_idx >= 0 else None
        cur_gpts  = _s_gpts[s_idx]  if s_idx >= 0 else []
        f = build_frame(
            canvas_size     = canvas_size,
            lantern         = lantern,
            lantern_pos     = (lx, ly),
            lantern_size    = (lw, lh),
            smoke_x_min     = smoke_x_min,
            smoke_x_max     = smoke_x_max,
            smoke_y         = smoke_y,
            frame_idx       = i,
            total_frames    = n_frames,
            font            = font,
            word_layout     = word_layout,
            cfg             = cfg,
            flash_alpha     = flash_alphas[i],
            lightning_bolts = cur_bolts,
            bolt_trees      = cur_trees,
            ground_points   = cur_gpts,
            lightning_alpha = lightning_alphas[i],
            embers_origin   = embers_origin,
            vignette_layer  = vignette_layer,
            scanlines_layer = scanlines_layer,
        )
        frames.append(f.convert("P", palette=Image.ADAPTIVE, colors=256))

    out = cfg.output_dir / f"brand_{size_name}.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=cfg.frame_ms,
        loop=0,
    )
    kb = out.stat().st_size // 1024
    print(f"    → {out}  ({kb} KB)")

    if cfg.output_static:
        if cfg.add_lightning and any(la > 0 for la in lightning_alphas):
            peak_la = max(lightning_alphas)
            peak_fi = lightning_alphas.index(peak_la)
            peak_si = frame_strike_idx[peak_fi]
        else:
            peak_fi = n_frames // 4
            peak_la = 0.0
            peak_si = -1
        static_frame = build_frame(
            canvas_size     = canvas_size,
            lantern         = lantern,
            lantern_pos     = (lx, ly),
            lantern_size    = (lw, lh),
            smoke_x_min     = smoke_x_min,
            smoke_x_max     = smoke_x_max,
            smoke_y         = smoke_y,
            frame_idx       = peak_fi,
            total_frames    = n_frames,
            font            = font,
            word_layout     = word_layout,
            cfg             = cfg,
            flash_alpha     = flash_alphas[peak_fi],
            lightning_bolts = _s_bolts[peak_si] if peak_si >= 0 else None,
            bolt_trees      = _s_trees[peak_si] if peak_si >= 0 else None,
            ground_points   = _s_gpts[peak_si]  if peak_si >= 0 else [],
            lightning_alpha = peak_la,
            embers_origin   = embers_origin,
            vignette_layer  = vignette_layer,
            scanlines_layer = scanlines_layer,
        )
        static_out = cfg.output_dir / f"brand_{size_name}_peak.png"
        static_frame.save(static_out)
        static_kb = static_out.stat().st_size // 1024
        print(f"    → {static_out}  ({static_kb} KB, static PNG)")


# ---------------------------------------------------------------------------
# Pipeline + entry point
# ---------------------------------------------------------------------------

def run_pipeline(cfg: RenderConfig, progress_cb=None) -> None:
    def _prog(n):
        if progress_cb:
            progress_cb(n)

    print("\nBrand Image Generator")
    print("=" * 40)
    _prog(5)

    lantern_raw = isolate_lantern(cfg)
    lantern     = apply_image_processing(lantern_raw, cfg)
    print(f"Subject isolated: {lantern.width}×{lantern.height}px\n")
    _prog(20)

    n_sizes = len(cfg.sizes)
    for i, (size_name, size) in enumerate(cfg.sizes.items()):
        generate_size(size_name, size, lantern, cfg)
        print()
        _prog(20 + int(80 * (i + 1) / n_sizes))

    print("All done. Files written to:", cfg.output_dir)


def main() -> None:
    global _window
    api  = Api()
    here = Path(__file__).parent
    html = (here / "wizard.html").read_text(encoding="utf-8")
    _window = webview.create_window(
        "Brand Image Generator",
        html=html,
        js_api=api,
        width=620,
        height=800,
        resizable=False,
        background_color="#1c1e23",
    )
    webview.start()


if __name__ == "__main__":
    main()
