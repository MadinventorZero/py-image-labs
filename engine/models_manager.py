"""ONNX model download, caching, and session management.

Models are stored in <project_root>/.models/.
Downloads use pooch (already installed via rembg) for checksum-verified retrieval.

To add a model: place an entry in MODEL_REGISTRY with a direct HTTPS URL to an
.onnx file.  Run `python -m engine.models_manager download <model_id>` from the
project root to pre-fetch.  Effects fall back gracefully when the model file is
absent — they either warn and return the input unchanged, or use a CPU fallback.

Verified model sources
──────────────────────
  animegan2_hayao / paprika / face_paint
    Export any AnimaGANv2 checkpoint to ONNX and place the file in .models/:
      pip install animegan2-pytorch  # or clone TachibanaYoshino/AnimeGANv2
      python -c "import torch, animegan2; m=animegan2.Generator(); \\
                 m.load_state_dict(torch.load('hayao.pt')); \\
                 torch.onnx.export(m, torch.zeros(1,3,256,256), '.models/animegan2_hayao.onnx',
                                   input_names=['x'], output_names=['y'],
                                   dynamic_axes={'x':{2:'h',3:'w'},'y':{2:'h',3:'w'}})"
    Or download pre-exported ONNX from:
      https://github.com/TachibanaYoshino/AnimeGANv2 (PyTorch → export script)
      https://huggingface.co/bryandlee/animegan2-pytorch

  realesrgan_x4 / realesrgan_x4_anime
    https://github.com/xinntao/Real-ESRGAN/releases  (look for .onnx assets)
    Or: pip install realesrgan && python -c "from realesrgan import RealESRGANer; ..."

  white_box_cartoon
    https://github.com/SystemErrorWang/White-box-Cartoonization
    Convert saved_model/ to ONNX via tf2onnx.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import onnxruntime as ort

# ── Paths ─────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parents[1]
MODELS_DIR    = _PROJECT_ROOT / ".models"
MODELS_DIR.mkdir(exist_ok=True)

# ── Registry ──────────────────────────────────────────────────────────────────
# url=None means "user must supply the file manually" (see module docstring).
# input_layout: "NHWC" = [1,H,W,3],  "NCHW" = [1,3,H,W]
# input_range:  "tanh" = [-1,1],     "unit" = [0,1]
MODEL_REGISTRY: dict[str, dict] = {
    "animegan2_hayao": {
        "url":          None,   # see module docstring for export instructions
        "checksum":     None,
        "filename":     "animegan2_hayao.onnx",
        "description":  "AnimeGAN v2 — Hayao landscape style",
        "input_layout": "NHWC",
        "input_range":  "tanh",
        "size_mb":      8.6,
    },
    "animegan2_paprika": {
        "url":          None,
        "checksum":     None,
        "filename":     "animegan2_paprika.onnx",
        "description":  "AnimeGAN v2 — Paprika cinematic style",
        "input_layout": "NHWC",
        "input_range":  "tanh",
        "size_mb":      8.6,
    },
    "animegan2_face_paint": {
        "url":          None,
        "checksum":     None,
        "filename":     "animegan2_face_paint.onnx",
        "description":  "AnimeGAN v2 — Face Paint portrait style",
        "input_layout": "NHWC",
        "input_range":  "tanh",
        "size_mb":      8.6,
    },
    "white_box_cartoon": {
        "url":          None,
        "checksum":     None,
        "filename":     "white_box_cartoon.onnx",
        "description":  "White-Box Cartoonizer (WBC)",
        "input_layout": "NHWC",
        "input_range":  "tanh",
        "size_mb":      8.0,
    },
    "realesrgan_x4": {
        "url":          None,
        "checksum":     None,
        "filename":     "realesrgan_x4.onnx",
        "description":  "Real-ESRGAN 4× upscale (general)",
        "input_layout": "NCHW",
        "input_range":  "unit",
        "scale":        4,
        "size_mb":      67.0,
    },
    "realesrgan_x4_anime": {
        "url":          None,
        "checksum":     None,
        "filename":     "realesrgan_x4_anime.onnx",
        "description":  "Real-ESRGAN 4× upscale (anime-optimised)",
        "input_layout": "NCHW",
        "input_range":  "unit",
        "scale":        4,
        "size_mb":      67.0,
    },
}


# ── Exceptions ────────────────────────────────────────────────────────────────
class ModelNotAvailableError(RuntimeError):
    def __init__(self, model_id: str):
        path = MODELS_DIR / MODEL_REGISTRY[model_id]["filename"]
        super().__init__(
            f"Neural model '{model_id}' not found at {path}.\n"
            "See engine/models_manager.py for download instructions, or run:\n"
            f"  python -m engine.models_manager download {model_id}"
        )
        self.model_id = model_id


# ── Session cache ─────────────────────────────────────────────────────────────
_session_cache: dict[str, ort.InferenceSession] = {}


def _providers() -> list[str]:
    avail = ort.get_available_providers()
    for ep in ("CUDAExecutionProvider", "CoreMLExecutionProvider"):
        if ep in avail:
            return [ep, "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def model_path(model_id: str) -> Optional[Path]:
    """Return path to the model file, or None if not downloaded."""
    if model_id not in MODEL_REGISTRY:
        return None
    p = MODELS_DIR / MODEL_REGISTRY[model_id]["filename"]
    return p if p.exists() else None


def model_available(model_id: str) -> bool:
    return model_path(model_id) is not None


def get_ort_session(model_id: str) -> ort.InferenceSession:
    """Return a cached InferenceSession, raising ModelNotAvailableError if absent."""
    if model_id not in _session_cache:
        p = model_path(model_id)
        if p is None:
            raise ModelNotAvailableError(model_id)
        _session_cache[model_id] = ort.InferenceSession(str(p), providers=_providers())
    return _session_cache[model_id]


def download_model(model_id: str, force: bool = False) -> Path:
    """Download a model via pooch. Raises ValueError if url is None."""
    if model_id not in MODEL_REGISTRY:
        raise KeyError(f"Unknown model: {model_id!r}")
    spec = MODEL_REGISTRY[model_id]
    if not spec.get("url"):
        raise ValueError(
            f"No automatic download URL for '{model_id}'.\n"
            "See engine/models_manager.py for manual export/download instructions."
        )
    import pooch
    dest = MODELS_DIR / spec["filename"]
    if dest.exists() and not force:
        print(f"  {model_id}: already present at {dest}")
        return dest
    print(f"  Downloading {model_id} ({spec.get('size_mb', '?')} MB)...")
    pooch.retrieve(
        url      = spec["url"],
        known_hash = spec.get("checksum"),
        fname    = spec["filename"],
        path     = str(MODELS_DIR),
        progressbar = True,
    )
    return dest


def list_models() -> dict[str, bool]:
    """Return {model_id: is_downloaded} for all registered models."""
    return {mid: model_available(mid) for mid in MODEL_REGISTRY}


# ── CLI helper ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Neural model manager")
    sub = parser.add_subparsers(dest="cmd")

    dl = sub.add_parser("download", help="Download a model")
    dl.add_argument("model_id", choices=list(MODEL_REGISTRY))
    dl.add_argument("--force", action="store_true")

    sub.add_parser("list", help="Show all models and download status")

    args = parser.parse_args()
    if args.cmd == "list":
        for mid, avail in list_models().items():
            spec = MODEL_REGISTRY[mid]
            status = "✓ downloaded" if avail else ("⚠ no URL — manual" if not spec.get("url") else "✗ not downloaded")
            print(f"  {mid:<28} {status:<22}  {spec['description']}")
    elif args.cmd == "download":
        try:
            download_model(args.model_id, force=args.force)
            print(f"  Done: {model_path(args.model_id)}")
        except ValueError as e:
            print(f"  Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
