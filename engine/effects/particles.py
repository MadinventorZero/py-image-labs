import math
import random

from PIL import Image, ImageDraw, ImageFilter


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
        edge  = min(1.0, y0 / max(1, h * 0.08), (h - y0) / max(1, h * 0.08))
        a     = int(base_alpha * max(0.0, edge))
        if a > 0:
            draw.line([(x0, y0), (x1, y1)], fill=(200, 210, 230, a), width=1)
    return layer


def make_snow_frame(
    canvas_size: tuple[int, int],
    t: float,
    n_flakes: int = 200,
) -> Image.Image:
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
