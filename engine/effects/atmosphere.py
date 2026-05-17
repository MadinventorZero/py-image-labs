"""Atmospheric overlay effects: fog/haze and god rays."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageFilter


def make_fog_frame(
    canvas_size: tuple[int, int],
    t: float,
    density: float = 0.4,
    tint: tuple[int, int, int] = (180, 185, 200),
    height_pct: float = 0.5,
) -> Image.Image:
    """Bottom-rising fog layer with animated horizontal undulation."""
    w, h = canvas_size
    r, g, b = tint

    fog_top = int(h * max(0.0, 1.0 - height_pct))
    rows = h - fog_top
    if rows <= 0:
        return Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    out = np.zeros((h, w, 4), dtype=np.float32)

    Y = np.arange(rows, dtype=np.float32)
    t_y = (Y / max(1, rows - 1)) ** 0.6

    # Animated horizontal undulation
    phase = t * math.tau + (fog_top + Y) * 0.04
    wave = 1.0 + 0.15 * np.sin(phase)

    alpha_row = (t_y * density * wave * 200).clip(0, 215)

    out[fog_top:, :, 0] = r
    out[fog_top:, :, 1] = g
    out[fog_top:, :, 2] = b
    out[fog_top:, :, 3] = alpha_row[:, np.newaxis]

    result = Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")
    blur_r = max(2, int(w * 0.012))
    return result.filter(ImageFilter.GaussianBlur(radius=blur_r))


def make_god_rays_frame(
    canvas_size: tuple[int, int],
    t: float,
    intensity: float = 0.5,
    origin_x: float = 0.5,
    origin_y: float = 0.15,
    color: tuple[int, int, int] = (255, 240, 180),
) -> Image.Image:
    """Animated radial light rays from a sky origin point."""
    w, h = canvas_size
    r, g, b = color

    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    ox = origin_x * w
    oy = origin_y * h

    dx = X - ox
    dy = Y - oy
    angle = np.arctan2(dy, dx)
    dist  = np.hypot(dx, dy)

    # Multi-frequency angular oscillation → distinct rays
    phase = t * math.tau
    ray_mask = (
        0.50 + 0.30 * np.sin(angle * 7  + phase) +
               0.14 * np.sin(angle * 13 - phase * 1.3) +
               0.06 * np.sin(angle * 19 + phase * 0.7)
    ).clip(0.0, 1.0)

    # Radial falloff: full brightness at source, zero past ~60 % of diagonal
    max_d = math.hypot(w, h)
    radial = np.clip(1.0 - dist / (max_d * 0.62), 0.0, 1.0) ** 0.45

    alpha = (ray_mask * radial * intensity * 210).clip(0, 255)

    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = r
    out[:, :, 1] = g
    out[:, :, 2] = b
    out[:, :, 3] = alpha.astype(np.uint8)

    result = Image.fromarray(out, "RGBA")
    blur_r = max(4, int(w * 0.018))
    return result.filter(ImageFilter.GaussianBlur(radius=blur_r))
