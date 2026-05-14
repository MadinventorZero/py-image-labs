#!/usr/bin/env python3
"""SHA-256 integrity manifest for Brand Image Generator.

Usage:
    python3 integrity.py --generate   # write .manifest/integrity.json
    python3 integrity.py --check      # verify files match manifest
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT     = Path(__file__).parent
MANIFEST = ROOT / ".manifest" / "integrity.json"

INCLUDE = [
    "app.py",
    "run.py",
    "integrity.py",
    "requirements.txt",
    "ui/index.html",
    "ui/css/main.css",
    "ui/css/wizard.css",
    "ui/js/api.js",
    "ui/js/wizard.js",
    "ui/views/landing.html",
    "ui/views/render.html",
    "ui/views/01-input.html",
    "ui/views/02-process.html",
    "ui/views/03-output.html",
    "ui/views/04-sizes.html",
    "ui/views/05-layers.html",
    "ui/views/06-tagline.html",
    "ui/views/07-confirm.html",
    "engine/__init__.py",
    "engine/models.py",
    "engine/image_proc.py",
    "engine/pipeline.py",
    "engine/effects/__init__.py",
    "engine/effects/smoke.py",
    "engine/effects/lightning.py",
    "engine/effects/particles.py",
    "engine/effects/text_render.py",
    "engine/effects/post.py",
    "engine/effects/overlay.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def generate() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for rel in INCLUDE:
        p = ROOT / rel
        if p.exists():
            manifest[rel] = sha256(p)
        else:
            print(f"  [warn] missing: {rel}")
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written: {MANIFEST}  ({len(manifest)} files)")


def check() -> None:
    if not MANIFEST.exists():
        print("No manifest found. Run --generate first.")
        sys.exit(1)
    manifest = json.loads(MANIFEST.read_text())
    failures = []
    for rel, expected in manifest.items():
        p = ROOT / rel
        if not p.exists():
            failures.append(f"  MISSING  {rel}")
        elif sha256(p) != expected:
            failures.append(f"  CHANGED  {rel}")
    if failures:
        print("Integrity check FAILED:")
        for f in failures:
            print(f)
        sys.exit(1)
    print(f"Integrity check passed ({len(manifest)} files OK).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true")
    group.add_argument("--check",    action="store_true")
    args = parser.parse_args()
    if args.generate:
        generate()
    else:
        check()
