import io

from PIL import Image
from rembg import remove, new_session

from engine.models import RenderConfig
from engine.effects.post import apply_stylize


def _rembg_session():
    try:
        session = new_session("birefnet-general")
        print("  Using BiRefNet model for subject extraction.")
        return session
    except Exception as e:
        print(f"  BiRefNet unavailable ({e}), falling back to u2net.")
        return new_session("u2net")


def isolate_subject(cfg: RenderConfig) -> Image.Image:
    if cfg.remove_bg:
        print(f"  Removing background from {cfg.source.name}...")
        raw     = cfg.source.read_bytes()
        session = _rembg_session()
        result  = remove(raw, session=session)
        img     = Image.open(io.BytesIO(result)).convert("RGBA")
    else:
        print(f"  Loading {cfg.source.name} (background removal skipped)...")
        img = Image.open(cfg.source).convert("RGBA")
    return img


def crop_to_subject(img: Image.Image, padding: float = 0.12) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    pw = int((r - l) * padding)
    ph = int((b - t) * padding)
    return img.crop((
        max(0, l - pw), max(0, t - ph),
        min(img.width, r + pw), min(img.height, b + ph),
    ))


def apply_image_processing(img: Image.Image, cfg: RenderConfig) -> Image.Image:
    if cfg.crop:
        img = crop_to_subject(img, padding=cfg.crop_padding)
    if cfg.rotate:
        img = img.rotate(-cfg.rotate, expand=True)
    if cfg.resize_pct != 100:
        nw = max(1, int(img.width  * cfg.resize_pct / 100))
        nh = max(1, int(img.height * cfg.resize_pct / 100))
        img = img.resize((nw, nh), Image.LANCZOS)
    if cfg.stylize_mode != "none":
        img = apply_stylize(img, cfg.stylize_mode)
    return img
