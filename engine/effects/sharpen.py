"""Sharpening and denoising effects."""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False


def _preserve_alpha(fn):
    """Decorator: strips alpha, applies fn to RGB, reattaches alpha."""
    def wrapper(img: Image.Image, *args, **kwargs) -> Image.Image:
        alpha = img.split()[3] if img.mode == "RGBA" else None
        result = fn(img.convert("RGB"), *args, **kwargs)
        if alpha is not None:
            result = result.convert("RGBA")
            result.putalpha(alpha)
        return result
    return wrapper


@_preserve_alpha
def _usm(img: Image.Image, radius: float, percent: int, threshold: int) -> Image.Image:
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


@_preserve_alpha
def _detail(img: Image.Image, sigma_s: float, sigma_r: float) -> Image.Image:
    if not _CV2:
        return img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=150, threshold=3))
    arr = np.array(img)
    return Image.fromarray(cv2.detailEnhance(arr, sigma_s=sigma_s, sigma_r=sigma_r), "RGB")


@_preserve_alpha
def _nlm_denoise(img: Image.Image, h: int) -> Image.Image:
    if not _CV2:
        return img.filter(ImageFilter.GaussianBlur(radius=1))
    arr = np.array(img)
    return Image.fromarray(cv2.fastNlMeansDenoisingColored(arr, None, h, h, 7, 21), "RGB")


@_preserve_alpha
def _bilateral(img: Image.Image, sigma: int) -> Image.Image:
    if not _CV2:
        return img
    arr = np.array(img)
    return Image.fromarray(cv2.bilateralFilter(arr, d=9, sigmaColor=sigma, sigmaSpace=sigma), "RGB")


def apply_sharpen(
    img: Image.Image,
    mode:      str   = "usm",
    amount:    float = 1.0,
    radius:    float = 2.0,
    threshold: int   = 3,
) -> Image.Image:
    """Dispatch to the requested sharpening mode."""
    if mode == "usm":
        return _usm(img, radius=radius, percent=int(amount * 150), threshold=threshold)
    elif mode in ("clarity", "detail_enhance"):
        sr = max(0.01, 0.10 * amount)
        return _detail(img, sigma_s=max(1, int(10 * amount)), sigma_r=sr)
    return img


def apply_denoise(
    img:      Image.Image,
    strength: int = 10,
    mode:     str = "nlm",
) -> Image.Image:
    """Reduce sensor/JPEG noise. Run before sharpening."""
    if mode == "nlm":
        return _nlm_denoise(img, h=strength)
    elif mode == "bilateral":
        return _bilateral(img, sigma=max(5, strength * 2))
    else:
        k = max(1, strength // 5) * 2 + 1
        alpha = img.split()[3] if img.mode == "RGBA" else None
        out = img.convert("RGB").filter(ImageFilter.GaussianBlur(radius=k // 2))
        if alpha:
            out = out.convert("RGBA")
            out.putalpha(alpha)
        return out
