import math
import random

from PIL import Image, ImageDraw, ImageFilter


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
