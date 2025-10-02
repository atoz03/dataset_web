#!/usr/bin/env python3
"""
Enhanced image cleanup utility with:
- Perceptual hashing (pHash / aHash fallback) for duplicate detection
- Blur detection via Laplacian variance
- Minimum size filtering
- Batch cleanup with safe trash move (or hard delete)

Examples:
  python3 scripts/deduplicate_images.py --roots datasets/diseases datasets/crops datasets/pests \
      --min-width 224 --min-height 224 --blur-threshold 60 --action move

Notes:
- Requires Pillow. NumPy is optional (accelerates Laplacian/variance and pHash DCT).
- By default, near-duplicate search uses exact hash match. You can allow small
  Hamming distance with --ham-threshold N (may increase runtime).
"""

import argparse
import hashlib
import os
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from PIL import Image, ImageFilter
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def is_image_file(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in IMAGE_EXTS


def ahash(img: "Image.Image", hash_size: int = 8) -> int:
    g = img.convert("L").resize((hash_size, hash_size))
    pixels = list(g.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, p in enumerate(pixels):
        if p >= avg:
            bits |= 1 << i
    return bits


def phash(img: "Image.Image", hash_size: int = 8, highfreq_factor: int = 4) -> int:
    if np is None:
        return ahash(img, hash_size)
    img = img.convert("L").resize((hash_size * highfreq_factor, hash_size * highfreq_factor))
    arr = np.asarray(img, dtype=np.float32)
    # 2D DCT
    dct = np.real(np.fft.fft2(arr))
    dct = np.abs(dct)
    # top-left low frequencies
    dctlow = dct[:hash_size, :hash_size]
    med = np.median(dctlow)
    bits = 0
    flat = dctlow.flatten()
    for i, v in enumerate(flat):
        if v >= med:
            bits |= 1 << i
    return bits


def hamming(a: int, b: int) -> int:
    x = a ^ b
    try:
        return x.bit_count()  # Python 3.10+
    except AttributeError:  # Fallback for older Python
        return bin(x).count("1")


def laplacian_var(img: "Image.Image") -> float:
    # Prefer NumPy path for speed
    if np is not None:
        g = np.asarray(img.convert("L"), dtype=np.float32)
        # 3x3 Laplacian kernel
        k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
        from numpy.lib.stride_tricks import as_strided
        H, W = g.shape
        kh, kw = k.shape
        sh, sw = g.strides
        bh, bw = H - kh + 1, W - kw + 1
        s = as_strided(g, shape=(bh, bw, kh, kw), strides=(sh, sw, sh, sw))
        conv = (s * k).sum(axis=(2, 3))
        return float(conv.var())
    # Fallback: use Pillow edge filter as proxy then variance of pixel values
    e = img.convert("L").filter(ImageFilter.FIND_EDGES)
    vals = list(e.getdata())
    m = sum(vals) / len(vals)
    return float(sum((v - m) ** 2 for v in vals) / len(vals))


def open_image(path: Path) -> "Image.Image | None":
    if Image is None:
        print("[ERROR] Pillow not installed; cannot analyze images", file=sys.stderr)
        return None
    try:
        return Image.open(path)
    except Exception as e:
        print(f"[WARN] Failed to open {path}: {e}")
        return None


def make_trash_dir(root: Path, reason: str) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    d = root / ".trash" / f"{reason}_{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def move_to(dst_root: Path, src: Path, rel: Path) -> Path:
    out = dst_root / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(out))
    return out


@dataclass
class Stats:
    total: int = 0
    removed_small: int = 0
    removed_blur: int = 0
    removed_dupe: int = 0
    errors: int = 0


def collect_images(root: Path) -> List[Path]:
    items: List[Path] = []
    for r, _, files in os.walk(root):
        for f in files:
            if is_image_file(f):
                items.append(Path(r) / f)
    return items


def cleanup_root(root: Path, min_w: int, min_h: int, blur_thr: float, action: str,
                 ham_thr: int, near_scope: str = "dir") -> Stats:
    stats = Stats()
    images = collect_images(root)
    stats.total = len(images)
    trash_small = make_trash_dir(root, "small") if action == "move" else None
    trash_blur = make_trash_dir(root, "blur") if action == "move" else None
    trash_dupe = make_trash_dir(root, "dupe") if action == "move" else None

    # First pass: size/blur filtering and compute hashes
    hashes: Dict[int, List[Path]] = defaultdict(list)
    kept: List[Tuple[Path, int]] = []
    for p in images:
        img = open_image(p)
        if img is None:
            stats.errors += 1
            continue
        try:
            w, h = img.size
        except Exception:
            stats.errors += 1
            continue
        if w < min_w or h < min_h:
            if action == "delete":
                try:
                    p.unlink()
                except Exception as e:
                    print(f"[WARN] Delete failed {p}: {e}")
                    stats.errors += 1
                stats.removed_small += 1
            else:
                rel = p.relative_to(root)
                move_to(trash_small, p, rel)  # type: ignore[arg-type]
                stats.removed_small += 1
            continue
        # Blur
        try:
            lv = laplacian_var(img)
        except Exception as e:
            print(f"[WARN] Blur failed {p}: {e}")
            lv = blur_thr
        if lv < blur_thr:
            if action == "delete":
                try:
                    p.unlink()
                except Exception as e:
                    print(f"[WARN] Delete failed {p}: {e}")
                    stats.errors += 1
                stats.removed_blur += 1
            else:
                rel = p.relative_to(root)
                move_to(trash_blur, p, rel)  # type: ignore[arg-type]
                stats.removed_blur += 1
            continue
        # Hash
        try:
            hval = phash(img)
        except Exception:
            hval = ahash(img)
        hashes[hval].append(p)
        kept.append((p, hval))

    # Second pass: exact/near-duplicate removal
    removed = set()
    if ham_thr <= 0:
        # Exact buckets
        for bucket in hashes.values():
            if len(bucket) <= 1:
                continue
            # Keep the first, remove the rest
            for q in bucket[1:]:
                if action == "delete":
                    try:
                        q.unlink()
                    except Exception as e:
                        print(f"[WARN] Delete failed {q}: {e}")
                        stats.errors += 1
                else:
                    rel = q.relative_to(root)
                    move_to(trash_dupe, q, rel)  # type: ignore[arg-type]
                stats.removed_dupe += 1
                removed.add(q)
    else:
        # Near-duplicate grouping scope
        # - dir: only within the same immediate parent directory (default)
        # - class: within first-level directory under the given root (helps cross-source dedupe like scraped_images/<class>/<source>)
        # - root: compare across the entire root (may be expensive)
        groups: Dict[Path, List[Tuple[Path, int]]] = defaultdict(list)
        for p, hv in kept:
            if near_scope == "root":
                key = root
            elif near_scope == "class":
                try:
                    rel = p.relative_to(root)
                    # group by top-level directory under root when available
                    top = rel.parts[0] if len(rel.parts) >= 1 else None
                    key = (root / top) if top else p.parent
                except Exception:
                    key = p.parent
            else:  # "dir"
                key = p.parent
            groups[key].append((p, hv))
        for d, items in groups.items():
            n = len(items)
            items.sort(key=lambda x: x[0].name)
            for i in range(n):
                pi, hi = items[i]
                if pi in removed:
                    continue
                for j in range(i + 1, n):
                    pj, hj = items[j]
                    if pj in removed:
                        continue
                    if hamming(hi, hj) <= ham_thr:
                        # remove pj
                        if action == "delete":
                            try:
                                pj.unlink()
                            except Exception as e:
                                print(f"[WARN] Delete failed {pj}: {e}")
                                stats.errors += 1
                        else:
                            rel = pj.relative_to(root)
                            move_to(trash_dupe, pj, rel)  # type: ignore[arg-type]
                        stats.removed_dupe += 1
                        removed.add(pj)

    return stats


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", default=["datasets/diseases"], help="Root folders to clean")
    ap.add_argument("--min-width", type=int, default=224)
    ap.add_argument("--min-height", type=int, default=224)
    ap.add_argument("--blur-threshold", type=float, default=60.0, help="Lower means blurrier")
    ap.add_argument("--ham-threshold", type=int, default=0, help="Hamming threshold for near-duplicate removal")
    ap.add_argument("--near-scope", choices=["dir", "class", "root"], default="dir",
                    help="Scope for near-duplicate grouping: dir (default), class (first directory under root), or root (global)")
    ap.add_argument("--action", choices=["move", "delete"], default="move")
    args = ap.parse_args(argv)

    roots = [Path(r) for r in args.roots]
    overall = Stats()
    for root in roots:
        if not root.exists():
            print(f"[WARN] Skip missing root: {root}")
            continue
        print(f"== Cleaning {root} ==")
        st = cleanup_root(root, args.min_width, args.min_height, args.blur_threshold, args.action, args.ham_threshold, args.near_scope)
        print(f"  Total: {st.total} | Small: {st.removed_small} | Blur: {st.removed_blur} | Dupe: {st.removed_dupe} | Errors: {st.errors}")
        overall.total += st.total
        overall.removed_small += st.removed_small
        overall.removed_blur += st.removed_blur
        overall.removed_dupe += st.removed_dupe
        overall.errors += st.errors

    print("Summary (all roots):")
    print(f"  Total: {overall.total} | Small: {overall.removed_small} | Blur: {overall.removed_blur} | Dupe: {overall.removed_dupe} | Errors: {overall.errors}")
    if Image is None:
        print("[HINT] Install Pillow: pip install pillow", file=sys.stderr)
    if np is None:
        print("[HINT] (Optional) Install numpy for faster pHash/blur.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
