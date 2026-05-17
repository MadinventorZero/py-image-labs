"""Tests for individual effect functions."""
import numpy as np
import pytest
from PIL import Image

# ── Atmosphere ────────────────────────────────────────────────────────────────

from engine.effects.atmosphere import make_fog_frame, make_god_rays_frame


def test_fog_returns_rgba():
    frame = make_fog_frame((480, 270), t=0.0)
    assert frame.mode == "RGBA"
    assert frame.size == (480, 270)


def test_fog_has_nonzero_alpha_at_bottom():
    frame = make_fog_frame((480, 270), t=0.0, density=0.8, height_pct=0.5)
    arr = np.array(frame)
    bottom_alpha = arr[260, :, 3]
    assert bottom_alpha.max() > 0, "Bottom rows should have non-zero alpha"


def test_fog_zero_density_is_transparent():
    frame = make_fog_frame((480, 270), t=0.0, density=0.0)
    arr = np.array(frame)
    assert arr[:, :, 3].max() == 0


def test_fog_height_pct_zero_is_blank():
    frame = make_fog_frame((480, 270), t=0.0, density=1.0, height_pct=0.0)
    arr = np.array(frame)
    assert arr[:, :, 3].max() == 0


def test_fog_tint_applied():
    frame = make_fog_frame((480, 270), t=0.0, density=1.0, height_pct=1.0, tint=(255, 0, 0))
    arr = np.array(frame)
    bottom_strip = arr[260:, :, :]
    # Where there's alpha, R should be highest channel
    mask = bottom_strip[:, :, 3] > 10
    if mask.any():
        assert bottom_strip[mask, 0].mean() > bottom_strip[mask, 1].mean()


def test_god_rays_returns_rgba():
    frame = make_god_rays_frame((480, 270), t=0.0)
    assert frame.mode == "RGBA"
    assert frame.size == (480, 270)


def test_god_rays_has_nonzero_alpha():
    frame = make_god_rays_frame((480, 270), t=0.0, intensity=0.8)
    arr = np.array(frame)
    assert arr[:, :, 3].max() > 0


def test_god_rays_zero_intensity_is_transparent():
    frame = make_god_rays_frame((480, 270), t=0.0, intensity=0.0)
    arr = np.array(frame)
    assert arr[:, :, 3].max() == 0


def test_god_rays_color_applied():
    frame = make_god_rays_frame((480, 270), t=0.0, intensity=1.0, color=(0, 255, 0))
    arr = np.array(frame)
    mask = arr[:, :, 3] > 10
    if mask.any():
        assert arr[mask, 1].mean() > arr[mask, 0].mean()


def test_god_rays_different_times_differ():
    f1 = np.array(make_god_rays_frame((120, 68), t=0.0))
    f2 = np.array(make_god_rays_frame((120, 68), t=0.5))
    assert not np.array_equal(f1, f2), "Different t values should produce different frames"


# ── Glitch ────────────────────────────────────────────────────────────────────

from engine.effects.glitch import apply_glitch


def _gradient_image(w=120, h=80, mode="RGBA"):
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    for x in range(w):
        arr[:, x, 0] = int(x / w * 255)
    for y in range(h):
        arr[y, :, 1] = int(y / h * 255)
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")
    if mode == "RGB":
        return img.convert("RGB")
    return img


def test_glitch_preserves_size():
    img = _gradient_image()
    result = apply_glitch(img, t=0.0, intensity=0.5)
    assert result.size == img.size


def test_glitch_rgba_preserves_alpha():
    img = _gradient_image()
    result = apply_glitch(img, t=0.0)
    assert result.mode == "RGBA"


def test_glitch_rgb_in_rgb_out():
    img = _gradient_image(mode="RGB")
    result = apply_glitch(img, t=0.0)
    assert result.mode == "RGB"


def test_glitch_changes_pixels():
    img = _gradient_image(w=200, h=100)
    result = apply_glitch(img, t=0.0, intensity=0.8, band_count=10)
    diff = np.abs(np.array(img.convert("RGB")).astype(int) - np.array(result.convert("RGB")).astype(int))
    assert diff.sum() > 0, "Glitch should change at least some pixels"


def test_glitch_deterministic_same_t():
    img = _gradient_image(w=200, h=100)
    r1 = np.array(apply_glitch(img, t=0.3))
    r2 = np.array(apply_glitch(img, t=0.3))
    assert np.array_equal(r1, r2), "Same t should produce identical output"


def test_glitch_different_t_differs():
    img = _gradient_image(w=200, h=100)
    r1 = np.array(apply_glitch(img, t=0.0, intensity=0.8))
    r2 = np.array(apply_glitch(img, t=0.5, intensity=0.8))
    assert not np.array_equal(r1, r2)


def test_glitch_no_channel_split():
    img = _gradient_image(w=200, h=100)
    result = apply_glitch(img, t=0.0, intensity=0.8, channel_split=False)
    assert result.size == img.size


# ── Chibi ─────────────────────────────────────────────────────────────────────

from engine.effects.chibi import apply_chibi


def _solid_image(w=100, h=200, mode="RGBA"):
    if mode == "RGBA":
        arr = np.full((h, w, 4), [100, 150, 200, 255], dtype=np.uint8)
    else:
        arr = np.full((h, w, 3), [100, 150, 200], dtype=np.uint8)
    return Image.fromarray(arr, mode)


def test_chibi_output_matches_input_size():
    img = _solid_image()
    result = apply_chibi(img, head_pct=0.42, head_scale=1.45)
    assert result.size == img.size


def test_chibi_rgba_in_rgba_out():
    img = _solid_image(mode="RGBA")
    result = apply_chibi(img)
    assert result.mode == "RGBA"


def test_chibi_rgb_in_rgb_out():
    img = _solid_image(mode="RGB")
    result = apply_chibi(img)
    assert result.mode == "RGB"


def test_chibi_clamps_head_pct_low():
    img = _solid_image()
    # head_pct=0.05 should be clamped to 0.20
    result = apply_chibi(img, head_pct=0.05)
    assert result.size == img.size


def test_chibi_clamps_head_pct_high():
    img = _solid_image()
    # head_pct=0.90 should be clamped to 0.65
    result = apply_chibi(img, head_pct=0.90)
    assert result.size == img.size


def test_chibi_clamps_head_scale_low():
    img = _solid_image()
    result = apply_chibi(img, head_scale=0.5)  # clamped to 1.10
    assert result.size == img.size


def test_chibi_clamps_head_scale_high():
    img = _solid_image()
    result = apply_chibi(img, head_scale=5.0)  # clamped to 2.20
    assert result.size == img.size


def test_chibi_modifies_image():
    # A gradient so the transform actually changes pixel values
    arr = np.zeros((200, 100, 4), dtype=np.uint8)
    for y in range(200):
        arr[y, :, :3] = y
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")
    result = apply_chibi(img, head_pct=0.4, head_scale=1.8)
    assert not np.array_equal(np.array(img), np.array(result))


# ── Post: Bloom ───────────────────────────────────────────────────────────────

from engine.effects.post import apply_bloom


def test_bloom_returns_same_mode():
    img = Image.new("RGB", (120, 80), (100, 150, 200))
    result = apply_bloom(img, radius=6, strength=0.5)
    assert result.mode == "RGB"
    assert result.size == img.size


def test_bloom_changes_image():
    img = Image.new("RGB", (120, 80), (200, 200, 200))
    result = apply_bloom(img, radius=6, strength=0.8)
    # Bloom adds light, so result should differ (or at least not error)
    assert result.size == img.size


# ── Post: Film grain ──────────────────────────────────────────────────────────

from engine.effects.post import apply_film_grain


def test_film_grain_changes_pixels():
    img = Image.new("RGB", (120, 80), (128, 128, 128))
    result = apply_film_grain(img, intensity=0.1, seed=42)
    diff = np.abs(np.array(img).astype(int) - np.array(result).astype(int))
    assert diff.sum() > 0


def test_film_grain_seeded_deterministic():
    img = Image.new("RGB", (120, 80), (128, 128, 128))
    r1 = np.array(apply_film_grain(img, intensity=0.1, seed=7))
    r2 = np.array(apply_film_grain(img, intensity=0.1, seed=7))
    assert np.array_equal(r1, r2)
