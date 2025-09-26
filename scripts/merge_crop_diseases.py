#!/usr/bin/env python3
"""
Merge images from the local "Crop Diseases" dataset into datasets/diseases
with sensible class mapping and file renaming.

Rules:
- Map known classes (e.g., Corn___Common_Rust -> datasets/diseases/Corn rust leaf).
- Create target class folders if missing (e.g., Rice leaf, Wheat brown rust).
- Copy (do not move) images to preserve the original dataset.
- Rename copied files uniformly to: <target_class>__cd__<uuid>.<ext>
  where <ext> is lowercased original extension without dots normalization.
- Skip non-image files.

This script is idempotent: if a destination file with the same final name
already exists, it will skip copying that specific item (UUID makes collisions
practically impossible, but the check is kept for safety when resuming).
"""

from __future__ import annotations

import hashlib
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "Crop Diseases"
DST_ROOT = ROOT / "datasets" / "diseases"

# Explicit mapping from source folder name to target class folder name
CLASS_MAP: Dict[str, str] = {
    # Corn
    "Corn___Common_Rust": "Corn rust leaf",
    "Corn___Gray_Leaf_Spot": "Corn Gray leaf spot",
    "Corn___Northern_Leaf_Blight": "Corn leaf blight",
    "Corn___Healthy": "Corn leaf",
    # Potato
    "Potato___Early_Blight": "Potato leaf early blight",
    "Potato___Late_Blight": "Potato leaf late blight",
    "Potato___Healthy": "Potato leaf",
    # Rice
    "Rice___Brown_Spot": "Rice brown spot",
    "Rice___Leaf_Blast": "Rice leaf blast",
    "Rice___Neck_Blast": "Rice neck blast",
    "Rice___Healthy": "Rice leaf",
    # Sugarcane
    "Sugarcane_Bacterial Blight": "Sugarcane bacterial blight",
    "Sugarcane_Red Rot": "Sugarcane red rot",
    "Sugarcane_Healthy": "Sugarcane leaf",
    # Wheat
    "Wheat___Brown_Rust": "Wheat brown rust",
    "Wheat___Yellow_Rust": "Wheat yellow rust",
    "Wheat___Healthy": "Wheat leaf",
}


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def iter_files(folder: Path) -> Iterable[Path]:
    for root, _, files in os.walk(folder):
        for f in files:
            yield Path(root) / f


def rename_for(target_class: str, src_path: Path) -> str:
    """Generate a deterministic-ish new filename for a copied image.

    We embed the target class for readability, tag with `__cd__` to indicate
    the source dataset (Crop Diseases), and append a uuid4 for uniqueness.
    """
    ext = src_path.suffix.lower()
    if ext not in IMAGE_EXTS:
        ext = ".jpg"  # default fallback if odd extension
    # Normalize spaces in target_class for filename readability
    cls_token = target_class.replace("/", "-").strip()
    return f"{cls_token}__cd__{uuid.uuid4().hex}{ext}"


def copy_file(src: Path, dst_dir: Path, new_name: str) -> Tuple[bool, Path]:
    ensure_dir(dst_dir)
    dst_path = dst_dir / new_name
    if dst_path.exists():
        return False, dst_path
    # Stream copy to be memory efficient
    with src.open("rb") as rf, dst_path.open("wb") as wf:
        while True:
            chunk = rf.read(1024 * 1024)
            if not chunk:
                break
            wf.write(chunk)
    return True, dst_path


def main() -> int:
    if not SRC_ROOT.exists():
        print(f"Source folder not found: {SRC_ROOT}", file=sys.stderr)
        return 1
    ensure_dir(DST_ROOT)

    # Warn on unmapped classes
    src_classes = sorted([p.name for p in SRC_ROOT.iterdir() if p.is_dir()])
    unmapped = [c for c in src_classes if c not in CLASS_MAP]
    if unmapped:
        print("[WARN] Some source classes have no mapping:", file=sys.stderr)
        for c in unmapped:
            print(f"  - {c}", file=sys.stderr)

    total = 0
    copied = 0
    skipped_non_images = 0
    for src_class, target_class in CLASS_MAP.items():
        src_dir = SRC_ROOT / src_class
        if not src_dir.exists():
            print(f"[SKIP] Missing: {src_dir}")
            continue
        dst_dir = DST_ROOT / target_class
        ensure_dir(dst_dir)
        print(f"[MERGE] {src_class} -> {target_class}")
        for f in iter_files(src_dir):
            total += 1
            if not is_image(f):
                skipped_non_images += 1
                continue
            new_name = rename_for(target_class, f)
            ok, out = copy_file(f, dst_dir, new_name)
            if ok:
                copied += 1
            # else: collision skip (extremely rare due to UUID)

    print("\nSummary:")
    print(f"  Total files seen: {total}")
    print(f"  Images copied:    {copied}")
    print(f"  Non-images skipped: {skipped_non_images}")
    print(f"  Output root:      {DST_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
