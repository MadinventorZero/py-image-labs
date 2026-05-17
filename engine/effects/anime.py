"""Anime / cartoon style transfer via ONNX inference.

Supports:
  - AnimeGAN v2  (Hayao, Paprika, Face Paint)  — NHWC, tanh-normalised
  - White-Box Cartoonizer (WBC)                — NHWC, tanh-normalised

Falls back to cv2.stylization when the ONNX model is not available.
All functions accept and return PIL Images (RGBA or RGB).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from engine.models_manager import (
    get_ort_session, model_available, ModelNotAvailableError,
)

# Map public style names → registry IDs
_STYLE_MAP = {
    "hayao":      "animegan2_hayao",
    "paprika":    "animegan2_paprika",
    "face_paint": "animegan2_face_paint",
    "wbc":        "white_box_cartoon",
}

# Max long-edge before inference (reduces VRAM; down-sampled back afterwards)
_MAX_EDGE = 1024


def _to_tanh(img_rgb: np.ndarray) -> np.ndarray:
    """uint8 HWC → float32 NHWC [-1, 1]"""
    return (img_rgb.astype(np.float32) / 127.5 - 1.0)[np.newaxis]


def _from_tanh(arr: np.ndarray) -> np.ndarray:
    """float32 NHWC [-1, 1] → uint8 HWC"""
    return np.clip((arr[0] + 1.0) * 127.5, 0, 255).astype(np.uint8)


def _limit_size(img: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    """Downscale long edge to _MAX_EDGE; return scaled image and original size."""
    orig = img.size  # (W, H)
    long_edge = max(orig)
    if long_edge <= _MAX_EDGE:
        return img, orig
    scale = _MAX_EDGE / long_edge
    nw, nh = max(1, int(orig[0] * scale)), max(1, int(orig[1] * scale))
    return img.resize((nw, nh), Image.LANCZOS), orig


def apply_anime_style(
    img: Image.Image,
    style: str = "hayao",
) -> Image.Image:
    """Apply neural anime/cartoon style transfer.

    Falls back to cv2.stylization if the model isn't downloaded yet.

    Args:
        img:   Input image (RGB or RGBA).
        style: One of "hayao", "paprika", "face_paint", "wbc".
    """
    model_id = _STYLE_MAP.get(style)
    if model_id is None:
        return img

    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb = img.convert("RGB")
    orig_size = rgb.size

    try:
        session = get_ort_session(model_id)
    except ModelNotAvailableError:
        return _fallback_style(img, style)

    try:
        work, downscaled_size = _limit_size(rgb)
        inp = _to_tanh(np.array(work))
        input_name  = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        out = session.run([output_name], {input_name: inp})[0]
        result_arr = _from_tanh(out)
        result = Image.fromarray(result_arr, "RGB")
        if result.size != orig_size:
            result = result.resize(orig_size, Image.LANCZOS)
        if alpha is not None:
            result = result.convert("RGBA")
            result.putalpha(alpha)
        return result
    except Exception as e:
        print(f"  [anime] inference failed ({e}); using fallback")
        return _fallback_style(img, style)


def _fallback_style(img: Image.Image, style: str) -> Image.Image:
    """cv2-based fallback when the ONNX model is unavailable."""
    try:
        import cv2
        alpha = img.split()[3] if img.mode == "RGBA" else None
        arr = np.array(img.convert("RGB"))
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        if style in ("hayao", "paprika"):
            out = cv2.stylization(bgr, sigma_s=60, sigma_r=0.07)
        elif style == "face_paint":
            out = cv2.stylization(bgr, sigma_s=60, sigma_r=0.45)
        else:  # wbc — cartoon-like
            out = cv2.stylization(bgr, sigma_s=50, sigma_r=0.45)
        result = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB), "RGB")
        if alpha is not None:
            result = result.convert("RGBA")
            result.putalpha(alpha)
        return result
    except ImportError:
        print(f"  [anime] cv2 not installed and model '{style}' not available — skipping")
        return img


def style_available(style: str) -> bool:
    """True if the ONNX model for this style is already downloaded."""
    mid = _STYLE_MAP.get(style)
    return mid is not None and model_available(mid)
