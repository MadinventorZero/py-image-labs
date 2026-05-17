"""GPU/compute backend detection."""
from __future__ import annotations


def get_best_backend() -> dict:
    """Return the best available compute backend as a serialisable dict."""
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "backend": "cuda",
                "name":    props.name,
                "vram_gb": props.total_memory // (1024 ** 3),
            }
        if torch.backends.mps.is_available():
            return {"backend": "mps", "name": "Apple Silicon MPS", "vram_gb": None}
    except ImportError:
        pass

    try:
        import onnxruntime as ort
        if "CoreMLExecutionProvider" in ort.get_available_providers():
            return {"backend": "coreml", "name": "Apple CoreML", "vram_gb": None}
    except ImportError:
        pass

    return {"backend": "cpu", "name": "CPU", "vram_gb": None}


def onnx_providers() -> list[str]:
    """Best ONNX execution providers for this machine, in priority order."""
    try:
        import onnxruntime as ort
        avail = ort.get_available_providers()
        for ep in ("CUDAExecutionProvider", "CoreMLExecutionProvider"):
            if ep in avail:
                return [ep, "CPUExecutionProvider"]
    except ImportError:
        pass
    return ["CPUExecutionProvider"]
