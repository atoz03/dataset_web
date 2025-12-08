#!/usr/bin/env python3
"""Move经人工审核的害虫图片到 datasets/pests 并自动重命名/去重。

使用流程：
  1. 在 docs/pest_manual_review.html 完成审核，下载 JSON 结果。
  2. 执行本脚本：
       python3 scripts/import_reviewed_pests.py \
           --review-json path/to/pest_review_xxx.json \
           --tag web

脚本会：
  - 读取 JSON，筛选 status == "accepted" 的条目；
  - 将对应图片从 web_scraper/scraped_images/<class>/... 拷贝到 datasets/pests/<class>/;
  - 调用 bulk_rename_by_class.py 统一命名 (<class>__<tag>__<uuid>.jpg)；
  - 调用 deduplicate_images.py (action=move) 做尺寸/模糊/重复清理；
  - 输出处理摘要。

可选：
  --dry-run           仅打印计划，不执行写操作
  --skip-rename       拷贝后跳过重命名
  --skip-dedupe       拷贝后跳过去重脚本
  --min-width/height  设置尺寸过滤阈值（默认 224）
  --blur-threshold    模糊阈值（默认 60）
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "mappings" / "consolidated_mapping.json"
SCRAPER_ROOT = ROOT / "web_scraper" / "scraped_images"
DEFAULT_DATASET_ROOT = ROOT / "datasets" / "pests"
BULK_RENAME_SCRIPT = ROOT / "scripts" / "bulk_rename_by_class.py"
DEDUP_SCRIPT = ROOT / "scripts" / "deduplicate_images.py"
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_mapping() -> Dict[str, str]:
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(f"Mapping file not found: {MAPPING_PATH}")
    with MAPPING_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    reverse: Dict[str, str] = {}
    for src, dst in data.items():
        reverse[src.lower()] = dst
        reverse[dst.lower()] = dst
    return reverse


def resolve_class(keyword: str, mapping: Dict[str, str]) -> str:
    key = keyword.lower()
    if key in mapping:
        return mapping[key]
    return keyword


def iter_entries(review_data: Iterable[dict]) -> Iterable[dict]:
    for item in review_data:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "accepted":
            continue
        path = item.get("path")
        if not path:
            continue
        yield item


def copy_image(src_path: Path, dst_dir: Path, dry_run: bool) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / src_path.name
    if dry_run:
        print(f"[DRY-RUN] copy {src_path} -> {dst_path}")
        return dst_path
    shutil.copy2(src_path, dst_path)
    return dst_path


def run_bulk_rename(target: Path, tag: str, dry_run: bool) -> None:
    args = ["python3", str(BULK_RENAME_SCRIPT), "--root", str(target), "--tag", tag]
    if dry_run:
        args.append("--dry-run")
    subprocess.run(args, check=True, cwd=ROOT)


def run_dedupe(targets: Iterable[Path], min_w: int, min_h: int,
               blur_thr: float, dry_run: bool) -> None:
    roots = [str(p) for p in targets]
    if not roots:
        return
    cmd = [
        "python3",
        str(DEDUP_SCRIPT),
        "--roots",
        *roots,
        "--min-width",
        str(min_w),
        "--min-height",
        str(min_h),
        "--blur-threshold",
        str(blur_thr),
        "--action",
        "move",
    ]
    if dry_run:
        print("[DRY-RUN] dedupe command:", " ".join(cmd))
        return
    subprocess.run(cmd, check=True, cwd=ROOT)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--review-json", required=True, help="JSON exported from review page")
    ap.add_argument("--tag", default="web", help="Source tag for rename (default: web)")
    ap.add_argument("--dest-root", default=str(DEFAULT_DATASET_ROOT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-rename", action="store_true")
    ap.add_argument("--skip-dedupe", action="store_true")
    ap.add_argument("--min-width", type=int, default=224)
    ap.add_argument("--min-height", type=int, default=224)
    ap.add_argument("--blur-threshold", type=float, default=60.0)
    args = ap.parse_args(argv)

    review_path = Path(args.review_json)
    if not review_path.exists():
        print(f"Review JSON not found: {review_path}", file=sys.stderr)
        return 1

    with review_path.open("r", encoding="utf-8") as fh:
        review_data = json.load(fh)
    if not isinstance(review_data, list):
        print("Review JSON must be a list", file=sys.stderr)
        return 1

    mapping = load_mapping()
    dest_root = Path(args.dest_root)
    accepted = list(iter_entries(review_data))
    if not accepted:
        print("No accepted entries found. Nothing to do.")
        return 0

    copied_paths = []
    touched_classes = set()

    for entry in accepted:
        keyword = entry.get("keyword") or "unknown"
        target_class = resolve_class(keyword, mapping)
        rel_path = entry["path"]
        src_path = ROOT / rel_path
        if src_path.suffix.lower() not in ALLOWED_EXTS:
            print(f"[SKIP] Unsupported extension: {src_path}")
            continue
        if not src_path.exists():
            print(f"[SKIP] Source not found: {src_path}")
            continue
        class_dir = dest_root / target_class
        copied = copy_image(src_path, class_dir, args.dry_run)
        copied_paths.append(copied)
        touched_classes.add(class_dir)

    print(f"Copied {len(copied_paths)} images into {len(touched_classes)} class folders.")

    if args.skip_rename:
        print("Skip rename flag set; remember to run bulk_rename_by_class.py later.")
    else:
        for class_dir in sorted(touched_classes):
            run_bulk_rename(class_dir, args.tag, args.dry_run)

    if args.skip_dedupe:
        print("Skip dedupe flag set; remember to run deduplicate_images.py later.")
    else:
        if args.dry_run:
            print("[DRY-RUN] Skip dedupe (no changes applied).")
        else:
            run_dedupe(sorted(touched_classes), args.min_width, args.min_height, args.blur_threshold, False)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
