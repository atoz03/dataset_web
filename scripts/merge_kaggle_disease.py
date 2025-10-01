#!/usr/bin/env python3
"""
Merge a downloaded Kaggle disease dataset into datasets/diseases.

Assumptions:
  - Source dir has class subfolders under the given --src (e.g., PlantVillage-like).
  - Files may have arbitrary names; we will normalize via bulk_rename_by_class.py
    into pattern <class>__<tag>__<uuid>.<ext>.

Usage:
  python3 scripts/merge_kaggle_disease.py --src sources/plantvillage --tag kd

Notes:
  - Copy-only; never move.
  - Creates mappings/<name>_report.json with per-class counts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Source root with class subfolders")
    ap.add_argument("--dst", default="datasets/diseases", help="Destination diseases root")
    ap.add_argument("--tag", default="kd", help="Source tag to embed in filenames")
    ap.add_argument("--rename", action="store_true", help="Run bulk_rename_by_class on --src before merging")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)

    if args.rename:
        # invoke the renamer so files have __<tag>__ pattern
        rename_script = Path(__file__).resolve().parent / "bulk_rename_by_class.py"
        subprocess.run(
            [
                sys.executable,
                str(rename_script),
                "--root",
                str(src),
                "--tag",
                args.tag,
                "--force",
            ],
            check=True,
        )

    report = {
        "source_root": str(src),
        "dest_root": str(dst),
        "tag": args.tag,
        "created_dirs": [],
        "existing_dirs_used": [],
        "counts_per_class": {},
        "total_copied": 0,
    }

    created, used = set(), set()
    counts = defaultdict(int)

    for cls_dir in sorted([p for p in src.iterdir() if p.is_dir()]):
        out_dir = dst / cls_dir.name
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            created.add(cls_dir.name)
        else:
            used.add(cls_dir.name)
        for f in cls_dir.iterdir():
            if f.is_file() and is_image(f):
                # copy using existing unique filename
                target = out_dir / f.name
                if target.exists():
                    # extremely unlikely if using uuid, fallback with suffix
                    stem, ext = f.stem, f.suffix
                    i = 1
                    while (out_dir / f"{stem}_{i}{ext}").exists():
                        i += 1
                    target = out_dir / f"{stem}_{i}{ext}"
                shutil.copy2(f, target)
                counts[cls_dir.name] += 1
                report["total_copied"] += 1

    report["created_dirs"] = sorted(created)
    report["existing_dirs_used"] = sorted(used)
    report["counts_per_class"] = dict(sorted(counts.items()))

    name = src.name.replace(" ", "_")
    out = Path("mappings") / f"{name}_merge_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Copied {report['total_copied']} images from {src} into {dst}")
    print(f"Report: {out}")


if __name__ == "__main__":
    main()
