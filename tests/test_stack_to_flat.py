"""Tests for app._stack_to_flat — effectStack JSON → flat config dict."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app import _stack_to_flat


def item(eid, enabled=True, params=None, opacity=1.0):
    return {"id": eid, "enabled": enabled, "opacity": opacity, "params": params or {}}


# ── Smoke / Rain / Embers ─────────────────────────────────────────────────────

def test_smoke_enabled():
    out = _stack_to_flat([item("smoke", params={"density": 0.5})])
    assert out["add_smoke"] is True
    assert out["smoke_density"] == pytest.approx(0.5)


def test_smoke_disabled():
    out = _stack_to_flat([item("smoke", enabled=False)])
    assert out["add_smoke"] is False


def test_rain_density_to_drops():
    out = _stack_to_flat([item("rain", params={"density": 0.6, "angle": 15.0})])
    assert out["add_rain"] is True
    assert out["rain_n_drops"] == max(10, int(0.6 * 460))
    assert out["rain_angle"] == pytest.approx(15.0)


def test_rain_density_low_clamp():
    out = _stack_to_flat([item("rain", params={"density": 0.0})])
    assert out["rain_n_drops"] == 10  # clamped by max(10, ...)


def test_embers_count_param():
    out = _stack_to_flat([item("embers", params={"count": 120})])
    assert out["add_embers"] is True
    assert out["embers_count"] == 120


def test_embers_default_count():
    out = _stack_to_flat([item("embers")])
    assert out["embers_count"] == 60


# ── Fog ───────────────────────────────────────────────────────────────────────

def test_fog_params_wired():
    out = _stack_to_flat([item("fog", params={"density": 0.7, "height_pct": 60})])
    assert out["add_fog"] is True
    assert out["fog_density"] == pytest.approx(0.7)
    assert out["fog_height_pct"] == pytest.approx(0.60)  # divided by 100


def test_fog_tint_conversion():
    out = _stack_to_flat([item("fog", params={"tint": [200, 210, 220]})])
    assert out["fog_tint"] == (200, 210, 220)


def test_fog_disabled():
    out = _stack_to_flat([item("fog", enabled=False)])
    assert out["add_fog"] is False


# ── God Rays ──────────────────────────────────────────────────────────────────

def test_god_rays_origin_percent_conversion():
    out = _stack_to_flat([item("god_rays", params={"origin_x": 75, "origin_y": 20})])
    assert out["add_god_rays"] is True
    assert out["god_rays_origin_x"] == pytest.approx(0.75)
    assert out["god_rays_origin_y"] == pytest.approx(0.20)


def test_god_rays_color():
    out = _stack_to_flat([item("god_rays", params={"color": [255, 200, 100]})])
    assert out["god_rays_color"] == (255, 200, 100)


def test_god_rays_defaults():
    out = _stack_to_flat([item("god_rays")])
    assert out["god_rays_intensity"] == pytest.approx(0.5)
    assert out["god_rays_origin_x"] == pytest.approx(0.50)
    assert out["god_rays_origin_y"] == pytest.approx(0.15)


# ── Glitch ────────────────────────────────────────────────────────────────────

def test_glitch_params():
    out = _stack_to_flat([item("glitch", params={"intensity": 0.8, "band_count": 10, "channel_split": False})])
    assert out["add_glitch"] is True
    assert out["glitch_intensity"] == pytest.approx(0.8)
    assert out["glitch_band_count"] == 10
    assert out["glitch_channel_split"] is False


def test_glitch_disabled():
    out = _stack_to_flat([item("glitch", enabled=False)])
    assert out["add_glitch"] is False


# ── Opacity map ───────────────────────────────────────────────────────────────

def test_opacity_map_populated():
    out = _stack_to_flat([
        item("fog",   opacity=0.5),
        item("bloom", opacity=0.75),
    ])
    op = out["effect_opacity"]
    assert op["fog"] == pytest.approx(0.5)
    assert op["bloom"] == pytest.approx(0.75)


def test_opacity_default_1():
    out = _stack_to_flat([item("rain")])
    assert out["effect_opacity"]["rain"] == pytest.approx(1.0)


# ── Neural FX ─────────────────────────────────────────────────────────────────

def test_anime_style_mapped():
    for eid, expected in [
        ("anime_hayao", "hayao"),
        ("anime_paprika", "paprika"),
        ("anime_face_paint", "face_paint"),
        ("anime_wbc", "wbc"),
    ]:
        out = _stack_to_flat([item(eid)])
        assert out["anime_style"] == expected, f"{eid} → {expected}"


def test_anime_disabled_gives_none():
    out = _stack_to_flat([item("anime_hayao", enabled=False)])
    assert out["anime_style"] == "none"


def test_chibi_params():
    out = _stack_to_flat([item("chibi", params={"head_pct": 50, "head_scale": 1.6})])
    assert out["add_chibi"] is True
    assert out["chibi_head_pct"] == pytest.approx(0.50)
    assert out["chibi_head_scale"] == pytest.approx(1.6)


def test_upscale_mode():
    out = _stack_to_flat([item("upscale", params={"mode": "x4_anime"})])
    assert out["upscale_mode"] == "x4_anime"


def test_upscale_disabled():
    out = _stack_to_flat([item("upscale", enabled=False)])
    assert out["upscale_mode"] == "none"


# ── Stylize sigma params ──────────────────────────────────────────────────────

def test_cartoon_sigma_params():
    out = _stack_to_flat([item("cartoon_cv2", params={"sigma_s": 80.0, "sigma_r": 0.3})])
    assert out["stylize_mode"] == "cartoon"
    assert out["stylize_sigma_s"] == pytest.approx(80.0)
    assert out["stylize_sigma_r"] == pytest.approx(0.3)


def test_watercolor_disabled_mode():
    out = _stack_to_flat([item("watercolor", enabled=False)])
    assert out["stylize_mode"] == "none"


def test_sketch_shade_factor():
    out = _stack_to_flat([item("sketch", params={"shade_factor": 0.08})])
    assert out["stylize_shade_factor"] == pytest.approx(0.08)


# ── Vignette / Bloom / Chroma ─────────────────────────────────────────────────

def test_vignette_strength():
    out = _stack_to_flat([item("vignette", params={"strength": 0.9})])
    assert out["add_vignette"] is True
    assert out["vignette_strength"] == pytest.approx(0.9)


def test_bloom_params():
    out = _stack_to_flat([item("bloom", params={"radius": 16, "strength": 0.55})])
    assert out["add_bloom"] is True
    assert out["bloom_radius"] == 16
    assert out["bloom_strength"] == pytest.approx(0.55)


def test_chroma_aberration_shift():
    out = _stack_to_flat([item("chroma_aberration", params={"shift": 8})])
    assert out["add_chroma_aberration"] is True
    assert out["chroma_shift"] == 8


# ── Aura ──────────────────────────────────────────────────────────────────────

def test_aura_preset_and_colors():
    out = _stack_to_flat([item("aura", params={
        "preset": "fire",
        "core_color": [255, 100, 0],
        "corona_color": [255, 50, 0],
    })])
    assert out["add_aura"] is True
    assert out["aura_preset"] == "fire"
    assert out["aura_core_color"] == (255, 100, 0)
    assert out["aura_corona_color"] == (255, 50, 0)


# ── Lightning ─────────────────────────────────────────────────────────────────

def test_lightning_enabled():
    out = _stack_to_flat([item("lightning", params={"mode": "branched", "n_bolts": 3})])
    assert out["lightning_mode"] == "branched"
    assert out["n_bolts"] == 3


def test_lightning_disabled():
    out = _stack_to_flat([item("lightning", enabled=False)])
    assert out["lightning_mode"] == "off"


# ── Tagline ───────────────────────────────────────────────────────────────────

def test_tagline_enabled():
    out = _stack_to_flat([item("tagline")])
    assert out["add_text"] is True


def test_tagline_disabled():
    out = _stack_to_flat([item("tagline", enabled=False)])
    assert out["add_text"] is False


# ── Multiple effects coexist ──────────────────────────────────────────────────

def test_multiple_effects():
    stack = [
        item("fog",    params={"density": 0.3}),
        item("bloom",  params={"radius": 10}),
        item("glitch", params={"intensity": 0.6}),
    ]
    out = _stack_to_flat(stack)
    assert out["add_fog"] is True
    assert out["add_bloom"] is True
    assert out["add_glitch"] is True
    assert out["fog_density"] == pytest.approx(0.3)
    assert out["bloom_radius"] == 10
    assert out["glitch_intensity"] == pytest.approx(0.6)


# ── Output format flags (these live in payload, but smoke-test _stack_to_flat key scope)

def test_unknown_eid_ignored():
    """Unknown effect IDs should not raise — just get skipped."""
    out = _stack_to_flat([item("unknown_future_effect")])
    assert isinstance(out, dict)
    assert "effect_opacity" in out
