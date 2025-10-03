#!/usr/bin/env python3
"""Regenerate docs review manifest from current scraped images.

Scans `web_scraper/scraped_images/` and writes
`web_scraper/pest_review_manifest.js` with entries that actually exist.

Rules:
- Include files with image extensions only.
- Exclude any path under a `.trash/` directory.
- `keyword` is the first-level directory under `scraped_images/`.
- `source` is the immediate parent directory of the image (e.g., `bing.com`).
- `id` is sha1 of the repository-relative path used in `path`.

Usage:
  python3 scripts/generate_pest_review_manifest.py \
    --root web_scraper/scraped_images \
    --out web_scraper/pest_review_manifest.js
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def iter_images(root: Path) -> Iterable[Path]:
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if any(tok == '.trash' for tok in p.parts):
            continue
        if p.suffix.lower() in IMAGE_EXTS:
            yield p


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='web_scraper/scraped_images', help='Folder to scan')
    ap.add_argument('--out', default='web_scraper/pest_review_manifest.js', help='Output JS file')
    args = ap.parse_args(argv)

    repo_root = Path('.').resolve()
    root = (repo_root / args.root).resolve()
    out_path = (repo_root / args.out)

    if not root.exists():
        print(f"Root not found: {root}")
        return 1

    items = []
    for img in iter_images(root):
        try:
            rel_repo = img.relative_to(repo_root)
        except Exception:
            # If not under repo root, skip
            continue
        rel_repo_posix = rel_repo.as_posix()

        # keyword: first dir under scraped_images
        try:
            rel_to_root = img.relative_to(root)
        except Exception:
            continue
        parts = rel_to_root.parts
        if len(parts) < 1:
            continue
        keyword = parts[0]
        # source: immediate parent folder of the image
        source = img.parent.name

        items.append({
            'id': hashlib.sha1(rel_repo_posix.encode()).hexdigest(),
            'keyword': keyword,
            'source': source,
            'path': rel_repo_posix,
        })

    items.sort(key=lambda x: (x['keyword'], x['path']))
    payload = "const pestReviewManifest = " + json.dumps(items, indent=2) + ";\n"
    out_path.write_text(payload, encoding='utf-8')
    print(f"Wrote {len(items)} entries -> {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(__import__('sys').argv[1:]))

