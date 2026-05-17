import math

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def apply_tone_mode(img: Image.Image, mode: str) -> Image.Image:
    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb   = img.convert("RGB")

    if mode == "bw":
        out = rgb.convert("L").convert("RGB")

    elif mode == "sepia":
        gray = rgb.convert("L")
        out  = Image.merge("RGB", (
            gray.point(lambda p: min(255, int(p * 1.08))),
            gray.point(lambda p: min(255, int(p * 0.87))),
            gray.point(lambda p: min(255, int(p * 0.69))),
        ))

    elif mode == "negative":
        out = ImageOps.invert(rgb)

    elif mode == "solarize":
        out = ImageOps.solarize(rgb, threshold=128)

    elif mode == "historical":
        gray = rgb.convert("L")
        out  = Image.merge("RGB", (
            gray.point(lambda p: min(255, int(p * 0.94 + 22))),
            gray.point(lambda p: min(255, int(p * 0.79 + 12))),
            gray.point(lambda p: min(255, int(p * 0.62 +  8))),
        ))
        w2, h2 = out.size
        xi = np.linspace(-1, 1, w2, dtype=np.float32)
        yi = np.linspace(-1, 1, h2, dtype=np.float32)
        X, Y  = np.meshgrid(xi, yi)
        burn  = np.clip((X ** 2 + Y ** 2) * 0.42, 0, 1)[:, :, np.newaxis]
        out   = Image.fromarray(
            (np.array(out, dtype=np.float32) * (1 - burn * 0.45)).clip(0, 255).astype(np.uint8),
            "RGB",
        )

    else:
        out = rgb

    if alpha is not None:
        out = out.convert("RGBA")
        out.putalpha(alpha)
    return out


def apply_chromatic_aberration(img: Image.Image, shift: int = 5) -> Image.Image:
    if shift <= 0:
        return img
    alpha = img.split()[3] if img.mode == "RGBA" else None
    arr   = np.array(img.convert("RGB"), dtype=np.uint8)
    out   = np.zeros_like(arr)
    out[:, shift:,  0] = arr[:, :-shift, 0]
    out[:, :,       1] = arr[:, :,       1]
    out[:, :-shift, 2] = arr[:, shift:,  2]
    result = Image.fromarray(out, "RGB")
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result


def apply_bloom(
    img: Image.Image,
    radius: int = 12,
    strength: float = 0.40,
) -> Image.Image:
    arr  = np.array(img.convert("RGB"), dtype=np.float32)
    lum  = arr.mean(axis=2)
    mask = np.clip((lum - 185) / 70.0, 0, 1)[:, :, np.newaxis]
    hi   = Image.fromarray((arr * mask).clip(0, 255).astype(np.uint8), "RGB")
    glow = hi.filter(ImageFilter.GaussianBlur(radius=radius))
    out  = np.clip(arr + np.array(glow, dtype=np.float32) * strength, 0, 255).astype(np.uint8)
    result = Image.fromarray(out, "RGB")
    if img.mode == "RGBA":
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


def apply_film_grain(img: Image.Image, intensity: float = 0.04, seed: int = 0) -> Image.Image:
    rng  = np.random.default_rng(seed)
    arr  = np.array(img.convert("RGB"), dtype=np.float32)
    arr += rng.normal(0, intensity * 255, arr.shape).astype(np.float32)
    result = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")
    if img.mode == "RGBA":
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


def make_holo_frame(
    canvas_size: tuple[int, int],
    t: float,
    subject_mask: Image.Image,
) -> Image.Image:
    w, h = canvas_size
    xi = np.linspace(0, 1, w, dtype=np.float32)
    yi = np.linspace(0, 1, h, dtype=np.float32)
    X, Y = np.meshgrid(xi, yi)

    hue  = (X * 0.7 + Y * 0.2 + t * 0.45) % 1.0
    h6   = hue * 6
    sec  = np.floor(h6).astype(int) % 6
    f    = h6 - np.floor(h6)
    sat, val = 0.75, 0.90
    p, q, tv = val * (1 - sat), val * (1 - sat * f), val * (1 - sat * (1 - f))
    R = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [val,q,p,p,tv], default=val)
    G = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [tv,val,val,q,p], default=p)
    B = np.select([sec==0, sec==1, sec==2, sec==3, sec==4], [p,p,tv,val,val], default=q)

    shimmer = np.sin(X * math.pi * 4 + t * math.tau * 1.5) * 0.5 + 0.5

    mask_img = (subject_mask.resize(canvas_size, Image.LANCZOS)
                if subject_mask.size != canvas_size else subject_mask)
    mask_arr = np.array(mask_img, dtype=np.float32) / 255.0

    alpha_arr = (shimmer * mask_arr * 90).clip(0, 255)
    out = np.stack(
        [R * 255, G * 255, B * 255, alpha_arr], axis=2
    ).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def apply_stylize(
    img: Image.Image,
    mode: str,
    sigma_s: float = 60.0,
    sigma_r: float = 0.45,
    shade_factor: float = 0.05,
) -> Image.Image:
    if mode == "none":
        return img
    try:
        import cv2
    except ImportError:
        print(f"  [Warning] opencv-python not installed — stylize_mode={mode!r} skipped.")
        return img

    alpha = img.split()[3] if img.mode == "RGBA" else None
    rgb   = np.array(img.convert("RGB"))
    bgr   = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    if mode in ("cartoon", "watercolor"):
        out_bgr = cv2.stylization(bgr, sigma_s=float(sigma_s), sigma_r=float(sigma_r))
    elif mode == "oil":
        try:
            out_bgr = cv2.xphoto.oilPainting(bgr, size=4, dynRatio=1)
        except AttributeError:
            out_bgr = cv2.stylization(bgr, sigma_s=40, sigma_r=0.30)
    elif mode == "sketch":
        _, sketch_gray = cv2.pencilSketch(
            bgr,
            sigma_s=float(sigma_s),
            sigma_r=float(sigma_r),
            shade_factor=float(shade_factor),
        )
        out_bgr = cv2.cvtColor(sketch_gray, cv2.COLOR_GRAY2BGR)
    else:
        return img

    result = Image.fromarray(cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB), "RGB")
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result
