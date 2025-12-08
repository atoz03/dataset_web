#!/usr/bin/env python3
"""
Bulk rename images inside class folders under a root directory to a
standard pattern: <class>__<tag>__<uuid>.<ext>

Intended to normalize existing files in datasets/diseases that predate
the Crop Diseases merge. Files already following a double-underscore tag
like '__cd__' are skipped by default.

Usage:
  python3 scripts/bulk_rename_by_class.py --root datasets/diseases --tag pd [--dry-run]

Notes:
- Only files directly inside class folders (one level deep) are targeted;
  nested subfolders are traversed as well, preserving the parent class name.
- Image types: .jpg .jpeg .png .bmp .webp
- Skips files whose basename already contains '__cd__' or '__pd__' to avoid
  double-renaming. You can override with --force.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Iterable


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SKIP_TOKENS = ("__cd__", "__pd__")


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def iter_files(root: Path) -> Iterable[Path]:
    for r, _, files in os.walk(root):
        for f in files:
            yield Path(r) / f


def new_name_for(class_name: str, tag: str, src: Path) -> str:
    ext = src.suffix.lower()
    if ext not in IMAGE_EXTS:
        ext = ".jpg"
    cls = class_name.replace("/", "-").strip()
    return f"{cls}__{tag}__{uuid.uuid4().hex}{ext}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Root folder containing class subfolders")
    ap.add_argument("--tag", required=True, help="Source tag to inject, e.g., 'pd'")
    ap.add_argument("--dry-run", action="store_true", help="Only print actions")
    ap.add_argument("--force", action="store_true", help="Rename even if token present")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"Root not found: {root}", file=sys.stderr)
        return 1

    renamed = 0
    skipped = 0
    processed = 0

    for p in iter_files(root):
        processed += 1
        if not is_image(p):
            skipped += 1
            continue
        # class name inferred as the immediate parent folder name
        cls = p.parent.name
        base = p.name
        if not args.force and any(tok in base for tok in SKIP_TOKENS):
            skipped += 1
            continue
        nn = new_name_for(cls, args.tag, p)
        dst = p.with_name(nn)
        if args.dry_run:
            print(f"RENAME: {p} -> {dst}")
        else:
            try:
                p.rename(dst)
            except OSError as e:
                print(f"[WARN] Failed to rename {p}: {e}")
                skipped += 1
                continue
        renamed += 1

    print("Summary:")
    print(f"  Files processed: {processed}")
    print(f"  Renamed:        {renamed}")
    print(f"  Skipped:        {skipped}")
    print(f"  Root:           {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
