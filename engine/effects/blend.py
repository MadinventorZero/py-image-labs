"""Photoshop-compatible blend modes (numpy float32, 0–1 range)."""
from __future__ import annotations
import numpy as np
from PIL import Image


# ── Blend functions (operate on float32 H×W×3 arrays in [0,1]) ─────────────

def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a * b

def screen(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 1.0 - (1.0 - a) * (1.0 - b)

def overlay(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.where(a < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))

def hard_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return overlay(b, a)

def soft_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (1.0 - 2.0 * b) * a ** 2 + 2.0 * b * a

def difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.abs(a - b)

def exclusion(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a + b - 2.0 * a * b

def color_dodge(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.minimum(1.0, b / np.maximum(1.0 - a, 1e-7))

def color_burn(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 1.0 - np.minimum(1.0, (1.0 - b) / np.maximum(a, 1e-7))

def add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.minimum(1.0, a + b)


BLEND_MODES: dict[str, callable] = {
    "normal":      lambda a, b: b,
    "multiply":    multiply,
    "screen":      screen,
    "overlay":     overlay,
    "hard_light":  hard_light,
    "soft_light":  soft_light,
    "difference":  difference,
    "exclusion":   exclusion,
    "color_dodge": color_dodge,
    "color_burn":  color_burn,
    "add":         add,
}


def blend(
    base: Image.Image,
    top:  Image.Image,
    mode: str   = "screen",
    opacity: float = 1.0,
) -> Image.Image:
    """Composite top over base using the named Photoshop blend mode.

    Both images are converted to RGBA; alpha of top controls compositing.
    Returns RGBA.
    """
    fn = BLEND_MODES.get(mode, BLEND_MODES["normal"])

    a = np.array(base.convert("RGBA"), dtype=np.float32) / 255.0
    b = np.array(top.convert("RGBA"),  dtype=np.float32) / 255.0

    a_rgb  = a[:, :, :3]
    b_rgb  = b[:, :, :3]
    b_mask = b[:, :, 3:4] * opacity

    blended  = fn(a_rgb, b_rgb).clip(0.0, 1.0)
    out_rgb  = a_rgb * (1.0 - b_mask) + blended * b_mask
    out_a    = np.maximum(a[:, :, 3:4], b_mask)

    result = np.concatenate([out_rgb, out_a], axis=2)
    return Image.fromarray((result * 255.0).clip(0, 255).astype(np.uint8), "RGBA")
