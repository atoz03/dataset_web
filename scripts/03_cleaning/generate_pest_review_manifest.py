#!/usr/bin/env python3
"""Regenerate docs review manifest from current scraped images.

Scans `web_scraper/scraped_images/` and writes
`web_scraper/pest_review_manifest.js` with entries that actually exist.

Rules:
- Include files with image extensions only。
- `.trash/` 中的文件也会被纳入清单，但会标记 `in_trash=true` 并保留原始类目/来源信息。
- `keyword` 使用图片所属的类目目录名（对于 `.trash/` 中的文件，仍保留原始类目）。
- `source` 是图片的直接父目录（例如 `bing.com`）。
- `id` 是基于仓库相对路径的 sha1。

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

        in_trash = parts[0] == '.trash'
        keyword: str
        source: str
        trash_reason = None

        if in_trash:
            # fallback keyword/source if structure is unexpected
            keyword = '__trash__'
            source = ''
            if len(parts) >= 2:
                source = parts[-2] if len(parts) >= 2 else ''
            if len(parts) >= 3:
                keyword_candidate = parts[-3]
                if keyword_candidate != '.trash':
                    keyword = keyword_candidate
            # capture intermediate segments as a joined trash reason for display
            if len(parts) > 3:
                reason_parts = [seg for seg in parts[1:-2] if seg and seg != '.trash']
                if reason_parts and reason_parts[-1] == keyword:
                    reason_parts = reason_parts[:-1]
                if reason_parts:
                    trash_reason = '/'.join(reason_parts)
        else:
            keyword = parts[0]
            source = img.parent.name

        entry = {
            'id': hashlib.sha1(rel_repo_posix.encode()).hexdigest(),
            'keyword': keyword,
            'source': source,
            'path': rel_repo_posix,
            'in_trash': in_trash,
        }
        if trash_reason:
            entry['trash_reason'] = trash_reason

        items.append(entry)

    items.sort(key=lambda x: (x['keyword'], x['path']))
    payload = "const pestReviewManifest = " + json.dumps(items, indent=2) + ";\n"
    out_path.write_text(payload, encoding='utf-8')
    print(f"Wrote {len(items)} entries -> {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(__import__('sys').argv[1:]))
