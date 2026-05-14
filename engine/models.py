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
    sizes: dict = field(default_factory=lambda: dict(ALL_SIZES))
