"""Fast low-resolution preview renderer for the Effects Lab."""
from __future__ import annotations
import io
import base64
from pathlib import Path
from PIL import Image, ImageFilter

from engine.image_proc import isolate_subject, crop_to_subject
from engine.models import RenderConfig, TaglineConfig

# In-memory cache: (abs_path, remove_bg) → RGBA subject Image
_subject_cache: dict[tuple[str, bool], Image.Image] = {}

_PREVIEW_W = 480
_PREVIEW_H = 270
_BG        = (10, 8, 14)


def _get_subject(source_path: str, remove_bg: bool) -> Image.Image:
    key = (source_path, remove_bg)
    if key not in _subject_cache:
        cfg = RenderConfig(
            source     = Path(source_path),
            output_dir = Path("."),
            remove_bg  = remove_bg,
        )
        raw = isolate_subject(cfg)
        raw = crop_to_subject(raw, padding=0.12)
        _subject_cache[key] = raw
    return _subject_cache[key]


def render_preview(payload: dict) -> str:
    """Render a preview frame from the effectStack payload.

    Returns a data:image/jpeg;base64,… URI string.
    """
    source    = payload.get("inputPath", "")
    remove_bg = payload.get("imgProc", {}).get("remove_bg", True)
    stack     = payload.get("effectStack", [])
    preview_w = int(payload.get("previewSize", _PREVIEW_W))
    preview_h = int(preview_w * 9 / 16)

    canvas = Image.new("RGBA", (preview_w, preview_h), _BG + (255,))

    if not source or not Path(source).exists():
        return _encode(canvas.convert("RGB"))

    try:
        subject = _get_subject(source, remove_bg)
    except Exception as e:
        print(f"  [preview] subject isolation failed: {e}")
        return _encode(canvas.convert("RGB"))

    # ── Scale subject to fit preview canvas ───────────────────────────────
    max_h = int(preview_h * 0.85)
    max_w = int(preview_w * 0.92)
    scale = min(max_h / subject.height, max_w / subject.width)
    sw = max(1, int(subject.width  * scale))
    sh = max(1, int(subject.height * scale))
    scaled = subject.resize((sw, sh), Image.LANCZOS)

    lx = (preview_w - sw) // 2
    ly = max(0, (preview_h - sh) // 2 - int(preview_h * 0.03))

    # ── Apply enabled effects in order ────────────────────────────────────
    # Build lookups: enabled items and per-effect opacity
    enabled: dict[str, dict] = {}
    opacities: dict[str, float] = {}
    for item in stack:
        eid = item["id"]
        opacities[eid] = float(item.get("opacity", 1.0))
        if item.get("enabled", True):
            enabled[eid] = item.get("params", {})

    def _op(layer, eid):
        pct = opacities.get(eid, 1.0)
        if pct >= 1.0:
            return layer
        r, g, b, a = layer.split()
        return Image.merge("RGBA", (r, g, b, a.point(lambda x: int(x * pct))))

    # Fog
    if "fog" in enabled:
        try:
            from engine.effects.atmosphere import make_fog_frame
            p = enabled["fog"]
            tint = tuple(int(c) for c in p["tint"]) if "tint" in p else (180, 185, 200)
            canvas = Image.alpha_composite(canvas,
                _op(make_fog_frame(
                    (preview_w, preview_h), 0.0,
                    density    = float(p.get("density",    0.4)),
                    tint       = tint,
                    height_pct = float(p.get("height_pct", 50)) / 100.0,
                ), "fog"))
        except Exception as e:
            print(f"  [preview] fog failed: {e}")

    # God rays
    if "god_rays" in enabled:
        try:
            from engine.effects.atmosphere import make_god_rays_frame
            p = enabled["god_rays"]
            color = tuple(int(c) for c in p["color"]) if "color" in p else (255, 240, 180)
            canvas = Image.alpha_composite(canvas,
                _op(make_god_rays_frame(
                    (preview_w, preview_h), 0.0,
                    intensity = float(p.get("intensity", 0.5)),
                    origin_x  = float(p.get("origin_x",  50)) / 100.0,
                    origin_y  = float(p.get("origin_y",  15)) / 100.0,
                    color     = color,
                ), "god_rays"))
        except Exception as e:
            print(f"  [preview] god_rays failed: {e}")

    # Bokeh (BG blur before subject)
    if "bokeh" in enabled:
        radius = int(enabled["bokeh"].get("radius", 18))
        blurred = canvas.filter(ImageFilter.GaussianBlur(radius=radius))
        bk_op = opacities.get("bokeh", 1.0)
        canvas = Image.blend(canvas, blurred, bk_op) if bk_op < 1.0 else blurred

    # Aura underlayer
    if "aura" in enabled:
        try:
            import numpy as np
            from engine.effects.aura import make_aura_frame
            p = enabled["aura"]
            mask = np.zeros((preview_h, preview_w), dtype=np.uint8)
            alpha_patch = np.array(scaled.split()[3], dtype=np.uint8)
            ph = min(sh, preview_h - max(0, ly))
            pw = min(sw, preview_w - max(0, lx))
            if ph > 0 and pw > 0:
                mask[max(0, ly):max(0, ly)+ph, max(0, lx):max(0, lx)+pw] = alpha_patch[:ph, :pw]
            aura_layer = make_aura_frame(
                mask, (preview_w, preview_h), 0.0,
                preset          = p.get("preset", "dbz_standard"),
                core_color      = tuple(p["core_color"])   if "core_color"   in p else None,
                corona_color    = tuple(p["corona_color"]) if "corona_color" in p else None,
                core_radius     = p.get("core_radius"),
                corona_radius   = p.get("corona_radius"),
                pulse_speed     = p.get("pulse_speed", 3.0),
                pulse_depth     = 0.0,  # static for preview
                electric_fringe = p.get("electric_fringe", True),
            )
            canvas = Image.alpha_composite(canvas, _op(aura_layer, "aura"))
        except Exception as e:
            print(f"  [preview] aura failed: {e}")

    # Subject
    canvas.paste(scaled, (lx, ly), scaled)

    # Holo
    if "holo_shimmer" in enabled:
        try:
            import numpy as np
            from engine.effects.post import make_holo_frame
            mask_img = Image.new("L", (preview_w, preview_h), 0)
            mask_img.paste(scaled.split()[3], (lx, ly))
            canvas = Image.alpha_composite(canvas,
                _op(make_holo_frame((preview_w, preview_h), 0.0, mask_img), "holo_shimmer"))
        except Exception as e:
            print(f"  [preview] holo failed: {e}")

    # Tone mode
    tone_item = enabled.get("tone_grade")
    if tone_item:
        from engine.effects.post import apply_tone_mode
        mode = tone_item.get("mode", "color")
        if mode != "color":
            tn_op = opacities.get("tone_grade", 1.0)
            toned = apply_tone_mode(canvas, mode)
            if toned.mode != "RGBA":
                toned = toned.convert("RGBA")
            canvas = Image.blend(canvas, toned, tn_op) if tn_op < 1.0 else toned

    # Neural anime / cartoon style (applied to whole canvas at preview quality)
    anime_map = {
        "anime_hayao":       "hayao",
        "anime_paprika":     "paprika",
        "anime_face_paint":  "face_paint",
        "anime_wbc":         "wbc",
    }
    for eid, style in anime_map.items():
        if eid in enabled:
            try:
                from engine.effects.anime import apply_anime_style
                canvas = apply_anime_style(canvas, style)
                if canvas.mode != "RGBA":
                    canvas = canvas.convert("RGBA")
            except Exception as e:
                print(f"  [preview] {eid} failed: {e}")
            break  # only one anime style at a time

    # Chibi (applied to whole canvas for preview)
    if "chibi" in enabled:
        try:
            from engine.effects.chibi import apply_chibi
            p = enabled["chibi"]
            canvas = apply_chibi(
                canvas,
                head_pct   = float(p.get("head_pct",   42)) / 100.0,
                head_scale = float(p.get("head_scale", 1.45)),
            )
            if canvas.mode != "RGBA":
                canvas = canvas.convert("RGBA")
        except Exception as e:
            print(f"  [preview] chibi failed: {e}")

    # Upscale (skip in preview — would make preview image too large)

    # Stylisation
    for eid, cv_mode in [
        ("cartoon_cv2", "cartoon"),
        ("watercolor",  "watercolor"),
        ("oil_paint",   "oil"),
        ("sketch",      "sketch"),
    ]:
        if eid in enabled:
            from engine.effects.post import apply_stylize
            p = enabled[eid]
            stylized = apply_stylize(
                canvas, cv_mode,
                sigma_s      = float(p.get("sigma_s",      60.0)),
                sigma_r      = float(p.get("sigma_r",      0.45 if cv_mode == "cartoon" else 0.07)),
                shade_factor = float(p.get("shade_factor", 0.05)),
            )
            if stylized.mode != "RGBA":
                stylized = stylized.convert("RGBA")
            canvas = stylized
            break

    # Chroma aberration
    if "chroma_aberration" in enabled:
        from engine.effects.post import apply_chromatic_aberration
        ca_op = opacities.get("chroma_aberration", 1.0)
        shift = int(enabled["chroma_aberration"].get("shift", 5))
        chromed = apply_chromatic_aberration(canvas.convert("RGB"), shift).convert("RGBA")
        canvas = Image.blend(canvas, chromed, ca_op) if ca_op < 1.0 else chromed

    # Bloom
    if "bloom" in enabled:
        from engine.effects.post import apply_bloom
        bl_op = opacities.get("bloom", 1.0)
        p = enabled["bloom"]
        bloomed = apply_bloom(canvas.convert("RGB"), p.get("radius", 12), p.get("strength", 0.40)).convert("RGBA")
        canvas = Image.blend(canvas, bloomed, bl_op) if bl_op < 1.0 else bloomed

    # Glitch
    if "glitch" in enabled:
        try:
            from engine.effects.glitch import apply_glitch
            gl_op = opacities.get("glitch", 1.0)
            p = enabled["glitch"]
            glitched = apply_glitch(
                canvas,
                t             = 0.25,
                intensity     = float(p.get("intensity",    0.5)),
                band_count    = int(p.get("band_count",     6)),
                channel_split = bool(p.get("channel_split", True)),
            ).convert("RGBA")
            canvas = Image.blend(canvas, glitched, gl_op) if gl_op < 1.0 else glitched
        except Exception as e:
            print(f"  [preview] glitch failed: {e}")

    # Denoise
    if "denoise" in enabled:
        from engine.effects.sharpen import apply_denoise
        dn_op = opacities.get("denoise", 1.0)
        p = enabled["denoise"]
        denoised = apply_denoise(canvas, strength=p.get("strength", 10), mode=p.get("mode", "nlm")).convert("RGBA")
        canvas = Image.blend(canvas, denoised, dn_op) if dn_op < 1.0 else denoised

    # Sharpen
    if "sharpen" in enabled:
        from engine.effects.sharpen import apply_sharpen
        sh_op = opacities.get("sharpen", 1.0)
        p = enabled["sharpen"]
        sharpened = apply_sharpen(
            canvas, mode=p.get("mode", "usm"),
            amount=p.get("amount", 1.0), radius=p.get("radius", 2.0),
            threshold=p.get("threshold", 3),
        ).convert("RGBA")
        canvas = Image.blend(canvas, sharpened, sh_op) if sh_op < 1.0 else sharpened

    # Film grain
    if "film_grain" in enabled:
        from engine.effects.post import apply_film_grain
        gr_op = opacities.get("film_grain", 1.0)
        p = enabled["film_grain"]
        grainy = apply_film_grain(canvas.convert("RGB"), p.get("intensity", 0.04), seed=0).convert("RGBA")
        canvas = Image.blend(canvas, grainy, gr_op) if gr_op < 1.0 else grainy

    # Vignette
    if "vignette" in enabled:
        from engine.effects.overlay import make_vignette
        p = enabled["vignette"]
        canvas = Image.alpha_composite(canvas,
            _op(make_vignette((preview_w, preview_h), p.get("strength", 0.72)), "vignette"))

    # Scan lines
    if "scanlines" in enabled:
        from engine.effects.overlay import make_scanlines
        p = enabled["scanlines"]
        canvas = Image.alpha_composite(canvas,
            _op(make_scanlines((preview_w, preview_h), p.get("alpha", 20)), "scanlines"))

    return _encode(canvas.convert("RGB"))


def _encode(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def clear_cache() -> None:
    _subject_cache.clear()
