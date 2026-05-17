"""Real-ESRGAN 4× upscaling via ONNX with tiled inference.

Falls back to PIL LANCZOS when the model file is not present.
Tile-based processing keeps VRAM under ~2 GB even on large canvases.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image

from engine.models_manager import (
    get_ort_session, model_available, ModelNotAvailableError,
)

_TILE  = 256   # input tile size (px)
_OVLAP = 16    # overlap to avoid tile-edge seams
_SCALE = 4


def upscale_image(
    img: Image.Image,
    mode: str = "x4",       # "x4" | "x4_anime"
) -> Image.Image:
    """4× upscale using Real-ESRGAN ONNX.

    Falls back to PIL LANCZOS when the model is not downloaded.
    """
    model_id = "realesrgan_x4_anime" if mode == "x4_anime" else "realesrgan_x4"

    try:
        session = get_ort_session(model_id)
    except ModelNotAvailableError:
        print(f"  [upscale] model '{model_id}' not downloaded — using PIL LANCZOS fallback")
        return img.resize((img.width * _SCALE, img.height * _SCALE), Image.LANCZOS)

    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb   = np.array(img.convert("RGB"), dtype=np.float32) / 255.0  # [H, W, 3] in [0,1]

    try:
        out_rgb = _tile_inference(session, rgb)
    except Exception as e:
        print(f"  [upscale] inference failed ({e}); using PIL fallback")
        return img.resize((img.width * _SCALE, img.height * _SCALE), Image.LANCZOS)

    result = Image.fromarray((out_rgb * 255).clip(0, 255).astype(np.uint8), "RGB")
    if alpha is not None:
        up_alpha = alpha.resize(result.size, Image.LANCZOS)
        result = result.convert("RGBA")
        result.putalpha(up_alpha)
    return result


def _tile_inference(session, rgb: np.ndarray) -> np.ndarray:
    """Process image in overlapping tiles to limit peak VRAM."""
    H, W = rgb.shape[:2]
    out_H, out_W = H * _SCALE, W * _SCALE
    output = np.zeros((out_H, out_W, 3), dtype=np.float32)
    weight = np.zeros((out_H, out_W, 1), dtype=np.float32)

    input_name  = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    step = _TILE - _OVLAP * 2
    for y in range(0, H, step):
        for x in range(0, W, step):
            # Source tile with overlap padding
            x0 = max(0, x - _OVLAP);  x1 = min(W, x + step + _OVLAP)
            y0 = max(0, y - _OVLAP);  y1 = min(H, y + step + _OVLAP)
            tile = rgb[y0:y1, x0:x1]

            # NCHW float32
            inp = tile.transpose(2, 0, 1)[np.newaxis]
            out_tile = session.run([output_name], {input_name: inp})[0]
            # → [1, 3, tH*4, tW*4]
            out_tile = out_tile[0].transpose(1, 2, 0)  # HWC

            # Destination coordinates
            ox0, ox1 = x0 * _SCALE, x1 * _SCALE
            oy0, oy1 = y0 * _SCALE, y1 * _SCALE
            oh, ow = out_tile.shape[:2]

            output[oy0:oy0+oh, ox0:ox0+ow] += out_tile
            weight[oy0:oy0+oh, ox0:ox0+ow] += 1.0

    weight = np.maximum(weight, 1.0)
    return (output / weight).clip(0.0, 1.0)


def upscale_available(mode: str = "x4") -> bool:
    model_id = "realesrgan_x4_anime" if mode == "x4_anime" else "realesrgan_x4"
    return model_available(model_id)
