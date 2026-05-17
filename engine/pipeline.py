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
from engine.effects.aura import make_aura_frame
from engine.effects.sharpen import apply_sharpen, apply_denoise
from engine.effects.atmosphere import make_fog_frame, make_god_rays_frame
from engine.effects.glitch import apply_glitch
from engine.image_proc import isolate_subject, apply_image_processing


def _opacity(layer: "Image.Image", pct: float) -> "Image.Image":
    """Scale the alpha channel of an RGBA layer by pct (0.0–1.0)."""
    if pct >= 1.0:
        return layer
    r, g, b, a = layer.split()
    a = a.point(lambda x: int(x * pct))
    return Image.merge("RGBA", (r, g, b, a))


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
        frame = Image.alpha_composite(frame,
            _opacity(make_rain_frame(canvas_size, t, n_drops=cfg.rain_n_drops, angle_deg=cfg.rain_angle),
                     cfg.effect_opacity.get("rain", 1.0)))
    if cfg.add_snow:
        frame = Image.alpha_composite(frame,
            _opacity(make_snow_frame(canvas_size, t),
                     cfg.effect_opacity.get("snow", 1.0)))

    if cfg.add_lightning and lightning_alpha > 0:
        _lg_op = cfg.effect_opacity.get("lightning", 1.0)
        if cfg.lightning_mode in ("ground_strike", "atmospheric", "full_storm") and bolt_trees:
            frame = Image.alpha_composite(
                frame,
                _opacity(make_atmospheric_lightning_layer(canvas_size, bolt_trees,
                                                          lightning_alpha, cfg.branch_depth),
                         _lg_op),
            )
            if ground_points:
                frame = Image.alpha_composite(
                    frame,
                    _opacity(make_ground_contact_glow(canvas_size, ground_points, lightning_alpha),
                             _lg_op),
                )
        elif lightning_bolts:
            frame = Image.alpha_composite(
                frame,
                _opacity(make_lightning_layer(canvas_size, lightning_bolts, lightning_alpha),
                         _lg_op),
            )

    if cfg.add_smoke:
        _smoke_n = max(20, int(cfg.smoke_density * 220))
        frame = Image.alpha_composite(
            frame,
            _opacity(make_smoke_frame(canvas_size, t * 0.5,
                                      smoke_x_min, smoke_x_max, smoke_y, cfg.smoke_tint,
                                      num_particles=_smoke_n),
                     cfg.effect_opacity.get("smoke", 1.0)),
        )

    if cfg.add_embers and embers_origin:
        frame = Image.alpha_composite(
            frame,
            _opacity(make_embers_frame(canvas_size, t, embers_origin[0], embers_origin[1],
                                       count=cfg.embers_count),
                     cfg.effect_opacity.get("embers", 1.0)),
        )

    if cfg.add_fog:
        frame = Image.alpha_composite(frame,
            _opacity(make_fog_frame(canvas_size, t,
                                    density=cfg.fog_density,
                                    tint=cfg.fog_tint,
                                    height_pct=cfg.fog_height_pct),
                     cfg.effect_opacity.get("fog", 1.0)))

    if cfg.add_god_rays:
        frame = Image.alpha_composite(frame,
            _opacity(make_god_rays_frame(canvas_size, t,
                                         intensity=cfg.god_rays_intensity,
                                         origin_x=cfg.god_rays_origin_x,
                                         origin_y=cfg.god_rays_origin_y,
                                         color=cfg.god_rays_color),
                     cfg.effect_opacity.get("god_rays", 1.0)))

    if cfg.add_bokeh and cfg.bokeh_radius > 0:
        _bk_op = cfg.effect_opacity.get("bokeh", 1.0)
        blurred = frame.filter(ImageFilter.GaussianBlur(radius=cfg.bokeh_radius))
        frame = Image.blend(frame, blurred, _bk_op) if _bk_op < 1.0 else blurred

    lx, ly = lantern_pos
    lw, lh = lantern_size
    import numpy as np
    scaled = lantern.resize((lw, lh), Image.LANCZOS)

    # ── Aura underlayer (L2, behind subject) ──────────────────────────────
    if cfg.add_aura:
        subj_mask_arr = np.zeros((canvas_size[1], canvas_size[0]), dtype=np.uint8)
        alpha_patch   = np.array(scaled.split()[3], dtype=np.uint8)
        ph, pw = min(lh, canvas_size[1] - max(0, ly)), min(lw, canvas_size[0] - max(0, lx))
        if ph > 0 and pw > 0:
            subj_mask_arr[max(0, ly):max(0, ly)+ph, max(0, lx):max(0, lx)+pw] = \
                alpha_patch[:ph, :pw]
        aura_layer = make_aura_frame(
            subj_mask_arr, canvas_size, t,
            preset          = cfg.aura_preset,
            core_color      = cfg.aura_core_color,
            corona_color    = cfg.aura_corona_color,
            core_radius     = cfg.aura_core_radius,
            corona_radius   = cfg.aura_corona_radius,
            pulse_speed     = cfg.aura_pulse_speed,
            pulse_depth     = cfg.aura_pulse_depth,
            electric_fringe = cfg.aura_electric_fringe,
        )
        frame = Image.alpha_composite(frame,
            _opacity(aura_layer, cfg.effect_opacity.get("aura", 1.0)))

    frame.paste(scaled, (lx, ly), scaled)

    if cfg.add_holo:
        subj_mask = Image.new("L", canvas_size, 0)
        subj_mask.paste(scaled.split()[3], (lx, ly))
        frame = Image.alpha_composite(frame,
            _opacity(make_holo_frame(canvas_size, t, subj_mask),
                     cfg.effect_opacity.get("holo_shimmer", 1.0)))

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
        frame = Image.alpha_composite(frame,
            _opacity(make_flash_layer(canvas_size, flash_alpha),
                     cfg.effect_opacity.get("flash", 1.0)))

    if cfg.tone_mode != "color":
        _tn_op = cfg.effect_opacity.get("tone_grade", 1.0)
        toned = apply_tone_mode(frame, cfg.tone_mode)
        if toned.mode != "RGBA":
            toned = toned.convert("RGBA")
        frame = Image.blend(frame, toned, _tn_op) if _tn_op < 1.0 else toned

    if cfg.add_chroma_aberration:
        _ca_op = cfg.effect_opacity.get("chroma_aberration", 1.0)
        chromed = apply_chromatic_aberration(frame.convert("RGB"), cfg.chroma_shift).convert("RGBA")
        frame = Image.blend(frame, chromed, _ca_op) if _ca_op < 1.0 else chromed

    if cfg.add_bloom:
        _bl_op = cfg.effect_opacity.get("bloom", 1.0)
        bloomed = apply_bloom(frame.convert("RGB"), cfg.bloom_radius, cfg.bloom_strength).convert("RGBA")
        frame = Image.blend(frame, bloomed, _bl_op) if _bl_op < 1.0 else bloomed

    if cfg.add_glitch:
        _gl_op = cfg.effect_opacity.get("glitch", 1.0)
        glitched = apply_glitch(frame, t=t, intensity=cfg.glitch_intensity,
                                band_count=cfg.glitch_band_count,
                                channel_split=cfg.glitch_channel_split).convert("RGBA")
        frame = Image.blend(frame, glitched, _gl_op) if _gl_op < 1.0 else glitched

    if cfg.add_denoise:
        _dn_op = cfg.effect_opacity.get("denoise", 1.0)
        denoised = apply_denoise(frame, strength=cfg.denoise_strength, mode=cfg.denoise_mode).convert("RGBA")
        frame = Image.blend(frame, denoised, _dn_op) if _dn_op < 1.0 else denoised

    if cfg.add_sharpen:
        _sh_op = cfg.effect_opacity.get("sharpen", 1.0)
        sharpened = apply_sharpen(
            frame, mode=cfg.sharpen_mode,
            amount=cfg.sharpen_amount, radius=cfg.sharpen_radius,
            threshold=cfg.sharpen_threshold,
        ).convert("RGBA")
        frame = Image.blend(frame, sharpened, _sh_op) if _sh_op < 1.0 else sharpened

    if vignette_layer is not None:
        frame = Image.alpha_composite(frame,
            _opacity(vignette_layer, cfg.effect_opacity.get("vignette", 1.0)))

    if scanlines_layer is not None:
        frame = Image.alpha_composite(frame,
            _opacity(scanlines_layer, cfg.effect_opacity.get("scanlines", 1.0)))

    rgb_out = frame.convert("RGB")
    if cfg.add_film_grain:
        _gr_op = cfg.effect_opacity.get("film_grain", 1.0)
        grainy = apply_film_grain(rgb_out, cfg.film_grain_intensity, seed=frame_idx)
        rgb_out = Image.blend(rgb_out, grainy, _gr_op) if _gr_op < 1.0 else grainy
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

    vignette_layer  = make_vignette(canvas_size, cfg.vignette_strength) if cfg.add_vignette  else None
    scanlines_layer = make_scanlines(canvas_size, cfg.scanlines_alpha)  if cfg.add_scanlines else None
    embers_origin = (lx + lw // 2, ly + lh // 4) if cfg.add_embers else None

    rgb_frames: list[Image.Image] = []
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
        rgb_frames.append(f)  # keep RGB for multi-format output

    # ── GIF ───────────────────────────────────────────────────────────────
    if cfg.output_gif:
        gif_frames = [f.convert("P", palette=Image.ADAPTIVE, colors=256) for f in rgb_frames]
        out = cfg.output_dir / f"brand_{size_name}.gif"
        gif_frames[0].save(
            out,
            save_all=True,
            append_images=gif_frames[1:],
            optimize=False,
            duration=cfg.frame_ms,
            loop=0,
        )
        kb = out.stat().st_size // 1024
        print(f"    → {out}  ({kb} KB)")

    # ── Animated WebP ─────────────────────────────────────────────────────
    if cfg.output_webp:
        out_webp = cfg.output_dir / f"brand_{size_name}.webp"
        rgb_frames[0].save(
            out_webp,
            format="WEBP",
            save_all=True,
            append_images=rgb_frames[1:],
            duration=cfg.frame_ms,
            loop=0,
            quality=85,
        )
        print(f"    → {out_webp}  ({out_webp.stat().st_size // 1024} KB)")

    # ── Animated PNG ──────────────────────────────────────────────────────
    if cfg.output_apng:
        out_apng = cfg.output_dir / f"brand_{size_name}.apng"
        rgb_frames[0].save(
            out_apng,
            format="PNG",
            save_all=True,
            append_images=rgb_frames[1:],
            default_image=False,
            duration=cfg.frame_ms,
            loop=0,
        )
        print(f"    → {out_apng}  ({out_apng.stat().st_size // 1024} KB)")

    # ── MP4 via imageio ───────────────────────────────────────────────────
    if cfg.output_mp4:
        try:
            import imageio
            import numpy as np
            out_mp4 = cfg.output_dir / f"brand_{size_name}.mp4"
            fps = max(1, round(1000 / cfg.frame_ms))
            writer = imageio.get_writer(str(out_mp4), fps=fps, codec="libx264",
                                        quality=8, macro_block_size=None)
            for f in rgb_frames:
                writer.append_data(np.array(f))
            writer.close()
            print(f"    → {out_mp4}  ({out_mp4.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"    ✗ MP4 skipped: {e} (ensure ffmpeg is on PATH)")

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
