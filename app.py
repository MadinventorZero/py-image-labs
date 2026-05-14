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

_progress: dict = {"progress": 0, "done": False, "error": None, "gif_b64": None}


class Api:
    def pick_image(self):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Images (*.jpg;*.jpeg;*.png;*.webp)",),
        )
        return result[0] if result else None

    def pick_output_dir(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def get_image_preview(self, path: str):
        try:
            img = Image.open(path)
            img.thumbnail((320, 180), Image.LANCZOS)
            canvas = Image.new("RGB", (320, 180), (20, 22, 27))
            ox = (320 - img.width) // 2
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
        gif_path = cfg.output_dir / f"brand_{first_size}.gif"
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
        gif_b64 = _get_preview_gif(cfg)
        _progress = {"progress": 100, "done": True, "error": None, "gif_b64": gif_b64}
    except Exception as e:
        _progress = {"progress": 0, "done": True, "error": str(e), "gif_b64": None}


def _payload_to_config(payload: dict) -> RenderConfig:
    ip = payload.get("imgProc", {})
    ly = payload.get("layers", {})
    td = payload.get("tagline", {})

    tag = TaglineConfig(
        text          = td.get("text", "Thunder Road Rails"),
        anchor        = td.get("anchor", "center"),
        offset_y      = float(td.get("offset_y", 0.0)),
        font_size_pct = float(td.get("font_size_pct", 0.075)),
        align         = td.get("align", "center"),
        orientation   = td.get("orientation", "horizontal"),
        text_color    = tuple(td.get("text_color", [220, 190, 120])),
        shadow        = bool(td.get("shadow", True)),
        glow          = bool(td.get("glow", True)),
    )

    sizes_flags    = payload.get("sizes", {})
    selected_sizes = {k: v for k, v in ALL_SIZES.items() if sizes_flags.get(k, True)}

    lightning_mode = ly.get("lightning_mode", "simple")
    add_lightning  = lightning_mode != "off"

    return RenderConfig(
        source        = Path(payload["inputPath"]),
        output_dir    = Path(payload["outputDir"]),
        tagline_cfg   = tag,
        remove_bg     = bool(ip.get("remove_bg", True)),
        crop          = bool(ip.get("crop_to_subject", True)),
        crop_padding  = float(ip.get("crop_padding", 0.12)),
        rotate        = int(ip.get("rotate_degrees", 0)),
        resize_pct    = int(ip.get("resize_pct", 100)),
        add_smoke           = bool(ly.get("add_smoke", True)),
        add_lightning       = add_lightning,
        lightning_mode      = lightning_mode if add_lightning else "simple",
        n_bolts             = int(ly.get("n_bolts", 2)),
        branch_depth        = int(ly.get("branch_depth", 4)),
        fork_concentration  = int(ly.get("fork_concentration", 3)),
        subbranch_length    = float(ly.get("subbranch_length", 0.40)),
        add_flash           = bool(ly.get("add_flash", True)),
        add_text      = bool(ly.get("add_text", True)),
        add_embers    = bool(ly.get("add_embers", False)),
        add_rain      = bool(ly.get("add_rain", False)),
        add_vignette  = bool(ly.get("add_vignette", True)),
        add_scanlines = bool(ly.get("add_scanlines", False)),
        output_static = bool(payload.get("output_static", False)),
        tone_mode     = ly.get("tone_mode", "color"),
        stylize_mode  = ly.get("stylize_mode", "none"),
        add_chroma_aberration = bool(ly.get("add_chroma_aberration", False)),
        add_bloom             = bool(ly.get("add_bloom", False)),
        add_film_grain        = bool(ly.get("add_film_grain", False)),
        add_snow              = bool(ly.get("add_snow", False)),
        add_holo              = bool(ly.get("add_holo", False)),
        add_bokeh             = bool(ly.get("add_bokeh", False)),
        sizes         = selected_sizes,
    )


def main() -> None:
    api  = Api()
    here = Path(__file__).parent
    webview.create_window(
        "Brand Image Generator",
        url=(here / "ui" / "index.html").as_uri(),
        js_api=api,
        width=620,
        height=800,
        resizable=False,
        background_color="#1c1e23",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
