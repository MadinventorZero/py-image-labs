"""Aura effects: DBZ energy, magic element glow, divine light."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    from scipy.ndimage import binary_dilation, distance_transform_edt as _edt
    _SCIPY = True
except ImportError:
    _SCIPY = False


PRESETS: dict[str, dict] = {
    "dbz_standard": {"core": (255, 255, 200), "corona": (255, 220,  60), "core_r": 20, "corona_r": 65, "electric": True },
    "dbz_blue":     {"core": (200, 220, 255), "corona": ( 60, 140, 255), "core_r": 20, "corona_r": 70, "electric": True },
    "dbz_ultra":    {"core": (240, 240, 255), "corona": (200, 200, 200), "core_r": 15, "corona_r": 55, "electric": True },
    "magic_fire":   {"core": (255, 180,  60), "corona": (200,  60,   0), "core_r": 15, "corona_r": 50, "electric": False},
    "magic_ice":    {"core": (200, 240, 255), "corona": ( 80, 180, 255), "core_r": 15, "corona_r": 50, "electric": False},
    "magic_arcane": {"core": (220, 180, 255), "corona": (120,  40, 200), "core_r": 15, "corona_r": 50, "electric": False},
    "divine":       {"core": (255, 255, 240), "corona": (255, 230, 100), "core_r": 20, "corona_r": 60, "electric": False},
}


def _disk(radius: int) -> np.ndarray:
    r = radius
    Y, X = np.ogrid[-r:r + 1, -r:r + 1]
    return (X ** 2 + Y ** 2 <= r ** 2)


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    if _CV2:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        return cv2.dilate(mask, k)
    if _SCIPY:
        return binary_dilation(mask > 0, structure=_disk(radius)).astype(np.uint8) * 255
    return mask   # no-op last resort


def _dist_field(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance from each pixel to the nearest subject pixel."""
    if _CV2:
        return cv2.distanceTransform((255 - mask).astype(np.uint8), cv2.DIST_L2, 5)
    if _SCIPY:
        return _edt(mask == 0).astype(np.float32)
    return np.zeros_like(mask, dtype=np.float32)


def make_aura_frame(
    subject_alpha: np.ndarray,
    canvas_size: tuple[int, int],
    t: float,
    preset: str = "dbz_standard",
    *,
    core_color:     tuple[int, int, int] | None = None,
    corona_color:   tuple[int, int, int] | None = None,
    core_radius:    int   | None = None,
    corona_radius:  int   | None = None,
    pulse_speed:    float = 3.0,
    pulse_depth:    float = 0.12,
    electric_fringe: bool | None = None,
) -> Image.Image:
    """One RGBA aura frame, sized to match canvas_size.

    Args:
        subject_alpha: H×W uint8 mask (255 = subject, 0 = background).
                       Should already be sized to canvas_size.
        canvas_size:   (W, H) output size.
        t:             Animation phase 0.0–1.0.
    """
    cfg  = PRESETS.get(preset, PRESETS["dbz_standard"])
    cr   = core_color    or cfg["core"]
    cc   = corona_color  or cfg["corona"]
    rv   = core_radius   if core_radius   is not None else cfg["core_r"]
    rk   = corona_radius if corona_radius is not None else cfg["corona_r"]
    elec = electric_fringe if electric_fringe is not None else cfg["electric"]

    # Animated pulse on radii
    pulse  = 1.0 + pulse_depth * math.sin(t * math.tau * pulse_speed)
    cr_px  = max(1, int(rv * pulse))
    ck_px  = max(1, int(rk * pulse))

    corona_mask = _dilate(subject_alpha, ck_px)
    ring_float  = (corona_mask.astype(np.float32) - subject_alpha.astype(np.float32)).clip(0, 255)

    dist    = _dist_field(subject_alpha)
    falloff = np.clip(1.0 - dist / max(1.0, float(ck_px)), 0.0, 1.0) ** 1.5

    flicker   = 0.85 + 0.15 * math.sin(t * math.tau * 7.3)
    alpha_arr = (ring_float / 255.0 * falloff * 200 * flicker).clip(0, 255)

    # Colour gradient: core_color near subject edge → corona_color at outer edge
    inner_frac = np.clip(1.0 - dist / max(1.0, float(cr_px * 2)), 0.0, 1.0)
    R = (cr[0] * inner_frac + cc[0] * (1.0 - inner_frac)).clip(0, 255)
    G = (cr[1] * inner_frac + cc[1] * (1.0 - inner_frac)).clip(0, 255)
    B = (cr[2] * inner_frac + cc[2] * (1.0 - inner_frac)).clip(0, 255)

    out = np.zeros((*subject_alpha.shape, 4), dtype=np.uint8)
    out[:, :, 0] = R.astype(np.uint8)
    out[:, :, 1] = G.astype(np.uint8)
    out[:, :, 2] = B.astype(np.uint8)
    out[:, :, 3] = alpha_arr.astype(np.uint8)

    result = Image.fromarray(out, "RGBA")

    if elec:
        result = _add_electric_fringe(result, subject_alpha, corona_mask, t, cc)

    return result


def _add_electric_fringe(
    aura:         Image.Image,
    subject_mask: np.ndarray,
    corona_mask:  np.ndarray,
    t:            float,
    color:        tuple[int, int, int],
) -> Image.Image:
    """Overlay short electric crackle lines on the corona edge."""
    elec = Image.new("RGBA", aura.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(elec)
    rng  = np.random.default_rng(int(t * 1000) % 10000)

    # Edge = corona ring minus a slightly eroded version
    shrunk = _dilate(subject_mask, 8)
    edge   = corona_mask.astype(np.int16) - shrunk.astype(np.int16)
    ys, xs = np.where(edge > 64)
    if len(xs) < 8:
        return aura

    n = min(14, len(xs))
    idx = rng.choice(len(xs), size=n, replace=False)
    for i in idx:
        x0, y0  = int(xs[i]), int(ys[i])
        angle   = rng.uniform(0, math.tau)
        length  = int(rng.integers(5, 18))
        x1 = x0 + int(math.cos(angle) * length)
        y1 = y0 + int(math.sin(angle) * length)
        a_val = int(rng.uniform(90, 200))
        draw.line([(x0, y0), (x1, y1)], fill=(*color, a_val), width=1)

    return Image.alpha_composite(aura, elec)
