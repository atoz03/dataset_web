#!/usr/bin/env python3
"""
Import LLM-verified images from web_scraper/scraped_images into datasets/*.

Rules:
- Only move images that have a sibling .json (accepted by LLM).
- Map scraped class names via mappings/consolidated_mapping.json when possible.
- Decide target root by consulting mappings/dataset_universal_map.json classes.
- Rename in destination with tag '__web__' using bulk_rename_by_class.py.
- Run deduplicate_images.py on touched class folders (near-scope=class, ham=3).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
SCRAPED_ROOT = ROOT / "web_scraper" / "scraped_images"
MAP_CONSOLIDATED = ROOT / "mappings" / "consolidated_mapping.json"
MAP_DATASET_UNIVERSAL = ROOT / "mappings" / "dataset_universal_map.json"
DATASETS = ROOT / "datasets"
RENAMER = ROOT / "scripts" / "bulk_rename_by_class.py"
DEDUP = ROOT / "scripts" / "deduplicate_images.py"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_consolidated_map() -> Dict[str, str]:
    if not MAP_CONSOLIDATED.exists():
        return {}
    data = json.loads(MAP_CONSOLIDATED.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for k, v in data.items():
        out[k.lower()] = v
    return out


def load_dataset_classes() -> Tuple[Set[str], Set[str], Set[str]]:
    crops: Set[str] = set()
    diseases: Set[str] = set()
    pests: Set[str] = set()
    if MAP_DATASET_UNIVERSAL.exists():
        j = json.loads(MAP_DATASET_UNIVERSAL.read_text(encoding="utf-8"))
        roots = j.get("roots", {})
        def collect(root_key: str) -> Set[str]:
            acc: Set[str] = set()
            root = roots.get(root_key)
            if not root:
                return acc
            classes = root.get("classes", {})
            for name in classes.keys():
                if name == "__root__":
                    continue
                acc.add(name)
            return acc
        crops = collect("datasets/crops")
        diseases = collect("datasets/diseases")
        pests = collect("datasets/pests")
    else:
        # Fallback: scan directories
        def scan(d: Path) -> Set[str]:
            if not d.exists():
                return set()
            return {p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith('.')}
        crops = scan(DATASETS / "crops")
        diseases = scan(DATASETS / "diseases")
        pests = scan(DATASETS / "pests")
    return crops, diseases, pests


def iter_scraped_images(root: Path) -> Iterable[Path]:
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and \
           ".rejected_by_llm" not in p.parts and ".trash" not in p.parts:
            yield p


def top_level_class(rel: Path) -> str:
    return rel.parts[0] if rel.parts else rel.name


def resolve_class_name(raw_cls: str, cmap: Dict[str, str]) -> str:
    return cmap.get(raw_cls.lower(), raw_cls)


def decide_root(class_name: str, crops: Set[str], diseases: Set[str], pests: Set[str]) -> Path:
    if class_name in diseases:
        return DATASETS / "diseases"
    if class_name in crops:
        return DATASETS / "crops"
    if class_name in pests:
        return DATASETS / "pests"
    # Default: diseases if looks like leaf/disease, else crops if plant-like, else pests
    low = class_name.lower()
    if "leaf" in low or "blight" in low or "rust" in low or "spot" in low or "mildew" in low:
        return DATASETS / "diseases"
    if any(w in low for w in ("plant", "tree", "seed", "fruit", "grain")):
        return DATASETS / "crops"
    return DATASETS / "pests"


def move_with_json(src_img: Path, dst_dir: Path, dry_run: bool) -> Path | None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    meta = src_img.with_suffix('.json')
    if not meta.exists():
        return None
    dst_img = dst_dir / src_img.name
    dst_meta = dst_dir / meta.name
    if dry_run:
        print(f"[DRY] MOVE {src_img} -> {dst_img}")
        print(f"[DRY] MOVE {meta} -> {dst_meta}")
        return dst_img
    shutil.move(str(src_img), str(dst_img))
    shutil.move(str(meta), str(dst_meta))
    return dst_img


def run_renamer(target: Path, tag: str, dry_run: bool) -> None:
    cmd = ["python3", str(RENAMER), "--root", str(target), "--tag", tag]
    if dry_run:
        print("[DRY]", " ".join(cmd))
        return
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def run_dedupe(targets: List[Path], dry_run: bool) -> None:
    if not targets:
        return
    cmd = [
        "python3", str(DEDUP), "--roots", *[str(t) for t in targets],
        "--blur-method", "both", "--blur-threshold", "60", "--tenengrad-threshold", "700",
        "--ham-threshold", "3", "--near-scope", "class", "--action", "move",
    ]
    if dry_run:
        print("[DRY]", " ".join(cmd))
        return
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="web")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not SCRAPED_ROOT.exists():
        print(f"Scraped root not found: {SCRAPED_ROOT}", file=sys.stderr)
        return 1

    cmap = load_consolidated_map()
    crops, diseases, pests = load_dataset_classes()

    moved: List[Path] = []
    touched_dirs: Set[Path] = set()

    for img in iter_scraped_images(SCRAPED_ROOT):
        if not img.with_suffix('.json').exists():
            continue
        try:
            rel = img.relative_to(SCRAPED_ROOT)
        except ValueError:
            continue
        raw_cls = top_level_class(rel)
        cls = resolve_class_name(raw_cls, cmap)
        target_root = decide_root(cls, crops, diseases, pests)
        dst_dir = target_root / cls
        dst_path = move_with_json(img, dst_dir, args.dry_run)
        if dst_path is not None:
            moved.append(dst_path)
            touched_dirs.add(dst_dir)

    print(f"Moved {len(moved)} images into {len(touched_dirs)} class folders.")

    for d in sorted(touched_dirs):
        run_renamer(d, args.tag, args.dry_run)

    run_dedupe(sorted(touched_dirs), args.dry_run)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
