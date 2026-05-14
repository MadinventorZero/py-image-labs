from PIL import Image, ImageDraw, ImageFilter

from engine.models import RenderConfig, ALL_SIZES, FRAMES_OVERRIDE
from engine.effects.smoke import make_smoke_frame
from engine.effects.lightning import (
    generate_lightning_bolt, make_lightning_layer,
    generate_ground_strike, generate_atmospheric_intracloud,
    generate_full_storm, make_ground_contact_glow,
    make_atmospheric_lightning_layer,
)
from engine.effects.particles import make_embers_frame, make_rain_frame, make_snow_frame
from engine.effects.text_render import get_font, build_word_layout, _draw_word
from engine.effects.post import (
    apply_tone_mode, apply_chromatic_aberration, apply_bloom,
    apply_film_grain, make_holo_frame,
)
from engine.effects.overlay import (
    _FLASH_ENVELOPE, make_flash_layer, make_vignette, make_scanlines,
)
from engine.image_proc import isolate_subject, apply_image_processing


def build_frame(
    canvas_size: tuple[int, int],
    lantern: Image.Image,
    lantern_pos: tuple[int, int],
    lantern_size: tuple[int, int],
    smoke_x_min: float,
    smoke_x_max: float,
    smoke_y: float,
    frame_idx: int,
    total_frames: int,
    font: "ImageFont.FreeTypeFont | None",
    word_layout: list[tuple[int, int, str]],
    cfg: RenderConfig,
    flash_alpha: float = 0.0,
    lightning_bolts: "list | None" = None,
    bolt_trees: "list | None" = None,
    ground_points: "list | None" = None,
    lightning_alpha: float = 0.0,
    embers_origin: "tuple | None" = None,
    vignette_layer: "Image.Image | None" = None,
    scanlines_layer: "Image.Image | None" = None,
) -> Image.Image:
    t   = frame_idx / total_frames
    tag = cfg.tagline_cfg

    frame = Image.new("RGBA", canvas_size, cfg.bg_color + (255,))

    if cfg.add_rain:
        frame = Image.alpha_composite(frame, make_rain_frame(canvas_size, t))
    if cfg.add_snow:
        frame = Image.alpha_composite(frame, make_snow_frame(canvas_size, t))

    if cfg.add_lightning and lightning_alpha > 0:
        if cfg.lightning_mode in ("ground_strike", "atmospheric", "full_storm") and bolt_trees:
            frame = Image.alpha_composite(
                frame,
                make_atmospheric_lightning_layer(canvas_size, bolt_trees,
                                                 lightning_alpha, cfg.branch_depth),
            )
            if ground_points:
                frame = Image.alpha_composite(
                    frame,
                    make_ground_contact_glow(canvas_size, ground_points, lightning_alpha),
                )
        elif lightning_bolts:
            frame = Image.alpha_composite(
                frame, make_lightning_layer(canvas_size, lightning_bolts, lightning_alpha)
            )

    if cfg.add_smoke:
        frame = Image.alpha_composite(
            frame,
            make_smoke_frame(canvas_size, t * 0.5,
                             smoke_x_min, smoke_x_max, smoke_y, cfg.smoke_tint),
        )

    if cfg.add_embers and embers_origin:
        frame = Image.alpha_composite(
            frame, make_embers_frame(canvas_size, t, embers_origin[0], embers_origin[1])
        )

    if cfg.add_bokeh and cfg.bokeh_radius > 0:
        frame = frame.filter(ImageFilter.GaussianBlur(radius=cfg.bokeh_radius))

    lx, ly = lantern_pos
    lw, lh = lantern_size
    scaled = lantern.resize((lw, lh), Image.LANCZOS)
    frame.paste(scaled, (lx, ly), scaled)

    if cfg.add_holo:
        subj_mask = Image.new("L", canvas_size, 0)
        subj_mask.paste(scaled.split()[3], (lx, ly))
        frame = Image.alpha_composite(frame, make_holo_frame(canvas_size, t, subj_mask))

    if cfg.add_text and font and word_layout:
        n_words = len(word_layout)
        act_len = total_frames / n_words
        visible = min(n_words, int(frame_idx / act_len) + 1)
        if tag.orientation == "vertical_cw":
            text_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(text_layer)
            for wx, wy, word in word_layout[:visible]:
                _draw_word(tdraw, word, wx, wy, font,
                           tag.text_color, cfg.shadow_color, tag.shadow, tag.glow)
            text_layer = text_layer.rotate(-90, expand=False)
            frame = Image.alpha_composite(frame, text_layer)
        else:
            draw = ImageDraw.Draw(frame)
            for wx, wy, word in word_layout[:visible]:
                _draw_word(draw, word, wx, wy, font,
                           tag.text_color, cfg.shadow_color, tag.shadow, tag.glow)

    if cfg.add_flash and flash_alpha > 0:
        frame = Image.alpha_composite(frame, make_flash_layer(canvas_size, flash_alpha))

    if cfg.tone_mode != "color":
        frame = apply_tone_mode(frame, cfg.tone_mode)
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")

    if cfg.add_chroma_aberration:
        frame = apply_chromatic_aberration(
            frame.convert("RGB"), cfg.chroma_shift
        ).convert("RGBA")

    if cfg.add_bloom:
        frame = apply_bloom(
            frame.convert("RGB"), cfg.bloom_radius, cfg.bloom_strength
        ).convert("RGBA")

    if vignette_layer is not None:
        frame = Image.alpha_composite(frame, vignette_layer)

    if scanlines_layer is not None:
        frame = Image.alpha_composite(frame, scanlines_layer)

    rgb_out = frame.convert("RGB")
    if cfg.add_film_grain:
        rgb_out = apply_film_grain(rgb_out, cfg.film_grain_intensity, seed=frame_idx)
    return rgb_out


def generate_size(
    size_name: str,
    canvas_size: tuple[int, int],
    lantern: Image.Image,
    cfg: RenderConfig,
) -> None:
    w, h      = canvas_size
    tag       = cfg.tagline_cfg
    n_frames  = FRAMES_OVERRIDE.get(size_name, cfg.frames)
    print(f"  Building {size_name} ({w}×{h}, {n_frames} frames)...")

    max_lh = int(h * (0.88 if w > h else 0.80))
    max_lw = int(w * 0.94)
    scale  = min(max_lh / lantern.height, max_lw / lantern.width)
    lh = int(lantern.height * scale)
    lw = int(lantern.width  * scale)
    lx = (w - lw) // 2
    ly = max(0, (h - lh) // 2 - int(h * 0.03))

    smoke_x_min = 0.0
    smoke_x_max = float(w)
    smoke_y     = float(h)

    font        = None
    word_layout: list[tuple[int, int, str]] = []
    if cfg.add_text and tag.text:
        font_size   = max(28, int(h * tag.font_size_pct))
        font        = get_font(font_size)
        word_layout = build_word_layout(tag, font, w, h, ly, lh, font_size)

    strike_starts    = [int(n_frames * 0.17), int(n_frames * 0.58)]
    n_strikes        = len(strike_starts)
    flash_alphas     = [0.0] * n_frames
    lightning_alphas = [0.0] * n_frames
    frame_strike_idx = [-1]  * n_frames
    bolt_envelope    = [0.4, 1.0, 0.55, 0.2]
    for s_idx, sf in enumerate(strike_starts):
        if cfg.add_flash:
            for j, fa in enumerate(_FLASH_ENVELOPE):
                flash_alphas[(sf + j) % n_frames] = max(flash_alphas[(sf + j) % n_frames], fa)
        if cfg.add_lightning:
            for j, la in enumerate(bolt_envelope):
                fi = (sf + j) % n_frames
                lightning_alphas[fi] = max(lightning_alphas[fi], la)
                frame_strike_idx[fi] = s_idx

    _s_bolts: list = [None] * n_strikes
    _s_trees: list = [None] * n_strikes
    _s_gpts:  list = [[]   for _ in range(n_strikes)]

    if cfg.add_lightning:
        for s in range(n_strikes):
            sseed = w * h + s * 1337
            if cfg.lightning_mode == "ground_strike":
                n = cfg.n_bolts
                origins = ([0.50] if n == 1 else
                           [0.25 + i * (0.52 / max(1, n - 1)) for i in range(n)])
                trees, gpts_s = [], []
                for i, ox in enumerate(origins):
                    segs, gpt = generate_ground_strike(
                        canvas_size, seed=sseed + i * 37,
                        origin_x_frac=ox, depth=cfg.branch_depth,
                        fork_concentration=cfg.fork_concentration,
                        subbranch_length=cfg.subbranch_length,
                    )
                    trees.extend(segs)
                    gpts_s.append(gpt)
                _s_trees[s] = trees
                _s_gpts[s]  = gpts_s

            elif cfg.lightning_mode == "atmospheric":
                trees, _ = generate_atmospheric_intracloud(
                    canvas_size, seed=sseed,
                    n_spines=cfg.n_bolts, depth=cfg.branch_depth,
                    fork_concentration=cfg.fork_concentration,
                    subbranch_length=cfg.subbranch_length,
                )
                _s_trees[s] = trees

            elif cfg.lightning_mode == "full_storm":
                trees, gpts_s = generate_full_storm(
                    canvas_size, seed=sseed,
                    n_ground_strikes=cfg.n_bolts, depth=cfg.branch_depth,
                    fork_concentration=cfg.fork_concentration,
                    subbranch_length=cfg.subbranch_length,
                )
                _s_trees[s] = trees
                _s_gpts[s]  = gpts_s

            else:
                _s_bolts[s] = generate_lightning_bolt(canvas_size, seed=sseed)

    vignette_layer  = make_vignette(canvas_size)  if cfg.add_vignette  else None
    scanlines_layer = make_scanlines(canvas_size) if cfg.add_scanlines else None
    embers_origin = (lx + lw // 2, ly + lh // 4) if cfg.add_embers else None

    frames: list[Image.Image] = []
    for i in range(n_frames):
        s_idx     = frame_strike_idx[i]
        cur_bolts = _s_bolts[s_idx] if s_idx >= 0 else None
        cur_trees = _s_trees[s_idx] if s_idx >= 0 else None
        cur_gpts  = _s_gpts[s_idx]  if s_idx >= 0 else []
        f = build_frame(
            canvas_size     = canvas_size,
            lantern         = lantern,
            lantern_pos     = (lx, ly),
            lantern_size    = (lw, lh),
            smoke_x_min     = smoke_x_min,
            smoke_x_max     = smoke_x_max,
            smoke_y         = smoke_y,
            frame_idx       = i,
            total_frames    = n_frames,
            font            = font,
            word_layout     = word_layout,
            cfg             = cfg,
            flash_alpha     = flash_alphas[i],
            lightning_bolts = cur_bolts,
            bolt_trees      = cur_trees,
            ground_points   = cur_gpts,
            lightning_alpha = lightning_alphas[i],
            embers_origin   = embers_origin,
            vignette_layer  = vignette_layer,
            scanlines_layer = scanlines_layer,
        )
        frames.append(f.convert("P", palette=Image.ADAPTIVE, colors=256))

    out = cfg.output_dir / f"brand_{size_name}.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=cfg.frame_ms,
        loop=0,
    )
    kb = out.stat().st_size // 1024
    print(f"    → {out}  ({kb} KB)")

    if cfg.output_static:
        if cfg.add_lightning and any(la > 0 for la in lightning_alphas):
            peak_la = max(lightning_alphas)
            peak_fi = lightning_alphas.index(peak_la)
            peak_si = frame_strike_idx[peak_fi]
        else:
            peak_fi = n_frames // 4
            peak_la = 0.0
            peak_si = -1
        static_frame = build_frame(
            canvas_size     = canvas_size,
            lantern         = lantern,
            lantern_pos     = (lx, ly),
            lantern_size    = (lw, lh),
            smoke_x_min     = smoke_x_min,
            smoke_x_max     = smoke_x_max,
            smoke_y         = smoke_y,
            frame_idx       = peak_fi,
            total_frames    = n_frames,
            font            = font,
            word_layout     = word_layout,
            cfg             = cfg,
            flash_alpha     = flash_alphas[peak_fi],
            lightning_bolts = _s_bolts[peak_si] if peak_si >= 0 else None,
            bolt_trees      = _s_trees[peak_si] if peak_si >= 0 else None,
            ground_points   = _s_gpts[peak_si]  if peak_si >= 0 else [],
            lightning_alpha = peak_la,
            embers_origin   = embers_origin,
            vignette_layer  = vignette_layer,
            scanlines_layer = scanlines_layer,
        )
        static_out = cfg.output_dir / f"brand_{size_name}_peak.png"
        static_frame.save(static_out)
        static_kb = static_out.stat().st_size // 1024
        print(f"    → {static_out}  ({static_kb} KB, static PNG)")


def run_pipeline(cfg: RenderConfig, progress_cb=None) -> None:
    def _prog(n):
        if progress_cb:
            progress_cb(n)

    print("\nBrand Image Generator")
    print("=" * 40)
    _prog(5)

    subject_raw = isolate_subject(cfg)
    subject     = apply_image_processing(subject_raw, cfg)
    print(f"Subject isolated: {subject.width}×{subject.height}px\n")
    _prog(20)

    n_sizes = len(cfg.sizes)
    for i, (size_name, size) in enumerate(cfg.sizes.items()):
        generate_size(size_name, size, subject, cfg)
        print()
        _prog(20 + int(80 * (i + 1) / n_sizes))

    print("All done. Files written to:", cfg.output_dir)
