#!/usr/bin/env python3
"""
从.rejected_by_llm/中挽救错误标注的害虫图片
将它们移动到scraped_images/的正确类别目录，并重新生成JSON元数据
"""
import os
import json
import shutil
import argparse
import logging
from pathlib import Path
from typing import Set, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 定义害虫类别白名单（只移动这些类别）
PEST_CATEGORIES = {
    # 核心害虫
    'moth', 'caterpillar', 'beetle', 'grasshopper', 'ant', 'wasp',
    'aphid', 'aphids', 'spider', 'weevil', 'cicada', 'cricket',
    'leafhopper', 'earwig', 'stink_bug', 'damselfly', 'dragonfly',
    'ladybug', 'snail', 'slug', 'butterfly',

    # 特定害虫种类
    'colorado_potato_beetle', 'potato_beetle', 'bark_beetle',
    'leaf_beetle', 'scarab_beetle', 'soldier_beetle', 'rhinoceros_beetle',
    'cabbage_worm', 'armyworm', 'cutworm', 'corn_earworm',
    'japanese_beetle', 'flea_beetle', 'click_beetle',

    # 幼虫形态
    'moth_larva', 'beetle_larva', 'fly_larva', 'fruit_fly_larva',
    'colorado_potato_beetle_larva',

    # 其他昆虫害虫
    'thrips', 'mite', 'scale_insect', 'mealybug', 'psyllid',
    'planthopper', 'treehopper', 'whitefly', 'locust',

    # 蜘蛛类
    'spider_mite', 'red_spider_mite',

    # 软体动物
    'snail_damage', 'slug_damage',

    # 复数/群体形态
    'beetles', 'caterpillars', 'moths', 'locusts', 'ants',
    'locust_swarm', 'ant_colony',
}

# 需要排除的非害虫类别
EXCLUDE_CATEGORIES = {
    'plant', 'leaf', 'flower', 'tree', 'tree_bark', 'mushroom',
    'bird', 'seashell', 'marine_slug', 'human_finger', 'hand',
    'leaf_spot', 'leaf_damage', 'bark_damage', 'fruit', 'seed',
    'wild_mallow', 'mugwort', 'poppy_flower', 'holly_berries',
    'hemlock_branch', 'gorse', 'ivy_plant', 'claytonia_virginica',
    'apple', 'potato', 'tomato', 'corn', 'grape',
}


def is_pest_category(category_name: str) -> bool:
    """判断类别是否为害虫类别"""
    normalized = category_name.lower().strip().replace('-', '_')

    # 优先排除非害虫
    if normalized in EXCLUDE_CATEGORIES:
        return False

    # 精确匹配
    if normalized in PEST_CATEGORIES:
        return True

    # 模糊匹配：包含害虫关键词
    pest_keywords = [
        'beetle', 'moth', 'caterpillar', 'worm', 'aphid', 'weevil',
        'bug', 'fly', 'wasp', 'ant', 'cricket', 'grasshopper',
        'locust', 'cicada', 'spider', 'mite', 'snail', 'slug',
        'larva', 'pest', 'insect'
    ]

    return any(keyword in normalized for keyword in pest_keywords)


def scan_rejected_dir(rejected_dir: Path) -> Dict[str, int]:
    """扫描.rejected_by_llm/目录，返回类别统计"""
    stats = {}

    if not rejected_dir.exists():
        logging.warning(f"Rejected directory not found: {rejected_dir}")
        return stats

    for category_dir in rejected_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category_name = category_dir.name
        image_count = sum(1 for f in category_dir.iterdir()
                         if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'})

        if image_count > 0:
            stats[category_name] = image_count

    return stats


def rescue_category(
    category_name: str,
    rejected_dir: Path,
    target_root: Path,
    dry_run: bool = False,
    regenerate_metadata: bool = True
) -> int:
    """
    挽救一个害虫类别的所有图片

    Returns:
        移动的图片数量
    """
    source_dir = rejected_dir / category_name
    target_dir = target_root / category_name

    if not source_dir.exists():
        logging.warning(f"Source directory not found: {source_dir}")
        return 0

    # 收集所有图片
    image_files = [f for f in source_dir.iterdir()
                   if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]

    if not image_files:
        logging.info(f"No images found in {category_name}")
        return 0

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Rescuing {len(image_files)} images from '{category_name}'")

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    for img_path in image_files:
        target_path = target_dir / img_path.name

        if dry_run:
            logging.debug(f"Would move: {img_path} -> {target_path}")
            moved_count += 1
        else:
            try:
                # 移动图片
                shutil.move(str(img_path), str(target_path))
                moved_count += 1

                # 生成元数据（简化版，标记为rescued）
                if regenerate_metadata:
                    metadata = {
                        "is_match": True,
                        "actual_class": category_name,
                        "quality_score": 7.0,  # 默认中等质量
                        "rejection_reason": None,
                        "description_en": f"This is a photo of {category_name.replace('_', ' ')}.",
                        "description_zh": f"这是{category_name.replace('_', ' ')}的照片。",
                        "rescued_from_rejected": True
                    }

                    json_path = target_path.with_suffix('.json')
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)

            except Exception as e:
                logging.error(f"Failed to move {img_path}: {e}")

    return moved_count


def main():
    parser = argparse.ArgumentParser(description='挽救错误标注的害虫图片')
    parser.add_argument(
        '--rejected-dir',
        type=Path,
        default=Path('web_scraper/scraped_images/.rejected_by_llm'),
        help='被拒绝图片的目录'
    )
    parser.add_argument(
        '--target-root',
        type=Path,
        default=Path('web_scraper/scraped_images'),
        help='目标根目录'
    )
    parser.add_argument(
        '--min-images',
        type=int,
        default=10,
        help='只处理图片数量>=此值的类别'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟，不实际移动文件'
    )
    parser.add_argument(
        '--no-metadata',
        action='store_true',
        help='不生成JSON元数据'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='仅列出可挽救的类别，不执行移动'
    )

    args = parser.parse_args()

    # 扫描rejected目录
    logging.info(f"Scanning rejected directory: {args.rejected_dir}")
    category_stats = scan_rejected_dir(args.rejected_dir)

    if not category_stats:
        logging.warning("No categories found in rejected directory")
        return

    # 筛选害虫类别
    pest_categories = {
        cat: count for cat, count in category_stats.items()
        if is_pest_category(cat) and count >= args.min_images
    }

    logging.info(f"\n{'='*60}")
    logging.info(f"Found {len(pest_categories)} pest categories to rescue:")
    logging.info(f"{'='*60}")

    total_images = 0
    for cat, count in sorted(pest_categories.items(), key=lambda x: x[1], reverse=True):
        logging.info(f"  {cat:40s} : {count:4d} images")
        total_images += count

    logging.info(f"{'='*60}")
    logging.info(f"Total images to rescue: {total_images}")
    logging.info(f"{'='*60}\n")

    if args.list_only:
        return

    # 执行挽救
    total_moved = 0
    for category_name in sorted(pest_categories.keys()):
        moved = rescue_category(
            category_name,
            args.rejected_dir,
            args.target_root,
            dry_run=args.dry_run,
            regenerate_metadata=not args.no_metadata
        )
        total_moved += moved

    logging.info(f"\n{'='*60}")
    logging.info(f"{'[DRY-RUN] ' if args.dry_run else ''}Successfully rescued {total_moved} images!")
    logging.info(f"{'='*60}")


if __name__ == '__main__':
    main()
