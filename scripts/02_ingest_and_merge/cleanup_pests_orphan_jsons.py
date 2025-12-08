#!/usr/bin/env python3
"""
清理pests目录中的孤儿JSON文件

问题背景:
- 旧版LLM验证脚本使用SHA1哈希作为JSON文件名
- 当前图片使用标准化命名 (class__source__uuid.ext)
- 导致5,502个JSON文件无法与图片关联

功能:
1. 生成详细的清理报告 (dry-run模式)
2. 将孤儿JSON移动到隔离目录 (可逆操作)
3. 统计需要生成JSON的图片

使用:
  # 阶段1: 生成报告
  python3 scripts/cleanup_pests_orphan_jsons.py --root datasets/pests --report-only

  # 阶段2: 执行清理
  python3 scripts/cleanup_pests_orphan_jsons.py --root datasets/pests --clean
"""

import argparse
import json
import shutil
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def is_sha1_filename(filename: str) -> bool:
    """检查文件名是否为SHA1哈希格式 (40位16进制)"""
    stem = Path(filename).stem
    return len(stem) == 40 and all(c in '0123456789abcdef' for c in stem.lower())


def analyze_pests_directory(root: Path) -> Dict:
    """分析pests目录,识别孤儿JSON和缺失JSON的图片"""

    print(f"正在扫描目录: {root}")
    print("-" * 60)

    # 收集所有文件
    all_images = list(root.rglob('*.jpg')) + list(root.rglob('*.jpeg')) + list(root.rglob('*.png'))
    all_jsons = list(root.rglob('*.json'))

    print(f"总图片数: {len(all_images)}")
    print(f"总JSON数: {len(all_jsons)}")
    print()

    # 分类统计
    report = {
        'sha1_orphan_jsons': [],       # SHA1格式的孤儿JSON
        'standard_orphan_jsons': [],   # 标准格式的孤儿JSON
        'images_without_json': [],     # 没有JSON的图片
        'matched_pairs': [],           # 正常匹配的图片-JSON对
    }

    stats = {
        'sha1_json_count': 0,
        'standard_json_count': 0,
    }

    # 1. 检查JSON文件
    for json_file in all_jsons:
        # 跳过特殊目录
        if any(part.startswith('.') for part in json_file.parts):
            continue

        is_sha1 = is_sha1_filename(json_file.name)

        if is_sha1:
            stats['sha1_json_count'] += 1
        else:
            stats['standard_json_count'] += 1

        # 检查是否有对应的图片
        has_image = False
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            img_file = json_file.with_suffix(ext)
            if img_file.exists():
                has_image = True
                report['matched_pairs'].append({
                    'image': str(img_file.relative_to(root)),
                    'json': str(json_file.relative_to(root))
                })
                break

        if not has_image:
            rel_path = str(json_file.relative_to(root))
            if is_sha1:
                report['sha1_orphan_jsons'].append(rel_path)
            else:
                report['standard_orphan_jsons'].append(rel_path)

    # 2. 检查图片文件
    for img_file in all_images:
        # 跳过特殊目录
        if any(part.startswith('.') for part in img_file.parts):
            continue

        json_file = img_file.with_suffix('.json')
        if not json_file.exists():
            report['images_without_json'].append(str(img_file.relative_to(root)))

    # 3. 按类别统计缺失JSON的图片
    images_no_json_by_class = defaultdict(int)
    for img_path in report['images_without_json']:
        class_name = Path(img_path).parent.name
        images_no_json_by_class[class_name] += 1

    report['images_no_json_by_class'] = dict(sorted(
        images_no_json_by_class.items(),
        key=lambda x: -x[1]
    ))

    # 4. 统计摘要
    report['summary'] = {
        'total_images': len(all_images),
        'total_jsons': len(all_jsons),
        'sha1_json_count': stats['sha1_json_count'],
        'standard_json_count': stats['standard_json_count'],
        'sha1_orphan_count': len(report['sha1_orphan_jsons']),
        'standard_orphan_count': len(report['standard_orphan_jsons']),
        'total_orphan_jsons': len(report['sha1_orphan_jsons']) + len(report['standard_orphan_jsons']),
        'images_without_json_count': len(report['images_without_json']),
        'matched_pairs_count': len(report['matched_pairs']),
        'match_rate': f"{len(report['matched_pairs']) / len(all_images) * 100:.1f}%" if all_images else "N/A"
    }

    return report


def print_report_summary(report: Dict):
    """打印报告摘要"""
    summary = report['summary']

    print("\n" + "=" * 60)
    print("清理报告摘要")
    print("=" * 60)

    print(f"\n📊 总体统计:")
    print(f"  图片总数:     {summary['total_images']:>6}")
    print(f"  JSON总数:     {summary['total_jsons']:>6}")
    print(f"  匹配对数:     {summary['matched_pairs_count']:>6}")
    print(f"  匹配率:       {summary['match_rate']:>6}")

    print(f"\n🔍 JSON分类:")
    print(f"  SHA1格式:     {summary['sha1_json_count']:>6}")
    print(f"  标准格式:     {summary['standard_json_count']:>6}")

    print(f"\n🗑️  孤儿JSON (需清理):")
    print(f"  SHA1孤儿:     {summary['sha1_orphan_count']:>6}")
    print(f"  标准孤儿:     {summary['standard_orphan_count']:>6}")
    print(f"  合计:         {summary['total_orphan_jsons']:>6}")

    print(f"\n❌ 缺失JSON的图片 (需生成):")
    print(f"  总计:         {summary['images_without_json_count']:>6}")

    if report['images_no_json_by_class']:
        print(f"\n  按类别分布 (Top 10):")
        for i, (class_name, count) in enumerate(list(report['images_no_json_by_class'].items())[:10], 1):
            print(f"    {i:2}. {class_name:40} {count:>4}")

    print("\n" + "=" * 60)


def cleanup_orphan_jsons(root: Path, report: Dict, dry_run: bool = False):
    """清理孤儿JSON文件"""

    orphan_dir = root / '.orphaned_jsons'
    sha1_dir = orphan_dir / 'sha1'
    standard_dir = orphan_dir / 'standard'

    if not dry_run:
        sha1_dir.mkdir(parents=True, exist_ok=True)
        standard_dir.mkdir(parents=True, exist_ok=True)

    total_moved = 0

    # 移动SHA1孤儿JSON
    print(f"\n🔧 移动SHA1孤儿JSON到: {sha1_dir}")
    for i, rel_path in enumerate(report['sha1_orphan_jsons'], 1):
        src = root / rel_path
        dst = sha1_dir / src.name

        if dry_run:
            print(f"  [DRY-RUN] {i}/{len(report['sha1_orphan_jsons'])}: {rel_path}")
        else:
            shutil.move(str(src), str(dst))
            if i % 100 == 0 or i == len(report['sha1_orphan_jsons']):
                print(f"  进度: {i}/{len(report['sha1_orphan_jsons'])}")

        total_moved += 1

    # 移动标准格式孤儿JSON (保留目录结构)
    print(f"\n🔧 移动标准孤儿JSON到: {standard_dir}")
    for i, rel_path in enumerate(report['standard_orphan_jsons'], 1):
        src = root / rel_path
        dst = standard_dir / rel_path

        if dry_run:
            print(f"  [DRY-RUN] {i}/{len(report['standard_orphan_jsons'])}: {rel_path}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            if i % 50 == 0 or i == len(report['standard_orphan_jsons']):
                print(f"  进度: {i}/{len(report['standard_orphan_jsons'])}")

        total_moved += 1

    print(f"\n✅ 完成! 共{'模拟' if dry_run else ''}移动 {total_moved} 个孤儿JSON文件")

    if not dry_run:
        print(f"\n💡 提示: 如需回滚,可以从 {orphan_dir} 恢复文件")


def main():
    parser = argparse.ArgumentParser(
        description="清理pests目录中的孤儿JSON文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成报告 (只读)
  python3 %(prog)s --root datasets/pests --report-only

  # 预览清理操作 (dry-run)
  python3 %(prog)s --root datasets/pests --clean --dry-run

  # 执行清理
  python3 %(prog)s --root datasets/pests --clean
        """
    )

    parser.add_argument(
        '--root',
        type=Path,
        required=True,
        help='pests目录路径'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='只生成报告,不执行清理'
    )

    parser.add_argument(
        '--clean',
        action='store_true',
        help='执行清理操作'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干跑模式,只模拟操作'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('pests_cleanup_report.json'),
        help='报告输出路径 (默认: pests_cleanup_report.json)'
    )

    args = parser.parse_args()

    # 验证路径
    if not args.root.exists():
        print(f"❌ 错误: 目录不存在: {args.root}")
        return 1

    # 生成分析报告
    report = analyze_pests_directory(args.root)

    # 打印摘要
    print_report_summary(report)

    # 保存详细报告
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {args.output}")

    # 执行清理
    if args.clean:
        print("\n" + "=" * 60)
        print("开始清理操作")
        print("=" * 60)

        if args.dry_run:
            print("\n⚠️  DRY-RUN模式 - 不会实际修改文件")

        cleanup_orphan_jsons(args.root, report, dry_run=args.dry_run)

    elif args.report_only:
        print(f"\n💡 提示: 使用 --clean 参数执行清理操作")

    else:
        print(f"\n💡 提示: 使用 --report-only 或 --clean 参数")

    return 0


if __name__ == '__main__':
    exit(main())
