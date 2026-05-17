from dataclasses import dataclass, field
from pathlib import Path

ALL_SIZES = {
    "youtube_thumbnail": (1280, 720),
    "channel_art":       (2560, 1440),
    "podcast_square":    (3000, 3000),
}

FRAMES_OVERRIDE = {"podcast_square": 24}


@dataclass
class TaglineConfig:
    text:          str   = "Thunder Road Rails"
    anchor:        str   = "center"
    offset_y:      float = 0.0
    font_size_pct: float = 0.075
    align:         str   = "center"
    orientation:   str   = "horizontal"
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
    remove_bg:    bool  = True
    crop:         bool  = True
    crop_padding: float = 0.12
    rotate:       int   = 0
    resize_pct:   int   = 100
    add_smoke:          bool  = True
    add_lightning:      bool  = True
    lightning_mode:     str   = "simple"
    n_bolts:            int   = 2
    branch_depth:       int   = 4
    fork_concentration: int   = 3
    subbranch_length:   float = 0.40
    add_flash:          bool  = True
    add_text:      bool  = True
    add_embers:    bool  = False
    add_rain:      bool  = False
    add_vignette:  bool  = True
    add_scanlines: bool  = False
    output_static: bool  = False
    tone_mode:    str   = "color"
    stylize_mode: str   = "none"
    add_chroma_aberration: bool  = False
    chroma_shift:          int   = 5
    add_bloom:             bool  = False
    bloom_radius:          int   = 12
    bloom_strength:        float = 0.40
    add_film_grain:       bool  = False
    film_grain_intensity: float = 0.04
    add_snow:             bool  = False
    add_holo:             bool  = False
    add_bokeh:            bool  = False
    bokeh_radius:         int   = 18
    # ── Aura ─────────────────────────────────────────────────────
    add_aura:             bool  = False
    aura_preset:          str   = "dbz_standard"
    aura_core_color:      tuple = (255, 255, 200)
    aura_corona_color:    tuple = (255, 220,  60)
    aura_core_radius:     int   = 20
    aura_corona_radius:   int   = 65
    aura_pulse_speed:     float = 3.0
    aura_pulse_depth:     float = 0.12
    aura_electric_fringe: bool  = True
    # ── Sharpen / Denoise ────────────────────────────────────────
    add_sharpen:          bool  = False
    sharpen_mode:         str   = "usm"
    sharpen_amount:       float = 1.0
    sharpen_radius:       float = 2.0
    sharpen_threshold:    int   = 3
    add_denoise:          bool  = False
    denoise_strength:     int   = 10
    denoise_mode:         str   = "nlm"
    # ── Extended effect params ───────────────────────────────────
    vignette_strength:    float = 0.72
    scanlines_alpha:      int   = 20
    # ── Neural FX (subject-level, applied once in image_proc) ───
    anime_style:          str   = "none"   # none|hayao|paprika|face_paint|wbc
    add_chibi:            bool  = False
    chibi_head_pct:       float = 0.42
    chibi_head_scale:     float = 1.45
    upscale_mode:         str   = "none"   # none|x4|x4_anime
    # ── Fog ──────────────────────────────────────────────────────
    add_fog:              bool  = False
    fog_density:          float = 0.4
    fog_height_pct:       float = 0.5
    fog_tint:             tuple = (180, 185, 200)
    # ── God rays ─────────────────────────────────────────────────
    add_god_rays:         bool  = False
    god_rays_intensity:   float = 0.5
    god_rays_origin_x:    float = 0.5
    god_rays_origin_y:    float = 0.15
    god_rays_color:       tuple = (255, 240, 180)
    # ── Glitch ───────────────────────────────────────────────────
    add_glitch:           bool  = False
    glitch_intensity:     float = 0.5
    glitch_band_count:    int   = 6
    glitch_channel_split: bool  = True
    # ── Particle params ──────────────────────────────────────────
    rain_n_drops:         int   = 280
    rain_angle:           float = 12.0
    embers_count:         int   = 80
    smoke_density:        float = 0.7
    # ── Stylize params ───────────────────────────────────────────
    stylize_sigma_s:      float = 60.0
    stylize_sigma_r:      float = 0.45
    stylize_shade_factor: float = 0.05
    # ── Per-layer opacity (effect_id → 0.0–1.0) ─────────────────
    effect_opacity:       dict  = field(default_factory=dict)
    # ── Output formats ───────────────────────────────────────────
    output_gif:           bool  = True
    output_webp:          bool  = False
    output_mp4:           bool  = False
    output_apng:          bool  = False
    sizes: dict = field(default_factory=lambda: dict(ALL_SIZES))
