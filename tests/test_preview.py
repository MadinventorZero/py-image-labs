"""Tests for engine.preview — low-res preview renderer."""
import pytest
from engine.preview import render_preview, clear_cache


DATA_URI_PREFIX = "data:image/jpeg;base64,"


def test_no_source_returns_data_uri():
    result = render_preview({"inputPath": "", "effectStack": [], "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_nonexistent_source_returns_data_uri():
    result = render_preview({"inputPath": "/nonexistent/path/photo.jpg", "effectStack": [], "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_empty_stack_returns_data_uri():
    result = render_preview({"inputPath": "", "effectStack": [], "imgProc": {"remove_bg": False}})
    assert result.startswith(DATA_URI_PREFIX)


def test_fog_in_stack_no_crash():
    stack = [{"id": "fog", "enabled": True, "opacity": 1.0, "params": {"density": 0.4, "height_pct": 50}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_god_rays_in_stack_no_crash():
    stack = [{"id": "god_rays", "enabled": True, "opacity": 1.0, "params": {}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_glitch_in_stack_no_crash():
    stack = [{"id": "glitch", "enabled": True, "opacity": 1.0,
              "params": {"intensity": 0.5, "band_count": 6, "channel_split": True}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_vignette_in_stack_no_crash():
    stack = [{"id": "vignette", "enabled": True, "opacity": 1.0, "params": {"strength": 0.72}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_bloom_in_stack_no_crash():
    stack = [{"id": "bloom", "enabled": True, "opacity": 1.0, "params": {"radius": 12, "strength": 0.4}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_scanlines_in_stack_no_crash():
    stack = [{"id": "scanlines", "enabled": True, "opacity": 1.0, "params": {"alpha": 20}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_disabled_effect_ignored():
    stack = [{"id": "glitch", "enabled": False, "opacity": 1.0, "params": {"intensity": 1.0}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_opacity_zero_effect_skipped():
    stack = [{"id": "fog", "enabled": True, "opacity": 0.0, "params": {"density": 1.0, "height_pct": 100}}]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_preview_size_parameter():
    result = render_preview({"inputPath": "", "effectStack": [], "previewSize": 240, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_result_is_non_empty_base64():
    result = render_preview({"inputPath": "", "effectStack": [], "imgProc": {}})
    b64_part = result[len(DATA_URI_PREFIX):]
    assert len(b64_part) > 100, "Base64 payload should be substantial"


def test_multiple_effects_stack_no_crash():
    stack = [
        {"id": "fog",     "enabled": True, "opacity": 0.8, "params": {"density": 0.4, "height_pct": 40}},
        {"id": "vignette","enabled": True, "opacity": 1.0, "params": {"strength": 0.6}},
        {"id": "bloom",   "enabled": True, "opacity": 0.9, "params": {"radius": 10, "strength": 0.3}},
        {"id": "glitch",  "enabled": True, "opacity": 0.5, "params": {"intensity": 0.3, "band_count": 4}},
    ]
    result = render_preview({"inputPath": "", "effectStack": stack, "imgProc": {}})
    assert result.startswith(DATA_URI_PREFIX)


def test_clear_cache_does_not_raise():
    clear_cache()  # should not raise even when empty
