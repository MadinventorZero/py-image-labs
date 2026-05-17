"""Chibi portrait: enlarge head, compress body — pure PIL/numpy, no model needed.

The effect splits the subject image at `head_pct` from the top, scales the head
region up by `head_scale`, then resizes the body to fill the remaining space and
recomposites the two halves back to the original canvas dimensions.

A narrow cross-fade blend zone (≈5 % of height) smooths the join so there is no
hard seam between head and body.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def apply_chibi(
    img: Image.Image,
    head_pct:   float = 0.42,
    head_scale: float = 1.45,
) -> Image.Image:
    """Chibi-style head enlargement.

    Args:
        img:        RGBA (or RGB) subject image.
        head_pct:   Fraction of image height considered "head" (0.3–0.6).
        head_scale: How much to enlarge the head relative to its original height.
    """
    orig_mode = img.mode
    orig_size = img.size
    w, h      = orig_size

    head_pct   = float(np.clip(head_pct,   0.20, 0.65))
    head_scale = float(np.clip(head_scale, 1.10, 2.20))

    split_y  = int(h * head_pct)
    body_src = h - split_y

    new_head_h = int(split_y * head_scale)
    new_body_h = max(4, h - new_head_h)
    total_h    = new_head_h + new_body_h

    # ── Resize both regions ───────────────────────────────────────────────────
    head_region = img.crop((0, 0,       w, split_y))
    body_region = img.crop((0, split_y, w, h      ))

    head_up   = head_region.resize((w, new_head_h), Image.LANCZOS)
    body_down = body_region.resize((w, new_body_h), Image.LANCZOS) if body_src > 0 \
                else Image.new(img.mode, (w, new_body_h), (0, 0, 0, 0))

    # ── Compose ───────────────────────────────────────────────────────────────
    mode   = "RGBA" if "A" in img.mode else "RGB"
    canvas = Image.new(mode, (w, total_h), (0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
    canvas.paste(head_up,   (0, 0))
    canvas.paste(body_down, (0, new_head_h))

    # ── Cross-fade blend zone at the seam ────────────────────────────────────
    blend_h = max(4, int(h * 0.05))
    seam_top    = max(0, new_head_h - blend_h)
    seam_bottom = min(total_h, new_head_h + blend_h)

    # Blur a stripe around the seam to hide the join
    stripe = canvas.crop((0, seam_top, w, seam_bottom))
    stripe = stripe.filter(ImageFilter.GaussianBlur(radius=max(1, blend_h // 3)))
    canvas.paste(stripe, (0, seam_top))

    # ── Resize back to original canvas dimensions ─────────────────────────────
    result = canvas.resize(orig_size, Image.LANCZOS)
    if orig_mode != mode:
        result = result.convert(orig_mode)
    return result
