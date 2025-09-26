#!/usr/bin/env python3
"""
Merge images from the local "140-most-popular-crops-image-dataset" into
datasets/crops with fine-grained class mapping and standardized filenames.

Decisions implemented (per user confirmation):
- Strategy B (harmonized naming):
  * Keep careful semantic mapping into existing class folders where safe.
  * Create new class folders for unmatched/ambiguous classes.
  * Merge chili varieties into existing 'chilli' class; keep 'Black pepper' separate.
  * Keep non-plant agricultural items like 'Hen eggs (shell weight)' as-is.
- Copy-only (no move), provenance via filename tag '__ac__'.

Output filename pattern: <class>__ac__<uuid>.<ext> (lowercase ext)

It also writes two artifacts under mappings/:
  - 140_crops_map.json: source_class -> dest_class mapping used.
  - 140_crops_report.json: summary counts per dest_class and totals.

Usage:
  python3 scripts/merge_140_crops.py \
    --src 140-most-popular-crops-image-dataset/Raw/Raw \
    --dst datasets/crops \
    [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import unicodedata
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def norm_source_class_name(s: str) -> str:
    # Trim and drop trailing ' plant'
    s = s.strip()
    if s.lower().endswith(" plant"):
        s = s[:-6]
    # Normalize unicode accents
    s = ascii_fold(s)
    # Collapse whitespace
    s = " ".join(s.split())
    return s


def sanitize_dest_dir_name(s: str) -> str:
    # Replace path separators with hyphen, keep parentheses/commas/hyphens
    s = s.replace("/", "-")
    s = s.replace("\\", "-")
    s = s.strip()
    return s


def build_mapping(existing_dirs: Dict[str, str]) -> Dict[str, str]:
    """Return a mapping from normalized lowercase source class to
    destination class directory name. Values point to existing folder names
    where appropriate, otherwise to proposed new folder names.

    existing_dirs: map lowercased existing dir name -> actual dir name
    """
    m: Dict[str, str] = {}

    # Helpers to bind to an existing folder by exact name (case-insensitive)
    def bind_exact(name: str, existing_key: str | None = None) -> None:
        key = name.lower()
        if existing_key is None:
            existing_key = key
        if existing_key in existing_dirs:
            m[key] = existing_dirs[existing_key]
        else:
            # Fall back to given name itself (create new)
            m[key] = sanitize_dest_dir_name(name)

    # Map synonyms and variants to existing dataset folder names
    to_existing = {
        # one-to-one into existing dirs
        "maize (corn)": "maize",
        "corn": "maize",
        "rice (paddy)": "rice",
        "wheat": "wheat",
        "tomatoes": "tomato",
        "bananas": "banana",
        "coconuts": "coconut",
        "coffee (green)": "Coffee-plant",
        "olives": "Olive-tree",
        "soybeans": "soyabean",
        "pineapples": "pineapple",
        "papayas": "papaya",
        "sunflowers": "sunflower",
        "tea": "tea",
        "jute": "jute",
        "sorghum": "jowar",
        "cucumbers and gherkins": "Cucumber",
        "tobacco plant": "Tobacco-plant",
        "sugar cane": "sugarcane",
        "cardamom": "cardamom",
        "cloves": "clove",
        "almonds": "almond",
        "cherry": "Cherry",
        "fox nut(makhana)": "Fox_nut(Makhana)",
        "fox nut (makhana)": "Fox_nut(Makhana)",
        "pearl millet (bajra)": "Pearl_millet(bajra)",
        "pearl millet(bajra)": "Pearl_millet(bajra)",
        "lemons": "Lemon",  # only plain lemons; 'Lemons and limes' kept separate
        "lemon": "Lemon",
        "mung bean": "vigna-radiati(Mung)",
    }

    # Chili family merged into existing 'chilli'
    to_chilli = {
        "chili peppers and green peppers",
        "aji pepper",
        "habanero pepper",
        "green peppers",
        "green pepper",
        "chilli",
        "chili",
        "chile",
    }

    for k, v in to_existing.items():
        if v.lower() in existing_dirs:
            m[k] = existing_dirs[v.lower()]
        else:
            m[k] = v

    for k in to_chilli:
        m[k] = "chilli" if "chilli" in existing_dirs else sanitize_dest_dir_name("chilli")

    return m


def choose_dest_dir(src_cls_raw: str, existing_dirs: Dict[str, str], alias: Dict[str, str]) -> Tuple[str, bool]:
    """Return (dest_dir_name, is_existing) for a given source class name.
    is_existing indicates whether the dest_dir already existed prior to merge.
    """
    norm = norm_source_class_name(src_cls_raw)
    key = norm.lower()

    # Direct alias match
    if key in alias:
        dest = alias[key]
        is_existing = dest.lower() in existing_dirs
        return dest, is_existing

    # If exact case-insensitive match to an existing dir, use it
    if key in existing_dirs:
        return existing_dirs[key], True

    # Singular fallback: drop trailing 's'
    if key.endswith('s') and key[:-1] in existing_dirs:
        return existing_dirs[key[:-1]], True

    # Default: create new folder named by normalized class
    return sanitize_dest_dir_name(norm), False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="140-most-popular-crops-image-dataset/Raw/Raw")
    ap.add_argument("--dst", default="datasets/crops")
    ap.add_argument("--tag", default="ac")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    src_root = Path(args.src)
    dst_root = Path(args.dst)
    if not src_root.exists():
        print(f"[ERR] Source root missing: {src_root}", file=sys.stderr)
        return 1
    if not dst_root.exists():
        print(f"[ERR] Dest root missing: {dst_root}", file=sys.stderr)
        return 1

    existing_dirs = {p.name.lower(): p.name for p in dst_root.iterdir() if p.is_dir()}
    alias = build_mapping(existing_dirs)

    # Prepare reporting
    map_out: Dict[str, str] = {}
    counts_by_dest: Dict[str, int] = defaultdict(int)
    created_dirs = set()
    copied = 0
    skipped_non_image = 0
    classes_total = 0

    for cls_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
        classes_total += 1
        src_cls_raw = cls_dir.name
        dest_dir_name, existed = choose_dest_dir(src_cls_raw, existing_dirs, alias)
        map_out[src_cls_raw] = dest_dir_name
        dest_dir = dst_root / dest_dir_name
        if not dest_dir.exists():
            if not args.dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.add(dest_dir_name)

        for r, _, files in os.walk(cls_dir):
            for f in files:
                sp = Path(r) / f
                if not is_image(sp):
                    skipped_non_image += 1
                    continue
                ext = sp.suffix.lower()
                if ext not in IMAGE_EXTS:
                    ext = ".jpg"
                fname = f"{dest_dir_name}__{args.tag}__{uuid.uuid4().hex}{ext}"
                dp = dest_dir / fname
                if args.dry_run:
                    print(f"COPY: {sp} -> {dp}")
                else:
                    try:
                        shutil.copy2(sp, dp)
                    except Exception as e:
                        print(f"[WARN] Failed to copy {sp} -> {dp}: {e}")
                        continue
                counts_by_dest[dest_dir_name] += 1
                copied += 1

    # Write mapping and report
    mappings_dir = Path("mappings")
    if not args.dry_run:
        mappings_dir.mkdir(exist_ok=True)
        with (mappings_dir / "140_crops_map.json").open("w", encoding="utf-8") as wf:
            json.dump(map_out, wf, ensure_ascii=False, indent=2)
        report = {
            "source_root": str(src_root),
            "dest_root": str(dst_root),
            "classes_total": classes_total,
            "created_dirs": sorted(created_dirs),
            "existing_dirs_used": sorted({v for v in map_out.values() if v.lower() in existing_dirs}),
            "copied": copied,
            "skipped_non_image": skipped_non_image,
            "counts_by_dest": counts_by_dest,
        }
        # Convert defaultdict to normal dict for JSON
        report["counts_by_dest"] = {k: int(v) for k, v in counts_by_dest.items()}
        with (mappings_dir / "140_crops_report.json").open("w", encoding="utf-8") as wf:
            json.dump(report, wf, ensure_ascii=False, indent=2)

    print("Merge summary:")
    print(f"  Classes scanned: {classes_total}")
    print(f"  Copied images:  {copied}")
    print(f"  Non-images:     {skipped_non_image}")
    print(f"  New class dirs: {len(created_dirs)}")
    print(f"  Report:         mappings/140_crops_report.json")
    print(f"  Mapping:        mappings/140_crops_map.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
