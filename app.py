#!/usr/bin/env python3
"""Brand Image Generator — pywebview entry point and Python API bridge."""

import base64
import io
import threading
from pathlib import Path

import webview
from PIL import Image

from engine.models import RenderConfig, TaglineConfig, ALL_SIZES
from engine.pipeline import run_pipeline

# Register HEIF/HEIC/AVIF support if available
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("  pillow-heif registered — HEIC/AVIF input enabled.")
except ImportError:
    pass

_progress: dict = {"progress": 0, "done": False, "error": None, "gif_b64": None}


class Api:
    def pick_image(self):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Images (*.jpg;*.jpeg;*.png;*.webp;*.heic;*.heif;*.avif;*.bmp;*.tiff)",),
        )
        return result[0] if result else None

    def pick_output_dir(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def browse_file(self, options: dict | None = None):
        opts   = options or {}
        exts   = ";".join(f"*.{e}" for e in opts.get("extensions", ["png", "jpg", "webp"]))
        label  = opts.get("title", "Select file")
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=(f"{label} ({exts})",),
        )
        return result[0] if result else None

    def get_image_preview(self, path: str):
        try:
            img = Image.open(path)
            img.thumbnail((320, 180), Image.LANCZOS)
            canvas = Image.new("RGB", (320, 180), (20, 22, 27))
            ox = (320 - img.width)  // 2
            oy = (180 - img.height) // 2
            if img.mode == "RGBA":
                canvas.paste(img, (ox, oy), img)
            else:
                canvas.paste(img.convert("RGB"), (ox, oy))
            buf = io.BytesIO()
            canvas.save(buf, "JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return None

    def get_device_info(self) -> dict:
        from engine.backend import get_best_backend
        return get_best_backend()

    def preview_stack(self, payload: dict) -> str:
        """Render a low-res preview of the current effect stack.

        Returns a data:image/jpeg;base64,… URI.
        Runs in the calling thread (pywebview handles threading).
        """
        from engine.preview import render_preview
        try:
            return render_preview(payload)
        except Exception as e:
            print(f"  [preview] error: {e}")
            import traceback; traceback.print_exc()
            return ""

    def run_generation(self, payload: dict) -> dict:
        global _progress
        _progress = {"progress": 0, "done": False, "error": None, "gif_b64": None}
        cfg = _payload_to_config(payload)
        threading.Thread(target=_run, args=(cfg,), daemon=True).start()
        return {"status": "started"}

    def get_progress(self) -> dict:
        return dict(_progress)


def _set_progress(n: int) -> None:
    global _progress
    _progress["progress"] = n


def _get_preview_gif(cfg: RenderConfig):
    try:
        first_size = next(iter(cfg.sizes))
        gif_path   = cfg.output_dir / f"brand_{first_size}.gif"
        if gif_path.exists():
            img = Image.open(gif_path)
            img.thumbnail((480, 270), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass
    return None


def _run(cfg: RenderConfig) -> None:
    global _progress
    try:
        run_pipeline(cfg, progress_cb=_set_progress)
        gif_b64  = _get_preview_gif(cfg)
        _progress = {"progress": 100, "done": True, "error": None, "gif_b64": gif_b64}
    except Exception as e:
        import traceback; traceback.print_exc()
        _progress = {"progress": 0, "done": True, "error": str(e), "gif_b64": None}


# ── Payload → RenderConfig ────────────────────────────────────────────────────

def _stack_to_flat(stack: list) -> dict:
    """Convert effectStack array to a flat config dict."""
    out: dict = {}
    opacity_map: dict = {}
    for item in stack:
        eid     = item.get("id", "")
        enabled = item.get("enabled", True)
        p       = item.get("params", {})
        opacity_map[eid] = float(item.get("opacity", 1.0))

        if eid == "smoke":
            out["add_smoke"]     = enabled
            out["smoke_density"] = float(p.get("density", 0.7))
        elif eid == "flash":
            out["add_flash"] = enabled
        elif eid == "rain":
            out["add_rain"]     = enabled
            out["rain_n_drops"] = max(10, int(float(p.get("density", 0.6)) * 460))
            out["rain_angle"]   = float(p.get("angle", 12.0))
        elif eid == "snow":
            out["add_snow"] = enabled
        elif eid == "embers":
            out["add_embers"]   = enabled
            out["embers_count"] = int(p.get("count", 60))
        elif eid == "lightning":
            out["lightning_mode"]      = p.get("mode", "simple") if enabled else "off"
            out["n_bolts"]             = int(p.get("n_bolts", 2))
            out["branch_depth"]        = int(p.get("branch_depth", 4))
            out["fork_concentration"]  = int(p.get("fork_concentration", 3))
            out["subbranch_pct"]       = float(p.get("subbranch_pct", 40))
        # ── Neural FX (subject-level) ────────────────────────────
        elif eid in ("anime_hayao", "anime_paprika", "anime_face_paint", "anime_wbc"):
            style_map = {"anime_hayao": "hayao", "anime_paprika": "paprika",
                         "anime_face_paint": "face_paint", "anime_wbc": "wbc"}
            out["anime_style"] = style_map[eid] if enabled else "none"
        elif eid == "chibi":
            out["add_chibi"]        = enabled
            out["chibi_head_pct"]   = float(p.get("head_pct",   42)) / 100.0
            out["chibi_head_scale"] = float(p.get("head_scale", 1.45))
        elif eid == "upscale":
            out["upscale_mode"] = p.get("mode", "x4") if enabled else "none"
        elif eid == "fog":
            out["add_fog"]       = enabled
            out["fog_density"]   = float(p.get("density",    0.4))
            out["fog_height_pct"]= float(p.get("height_pct", 50)) / 100.0
            if "tint" in p: out["fog_tint"] = tuple(int(c) for c in p["tint"])
        elif eid == "god_rays":
            out["add_god_rays"]        = enabled
            out["god_rays_intensity"]  = float(p.get("intensity", 0.5))
            out["god_rays_origin_x"]   = float(p.get("origin_x",  50)) / 100.0
            out["god_rays_origin_y"]   = float(p.get("origin_y",  15)) / 100.0
            if "color" in p: out["god_rays_color"] = tuple(int(c) for c in p["color"])
        elif eid == "glitch":
            out["add_glitch"]           = enabled
            out["glitch_intensity"]     = float(p.get("intensity",    0.5))
            out["glitch_band_count"]    = int(p.get("band_count",     6))
            out["glitch_channel_split"] = bool(p.get("channel_split", True))
        elif eid == "vignette":
            out["add_vignette"]      = enabled
            out["vignette_strength"] = float(p.get("strength", 0.72))
        elif eid == "scanlines":
            out["add_scanlines"]  = enabled
            out["scanlines_alpha"] = int(p.get("alpha", 20))
        elif eid == "tone_grade":
            out["tone_mode"] = p.get("mode", "color") if enabled else "color"
        elif eid == "cartoon_cv2":
            out["stylize_mode"]    = "cartoon" if enabled else "none"
            out["stylize_sigma_s"] = float(p.get("sigma_s", 60.0))
            out["stylize_sigma_r"] = float(p.get("sigma_r", 0.45))
        elif eid == "watercolor":
            out["stylize_mode"]    = "watercolor" if enabled else "none"
            out["stylize_sigma_s"] = float(p.get("sigma_s", 60.0))
            out["stylize_sigma_r"] = float(p.get("sigma_r", 0.07))
        elif eid == "oil_paint":
            out["stylize_mode"] = "oil" if enabled else "none"
        elif eid == "sketch":
            out["stylize_mode"]          = "sketch" if enabled else "none"
            out["stylize_sigma_s"]       = float(p.get("sigma_s", 60.0))
            out["stylize_sigma_r"]       = float(p.get("sigma_r", 0.07))
            out["stylize_shade_factor"]  = float(p.get("shade_factor", 0.05))
        elif eid == "chroma_aberration":
            out["add_chroma_aberration"] = enabled
            out["chroma_shift"]          = int(p.get("shift", 5))
        elif eid == "bloom":
            out["add_bloom"]      = enabled
            out["bloom_radius"]   = int(p.get("radius", 12))
            out["bloom_strength"] = float(p.get("strength", 0.40))
        elif eid == "film_grain":
            out["add_film_grain"]       = enabled
            out["film_grain_intensity"] = float(p.get("intensity", 0.04))
        elif eid == "holo_shimmer":
            out["add_holo"] = enabled
        elif eid == "bokeh":
            out["add_bokeh"]    = enabled
            out["bokeh_radius"] = int(p.get("radius", 18))
        elif eid == "aura":
            out["add_aura"]           = enabled
            out["aura_preset"]        = p.get("preset", "dbz_standard")
            if "core_color"   in p: out["aura_core_color"]   = tuple(p["core_color"])
            if "corona_color" in p: out["aura_corona_color"] = tuple(p["corona_color"])
            out["aura_core_radius"]     = int(p.get("core_radius",   20))
            out["aura_corona_radius"]   = int(p.get("corona_radius", 65))
            out["aura_pulse_speed"]     = float(p.get("pulse_speed",  3.0))
            out["aura_pulse_depth"]     = float(p.get("pulse_depth",  0.12))
            out["aura_electric_fringe"] = bool(p.get("electric_fringe", True))
        elif eid == "sharpen":
            out["add_sharpen"]       = enabled
            out["sharpen_mode"]      = p.get("mode", "usm")
            out["sharpen_amount"]    = float(p.get("amount",    1.0))
            out["sharpen_radius"]    = float(p.get("radius",    2.0))
            out["sharpen_threshold"] = int(p.get("threshold",   3))
        elif eid == "denoise":
            out["add_denoise"]     = enabled
            out["denoise_strength"] = int(p.get("strength", 10))
            out["denoise_mode"]    = p.get("mode", "nlm")
        elif eid == "tagline":
            out["add_text"] = enabled
    out["effect_opacity"] = opacity_map
    return out


def _payload_to_config(payload: dict) -> RenderConfig:
    ip    = payload.get("imgProc",  {})
    td    = payload.get("tagline",  {})
    stack = payload.get("effectStack", [])
    ly    = payload.get("layers",   {})   # legacy flat object fallback

    # Merge: effectStack takes precedence, legacy fills gaps
    flat: dict = {}
    if stack:
        flat = _stack_to_flat(stack)
    # Fill any missing keys from legacy layers
    for k, v in ly.items():
        if k not in flat:
            flat[k] = v

    tag = TaglineConfig(
        text          = td.get("text",          "Thunder Road Rails"),
        anchor        = td.get("anchor",         "center"),
        offset_y      = float(td.get("offset_y",       0.0)),
        font_size_pct = float(td.get("font_size_pct", 0.075)),
        align         = td.get("align",          "center"),
        orientation   = td.get("orientation",    "horizontal"),
        text_color    = tuple(td.get("text_color", [220, 190, 120])),
        shadow        = bool(td.get("shadow", True)),
        glow          = bool(td.get("glow",   True)),
    )

    sizes_flags    = payload.get("sizes", {})
    selected_sizes = {k: v for k, v in ALL_SIZES.items() if sizes_flags.get(k, True)}

    lightning_mode = flat.get("lightning_mode", ly.get("lightning_mode", "simple"))
    add_lightning  = lightning_mode != "off"

    out_fmt = payload.get("output", {})

    return RenderConfig(
        source        = Path(payload["inputPath"]),
        output_dir    = Path(payload["outputDir"]),
        tagline_cfg   = tag,
        remove_bg     = bool(ip.get("remove_bg",       True)),
        crop          = bool(ip.get("crop_to_subject", True)),
        crop_padding  = float(ip.get("crop_padding",  0.12)),
        rotate        = int(ip.get("rotate_degrees",     0)),
        resize_pct    = int(ip.get("resize_pct",       100)),
        anime_style         = flat.get("anime_style",  "none"),
        add_chibi           = bool(flat.get("add_chibi",  False)),
        chibi_head_pct      = float(flat.get("chibi_head_pct",   0.42)),
        chibi_head_scale    = float(flat.get("chibi_head_scale", 1.45)),
        upscale_mode        = flat.get("upscale_mode", "none"),
        add_fog             = bool(flat.get("add_fog",     False)),
        fog_density         = float(flat.get("fog_density",    0.4)),
        fog_height_pct      = float(flat.get("fog_height_pct", 0.5)),
        fog_tint            = tuple(flat.get("fog_tint", (180, 185, 200))),
        add_god_rays        = bool(flat.get("add_god_rays",    False)),
        god_rays_intensity  = float(flat.get("god_rays_intensity", 0.5)),
        god_rays_origin_x   = float(flat.get("god_rays_origin_x",  0.5)),
        god_rays_origin_y   = float(flat.get("god_rays_origin_y",  0.15)),
        god_rays_color      = tuple(flat.get("god_rays_color", (255, 240, 180))),
        add_glitch          = bool(flat.get("add_glitch",     False)),
        glitch_intensity    = float(flat.get("glitch_intensity",    0.5)),
        glitch_band_count   = int(flat.get("glitch_band_count",     6)),
        glitch_channel_split= bool(flat.get("glitch_channel_split", True)),
        add_smoke           = bool(flat.get("add_smoke",  True)),
        smoke_density       = float(flat.get("smoke_density", 0.7)),
        add_lightning       = add_lightning,
        lightning_mode      = lightning_mode if add_lightning else "simple",
        n_bolts             = int(flat.get("n_bolts",             2)),
        branch_depth        = int(flat.get("branch_depth",        4)),
        fork_concentration  = int(flat.get("fork_concentration",  3)),
        subbranch_length    = float(flat.get("subbranch_pct",     40)) / 100.0,
        add_flash           = bool(flat.get("add_flash",  True)),
        add_text            = bool(flat.get("add_text",   True)),
        add_embers          = bool(flat.get("add_embers", False)),
        embers_count        = int(flat.get("embers_count",  80)),
        add_rain            = bool(flat.get("add_rain",   False)),
        rain_n_drops        = int(flat.get("rain_n_drops",  280)),
        rain_angle          = float(flat.get("rain_angle",  12.0)),
        add_vignette        = bool(flat.get("add_vignette",  True)),
        vignette_strength   = float(flat.get("vignette_strength", 0.72)),
        add_scanlines       = bool(flat.get("add_scanlines", False)),
        scanlines_alpha     = int(flat.get("scanlines_alpha",  20)),
        output_static       = bool(payload.get("output_static", False)),
        tone_mode            = flat.get("tone_mode",    "color"),
        stylize_mode         = flat.get("stylize_mode", "none"),
        stylize_sigma_s      = float(flat.get("stylize_sigma_s",      60.0)),
        stylize_sigma_r      = float(flat.get("stylize_sigma_r",      0.45)),
        stylize_shade_factor = float(flat.get("stylize_shade_factor", 0.05)),
        effect_opacity       = flat.get("effect_opacity", {}),
        add_chroma_aberration = bool(flat.get("add_chroma_aberration", False)),
        chroma_shift          = int(flat.get("chroma_shift",   5)),
        add_bloom             = bool(flat.get("add_bloom",  False)),
        bloom_radius          = int(flat.get("bloom_radius",  12)),
        bloom_strength        = float(flat.get("bloom_strength", 0.40)),
        add_film_grain        = bool(flat.get("add_film_grain", False)),
        film_grain_intensity  = float(flat.get("film_grain_intensity", 0.04)),
        add_snow              = bool(flat.get("add_snow",  False)),
        add_holo              = bool(flat.get("add_holo",  False)),
        add_bokeh             = bool(flat.get("add_bokeh", False)),
        bokeh_radius          = int(flat.get("bokeh_radius", 18)),
        add_aura              = bool(flat.get("add_aura",  False)),
        aura_preset           = flat.get("aura_preset", "dbz_standard"),
        aura_core_color       = tuple(flat.get("aura_core_color",   (255, 255, 200))),
        aura_corona_color     = tuple(flat.get("aura_corona_color", (255, 220,  60))),
        aura_core_radius      = int(flat.get("aura_core_radius",    20)),
        aura_corona_radius    = int(flat.get("aura_corona_radius",  65)),
        aura_pulse_speed      = float(flat.get("aura_pulse_speed",  3.0)),
        aura_pulse_depth      = float(flat.get("aura_pulse_depth",  0.12)),
        aura_electric_fringe  = bool(flat.get("aura_electric_fringe", True)),
        add_sharpen           = bool(flat.get("add_sharpen", False)),
        sharpen_mode          = flat.get("sharpen_mode",  "usm"),
        sharpen_amount        = float(flat.get("sharpen_amount",  1.0)),
        sharpen_radius        = float(flat.get("sharpen_radius",  2.0)),
        sharpen_threshold     = int(flat.get("sharpen_threshold",  3)),
        add_denoise           = bool(flat.get("add_denoise", False)),
        denoise_strength      = int(flat.get("denoise_strength", 10)),
        denoise_mode          = flat.get("denoise_mode", "nlm"),
        output_gif            = bool(out_fmt.get("gif",  True)),
        output_webp           = bool(out_fmt.get("webp", False)),
        output_mp4            = bool(out_fmt.get("mp4",  False)),
        output_apng           = bool(out_fmt.get("apng", False)),
        sizes                 = selected_sizes,
    )


def main() -> None:
    api  = Api()
    here = Path(__file__).parent
    webview.create_window(
        "Brand Image Generator",
        url=(here / "ui" / "index.html").as_uri(),
        js_api=api,
        width=640,
        height=860,
        resizable=True,
        background_color="#1c1e23",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
