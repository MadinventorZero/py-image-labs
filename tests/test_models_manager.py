"""Tests for engine.models_manager — ONNX model lifecycle."""
import pytest
from engine.models_manager import (
    MODEL_REGISTRY,
    ModelNotAvailableError,
    download_model,
    get_ort_session,
    list_models,
    model_available,
    model_path,
)


# ── Registry completeness ─────────────────────────────────────────────────────

def test_all_expected_models_registered():
    expected = {
        "animegan2_hayao",
        "animegan2_paprika",
        "animegan2_face_paint",
        "white_box_cartoon",
        "realesrgan_x4",
        "realesrgan_x4_anime",
    }
    assert expected.issubset(MODEL_REGISTRY.keys())


def test_registry_entries_have_required_fields():
    for mid, spec in MODEL_REGISTRY.items():
        assert "filename" in spec,       f"{mid} missing 'filename'"
        assert "input_layout" in spec,   f"{mid} missing 'input_layout'"
        assert "input_range" in spec,    f"{mid} missing 'input_range'"
        assert spec["input_layout"] in ("NHWC", "NCHW"), f"{mid} bad input_layout"
        assert spec["input_range"] in ("tanh", "unit"),   f"{mid} bad input_range"


# ── model_path / model_available ──────────────────────────────────────────────

def test_model_path_returns_none_when_not_downloaded():
    # No .onnx files exist in the test env
    for mid in MODEL_REGISTRY:
        assert model_path(mid) is None, f"{mid} should not be present"


def test_model_available_false_when_not_downloaded():
    for mid in MODEL_REGISTRY:
        assert model_available(mid) is False


def test_model_path_unknown_id_returns_none():
    assert model_path("does_not_exist") is None


# ── list_models ───────────────────────────────────────────────────────────────

def test_list_models_returns_dict():
    result = list_models()
    assert isinstance(result, dict)


def test_list_models_covers_all_registry_keys():
    result = list_models()
    assert set(result.keys()) == set(MODEL_REGISTRY.keys())


def test_list_models_all_false_in_test_env():
    result = list_models()
    for mid, available in result.items():
        assert available is False, f"{mid} should be unavailable"


# ── get_ort_session ───────────────────────────────────────────────────────────

def test_get_ort_session_raises_model_not_available():
    for mid in MODEL_REGISTRY:
        with pytest.raises(ModelNotAvailableError) as exc_info:
            get_ort_session(mid)
        assert mid in str(exc_info.value)


def test_model_not_available_error_mentions_models_dir():
    with pytest.raises(ModelNotAvailableError) as exc_info:
        get_ort_session("animegan2_hayao")
    assert ".models" in str(exc_info.value)


def test_model_not_available_error_has_model_id_attr():
    with pytest.raises(ModelNotAvailableError) as exc_info:
        get_ort_session("animegan2_hayao")
    assert exc_info.value.model_id == "animegan2_hayao"


# ── download_model ────────────────────────────────────────────────────────────

def test_download_model_raises_value_error_when_url_none():
    # All registered models have url=None — manual export only
    for mid in MODEL_REGISTRY:
        with pytest.raises(ValueError) as exc_info:
            download_model(mid)
        assert mid in str(exc_info.value) or "download" in str(exc_info.value).lower()


def test_download_model_raises_key_error_unknown():
    with pytest.raises(KeyError):
        download_model("completely_unknown_model_xyz")


# ── ONNX Runtime session cache isolation ─────────────────────────────────────

def test_get_ort_session_consistent_error_for_same_id():
    """Two calls for same unavailable model both raise ModelNotAvailableError."""
    with pytest.raises(ModelNotAvailableError):
        get_ort_session("animegan2_paprika")
    with pytest.raises(ModelNotAvailableError):
        get_ort_session("animegan2_paprika")
