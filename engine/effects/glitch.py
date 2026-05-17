"""Glitch effect: horizontal band displacement + RGB channel split."""
from __future__ import annotations
import numpy as np
from PIL import Image


def apply_glitch(
    img: Image.Image,
    t: float = 0.0,
    intensity: float = 0.5,
    band_count: int = 6,
    channel_split: bool = True,
) -> Image.Image:
    alpha = img.split()[3] if img.mode == "RGBA" else None
    arr = np.array(img.convert("RGB")).copy()
    h, w = arr.shape[:2]
    rng = np.random.default_rng(int(t * 10000) % 9999 + 1)

    n = max(1, band_count)
    max_shift = max(1, int(w * 0.10 * intensity))
    for _ in range(n):
        y0 = int(rng.integers(0, h))
        bh = int(rng.integers(1, max(2, int(h * 0.06 * intensity) + 1)))
        y1 = min(h, y0 + bh)
        shift = int(rng.integers(-max_shift, max_shift + 1))
        if shift:
            arr[y0:y1] = np.roll(arr[y0:y1], shift, axis=1)

    if channel_split and intensity > 0.1:
        cs = max(1, int(intensity * 8))
        arr[:, :, 0] = np.roll(arr[:, :, 0],  cs, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -cs, axis=1)

    result = Image.fromarray(arr, "RGB")
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result
