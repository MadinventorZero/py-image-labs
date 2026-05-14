import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_FLASH_COLOR    = (200, 220, 255)
_FLASH_ENVELOPE = [1.0, 0.60, 0.30, 0.12, 0.04]


def make_flash_layer(canvas_size: tuple[int, int], alpha: float) -> Image.Image:
    if alpha <= 0:
        return Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    r, g, b = _FLASH_COLOR
    a = max(0, min(255, int(210 * alpha)))
    return Image.new("RGBA", canvas_size, (r, g, b, a))


def make_vignette(canvas_size: tuple[int, int], strength: float = 0.72) -> Image.Image:
    w, h = canvas_size
    xs   = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    ys   = np.linspace(-1.0, 1.0, h, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)
    dist   = np.sqrt(xx ** 2 + yy ** 2)
    dist   = np.clip(dist / 1.414, 0.0, 1.0)
    alpha  = (dist ** 2.0 * strength * 255).clip(0, 255).astype(np.uint8)
    rgba   = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def make_scanlines(canvas_size: tuple[int, int], alpha: int = 20) -> Image.Image:
    w, h = canvas_size
    scan = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scan)
    for y in range(0, h, 2):
        draw.line([(0, y), (w - 1, y)], fill=(0, 0, 0, alpha))
    return scan
