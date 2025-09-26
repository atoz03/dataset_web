#!/usr/bin/env python3
"""
Scan datasets/{diseases,crops,pests} and produce bilingual JSONL covering
caption and VQA samples with labels, source, and splits.

Output JSONL fields per line:
  - image: relative path to image
  - task: one of {caption, vqa}
  - text: input text (caption text for caption task, question for vqa)
  - answer: only for vqa
  - lang: 'en' or 'zh'
  - labels: {root, class, crop, disease, pest, healthy, source}
  - split: 'train' | 'val' | 'test'

Usage:
  python3 scripts/build_jsonl.py --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl --train 0.8 --val 0.1 --test 0.1 --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
SOURCE_TOKENS = ("__cd__", "__pd__", "__ac__", "__ap__")


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def list_images(root: Path) -> List[Path]:
    out: List[Path] = []
    for r, _, files in os.walk(root):
        for f in files:
            p = Path(r) / f
            if is_image(p):
                out.append(p)
    return out


# English -> Chinese mapping for crops and common terms
CROP_ZH: Dict[str, str] = {
    # diseases crops
    "Apple": "苹果",
    "Bell_pepper": "甜椒",
    "Blueberry": "蓝莓",
    "Cherry": "樱桃",
    "Corn": "玉米",
    "Peach": "桃",
    "Potato": "马铃薯",
    "Raspberry": "覆盆子",
    "Rice": "稻",
    "Soyabean": "大豆",
    "Squash": "南瓜",
    "Strawberry": "草莓",
    "Sugarcane": "甘蔗",
    "Tomato": "番茄",
    "Wheat": "小麦",
    "grape": "葡萄",
    # crops dir
    "almond": "杏仁",
    "banana": "香蕉",
    "cardamom": "小豆蔻",
    "clove": "丁香",
    "coconut": "椰子",
    "cotton": "棉花",
    "gram": "鹰嘴豆",
    "jowar": "高粱",
    "jute": "黄麻",
    "kag2": "Kaggle补充",
    "maize": "玉米",
    "mustard-oil": "芥籽",
    "papaya": "木瓜",
    "pineapple": "菠萝",
    "rice": "稻",
    "soyabean": "大豆",
    "sugarcane": "甘蔗",
    "sunflower": "向日葵",
    "tea": "茶树",
    "tomato": "番茄",
    "vigna-radiati(Mung)": "绿豆",
    "wheat": "小麦",
    "Olive-tree": "橄榄树",
    "Coffee-plant": "咖啡树",
    "Tobacco-plant": "烟草",
    "Fox_nut(Makhana)": "芡实",
    "Pearl_millet(bajra)": "珍珠粟",
}


DISEASE_TOKENS = {
    "blight": "叶枯/疫病",
    "rust": "锈病",
    "spot": "斑点/斑病",
    "mildew": "白粉病",
    "virus": "病毒",
    "mite": "螨害",
    "rot": "腐烂/腐病",
    "bacterial": "细菌性病害",
    "blast": "稻瘟病",
    "septoria": "叶斑病(Septoria)",
    "mold": "霉病",
}


def infer_source(name: str, default_root: str) -> str:
    for tok in SOURCE_TOKENS:
        if tok in name:
            return tok.strip("_")
    return default_root  # e.g., 'diseases', 'crops', 'pests'


def split_by_class(items: List[Path], ratios: Tuple[float, float, float], seed: int) -> Dict[Path, str]:
    # Stratify per parent class directory
    random.seed(seed)
    assign: Dict[Path, str] = {}
    by_class: Dict[Path, List[Path]] = {}
    for p in items:
        by_class.setdefault(p.parent, []).append(p)
    for cls, lst in by_class.items():
        random.shuffle(lst)
        n = len(lst)
        n_train = int(n * ratios[0])
        n_val = int(n * ratios[1])
        for i, p in enumerate(lst):
            if i < n_train:
                assign[p] = "train"
            elif i < n_train + n_val:
                assign[p] = "val"
            else:
                assign[p] = "test"
    return assign


def norm_crop_name_from_class(class_name: str, root: str) -> Optional[str]:
    # Diseases: use the first token as crop (handling Bell_pepper, grape)
    if root == "diseases":
        # e.g., "Corn leaf blight" -> Corn, "Bell_pepper leaf" -> Bell_pepper, "grape leaf" -> grape
        tok = class_name.split(" ")[0]
        return tok
    if root == "crops":
        return class_name
    return None


def zh_crop(crop: Optional[str]) -> Optional[str]:
    if crop is None:
        return None
    return CROP_ZH.get(crop, CROP_ZH.get(crop.lower(), crop))


def infer_health_and_disease(class_name: str) -> Tuple[bool, Optional[str]]:
    lc = class_name.lower()
    # Healthy: ends with 'leaf' and no disease tokens
    tokens = [k for k in DISEASE_TOKENS.keys() if k in lc]
    if class_name.strip().lower().endswith("leaf") and not tokens:
        return True, None
    # Otherwise unhealthy if any token appears
    if tokens:
        return False, class_name
    # default unknown
    return False, None


def build_caption_and_vqa(root: str, class_name: str, path: Path) -> List[dict]:
    rel = str(path)
    base = path.name
    source = infer_source(base, root)
    crop = norm_crop_name_from_class(class_name, root)
    crop_zh = zh_crop(crop) if crop else None

    items: List[dict] = []
    if root == "diseases":
        healthy, disease = infer_health_and_disease(class_name)
        # Captions
        if healthy:
            en = f"A healthy {crop} leaf."
            zh = f"一张健康的{crop_zh}叶片。" if crop_zh else f"一张健康的叶片。"
        else:
            if disease:
                en = f"A {crop} leaf showing {disease}." if crop else f"A leaf showing {disease}."
                zh = f"一张{crop_zh}叶片，患有{disease}。" if crop_zh else f"一张叶片，患有{disease}。"
            else:
                en = f"A {class_name}."
                zh = f"一张{class_name}。"
        items.append({"image": rel, "task": "caption", "text": en, "lang": "en",
                      "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
        items.append({"image": rel, "task": "caption", "text": zh, "lang": "zh",
                      "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
        # VQA samples
        if crop:
            items.append({"image": rel, "task": "vqa", "text": "What crop is this?", "answer": crop, "lang": "en",
                          "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
            items.append({"image": rel, "task": "vqa", "text": "这是什么作物？", "answer": crop_zh or crop, "lang": "zh",
                          "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
        if healthy:
            items.append({"image": rel, "task": "vqa", "text": "Is the leaf healthy?", "answer": "yes", "lang": "en",
                          "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
            items.append({"image": rel, "task": "vqa", "text": "这片叶子是否健康？", "answer": "是", "lang": "zh",
                          "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
        else:
            if disease:
                items.append({"image": rel, "task": "vqa", "text": "What disease is present?", "answer": disease, "lang": "en",
                              "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
                items.append({"image": rel, "task": "vqa", "text": "这张叶片得了什么病？", "answer": disease, "lang": "zh",
                              "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
            else:
                items.append({"image": rel, "task": "vqa", "text": "Is the leaf healthy?", "answer": "unknown", "lang": "en",
                              "labels": {"root": root, "class": class_name, "crop": crop, "disease": disease, "healthy": healthy, "source": source}})
    elif root == "crops":
        crop = class_name
        crop_zh = zh_crop(crop) or crop
        en = f"A photo of {crop}."
        zh = f"一张{crop_zh}的图像。"
        items.append({"image": rel, "task": "caption", "text": en, "lang": "en",
                      "labels": {"root": root, "class": class_name, "crop": crop, "source": source}})
        items.append({"image": rel, "task": "caption", "text": zh, "lang": "zh",
                      "labels": {"root": root, "class": class_name, "crop": crop, "source": source}})
        items.append({"image": rel, "task": "vqa", "text": "What crop is this?", "answer": crop, "lang": "en",
                      "labels": {"root": root, "class": class_name, "crop": crop, "source": source}})
        items.append({"image": rel, "task": "vqa", "text": "这是什么作物？", "answer": crop_zh, "lang": "zh",
                      "labels": {"root": root, "class": class_name, "crop": crop, "source": source}})
    else:  # pests
        pest = class_name
        pest_zh = CROP_ZH.get(pest, CROP_ZH.get(pest.lower(), pest))
        en = f"An image of {pest}."
        zh = f"一张{pest_zh}的图像。"
        items.append({"image": rel, "task": "caption", "text": en, "lang": "en",
                      "labels": {"root": root, "class": class_name, "pest": pest, "source": source}})
        items.append({"image": rel, "task": "caption", "text": zh, "lang": "zh",
                      "labels": {"root": root, "class": class_name, "pest": pest, "source": source}})
        items.append({"image": rel, "task": "vqa", "text": "What pest is shown?", "answer": pest, "lang": "en",
                      "labels": {"root": root, "class": class_name, "pest": pest, "source": source}})
        items.append({"image": rel, "task": "vqa", "text": "这是什么害虫？", "answer": pest_zh, "lang": "zh",
                      "labels": {"root": root, "class": class_name, "pest": pest, "source": source}})
    return items


def build_dataset(roots: List[Path], ratios: Tuple[float, float, float], seed: int, out_path: Path) -> None:
    all_paths: List[Tuple[str, Path]] = []  # (root_name, path)
    for r in roots:
        if not r.exists():
            print(f"[WARN] Missing root {r}")
            continue
        root_name = r.name
        imgs = list_images(r)
        for p in imgs:
            all_paths.append((root_name, p))

    # Split per-class inside each root
    assign: Dict[Path, str] = {}
    for root_name in {rn for rn, _ in all_paths}:
        items = [p for rn, p in all_paths if rn == root_name]
        m = split_by_class(items, ratios, seed)
        assign.update(m)

    with out_path.open("w", encoding="utf-8") as wf:
        for root_name, p in all_paths:
            cls = p.parent.name
            split = assign.get(p, "train")
            entries = build_caption_and_vqa(root_name, cls, p)
            for e in entries:
                e["split"] = split
                # Store path relative to repo root
                e["image"] = str(Path(e["image"]))
                wf.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Wrote JSONL: {out_path}")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", default=["datasets/diseases", "datasets/crops", "datasets/pests"])
    ap.add_argument("--out", default="data.jsonl")
    ap.add_argument("--train", type=float, default=0.8)
    ap.add_argument("--val", type=float, default=0.1)
    ap.add_argument("--test", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    if abs(args.train + args.val + args.test - 1.0) > 1e-6:
        print("Split ratios must sum to 1.0", file=sys.stderr)
        return 2
    roots = [Path(r) for r in args.roots]
    out = Path(args.out)
    build_dataset(roots, (args.train, args.val, args.test), args.seed, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
