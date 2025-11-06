#!/usr/bin/env python3
"""
Generate comprehensive statistics reports from JSONL datasets.

This script reads JSONL files (data.jsonl, data_holdout_web.jsonl) and generates
four CSV reports with statistics grouped by class, source, split, and class×source pivot table.

Usage:
  python3 scripts/generate_stats.py \
    --jsonl data.jsonl data_holdout_web.jsonl \
    --out-dir stats_reports

  # Or summary only (no CSV files)
  python3 scripts/generate_stats.py \
    --jsonl data.jsonl \
    --summary-only

Output Files:
  - counts_by_class.csv: Statistics grouped by class (labels.class)
  - counts_by_source.csv: Statistics grouped by source (labels.source)
  - counts_by_split.csv: Statistics grouped by split (train/val/test)
  - class_source_pivot.csv: Cross-tabulation of class × source (image counts)

Author: Claude Code
Date: 2025-11-06
"""

import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, Set, List, Any


class StatsCollector:
    """Collects and aggregates statistics from JSONL dataset files."""

    def __init__(self):
        # Store metadata for each unique image
        self.images: Dict[str, Dict[str, Any]] = {}

        # Aggregated statistics by different dimensions
        # Structure: {class_name: {images: set(), records: int, train: set(), val: set(), test: set()}}
        self.by_class = defaultdict(lambda: {
            'root': None,
            'images': set(),
            'records': 0,
            'train': set(),
            'val': set(),
            'test': set()
        })

        self.by_source = defaultdict(lambda: {
            'images': set(),
            'records': 0,
            'train': set(),
            'val': set(),
            'test': set()
        })

        self.by_split = defaultdict(lambda: {
            'images': set(),
            'records': 0,
            'classes': set(),
            'sources': set()
        })

        # Pivot table: class -> source -> set of images
        self.pivot: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

        # Track source JSONL files
        self.source_files: List[str] = []

        # Total records processed
        self.total_records = 0

    def process_jsonl(self, jsonl_path: Path):
        """Process a single JSONL file and update statistics."""
        print(f"📖 处理文件: {jsonl_path.name} ...")

        self.source_files.append(jsonl_path.name)
        records_in_file = 0

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"⚠️  行 {line_num} JSON解析错误: {e}")
                    continue

                self.process_record(record)
                records_in_file += 1

                # Progress indicator
                if records_in_file % 100000 == 0:
                    print(f"   已处理 {records_in_file:,} 条记录...")

        self.total_records += records_in_file
        print(f"✅ 完成: {records_in_file:,} 条记录\n")

    def process_record(self, record: Dict[str, Any]):
        """Process a single JSONL record and update statistics."""
        # Extract key fields
        image_path = record.get('image', '')
        split = record.get('split', 'unknown')
        labels = record.get('labels', {})

        class_name = labels.get('class', 'unknown')
        source = labels.get('source', 'unknown')
        root = labels.get('root', 'unknown')

        # Update image metadata (only store once per unique image)
        if image_path not in self.images:
            self.images[image_path] = {
                'class': class_name,
                'source': source,
                'root': root,
                'split': split
            }

        # Update by_class statistics
        if self.by_class[class_name]['root'] is None:
            self.by_class[class_name]['root'] = root
        self.by_class[class_name]['images'].add(image_path)
        self.by_class[class_name]['records'] += 1
        self.by_class[class_name][split].add(image_path)

        # Update by_source statistics
        self.by_source[source]['images'].add(image_path)
        self.by_source[source]['records'] += 1
        self.by_source[source][split].add(image_path)

        # Update by_split statistics
        self.by_split[split]['images'].add(image_path)
        self.by_split[split]['records'] += 1
        self.by_split[split]['classes'].add(class_name)
        self.by_split[split]['sources'].add(source)

        # Update pivot table
        self.pivot[class_name][source].add(image_path)

    def generate_reports(self, out_dir: Path):
        """Generate all four CSV reports."""
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        source_jsonl = ', '.join(self.source_files)

        print(f"📊 生成CSV报告到: {out_dir}/\n")

        # 1. counts_by_class.csv
        self._generate_class_report(out_dir / 'counts_by_class.csv', timestamp, source_jsonl)

        # 2. counts_by_source.csv
        self._generate_source_report(out_dir / 'counts_by_source.csv', timestamp, source_jsonl)

        # 3. counts_by_split.csv
        self._generate_split_report(out_dir / 'counts_by_split.csv', timestamp, source_jsonl)

        # 4. class_source_pivot.csv
        self._generate_pivot_report(out_dir / 'class_source_pivot.csv', timestamp, source_jsonl)

        print(f"\n✅ 所有CSV报告已生成完成!")

    def _generate_class_report(self, output_path: Path, timestamp: str, source_jsonl: str):
        """Generate counts_by_class.csv"""
        print(f"   生成 {output_path.name} ...")

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'class', 'root', 'image_count', 'record_count',
                'train_images', 'val_images', 'test_images',
                'generated_at', 'source_jsonl'
            ])

            # Sort by class name
            for class_name in sorted(self.by_class.keys()):
                stats = self.by_class[class_name]
                writer.writerow([
                    class_name,
                    stats['root'],
                    len(stats['images']),
                    stats['records'],
                    len(stats['train']),
                    len(stats['val']),
                    len(stats['test']),
                    timestamp,
                    source_jsonl
                ])

        print(f"      ✓ {len(self.by_class)} 个类别")

    def _generate_source_report(self, output_path: Path, timestamp: str, source_jsonl: str):
        """Generate counts_by_source.csv"""
        print(f"   生成 {output_path.name} ...")

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'source', 'image_count', 'record_count',
                'train_images', 'val_images', 'test_images',
                'generated_at', 'source_jsonl'
            ])

            # Sort by source name
            for source in sorted(self.by_source.keys()):
                stats = self.by_source[source]
                writer.writerow([
                    source,
                    len(stats['images']),
                    stats['records'],
                    len(stats['train']),
                    len(stats['val']),
                    len(stats['test']),
                    timestamp,
                    source_jsonl
                ])

        print(f"      ✓ {len(self.by_source)} 个来源")

    def _generate_split_report(self, output_path: Path, timestamp: str, source_jsonl: str):
        """Generate counts_by_split.csv"""
        print(f"   生成 {output_path.name} ...")

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'split', 'image_count', 'record_count',
                'class_count', 'source_count',
                'generated_at', 'source_jsonl'
            ])

            # Sort by split (train, val, test)
            for split in sorted(self.by_split.keys()):
                stats = self.by_split[split]
                writer.writerow([
                    split,
                    len(stats['images']),
                    stats['records'],
                    len(stats['classes']),
                    len(stats['sources']),
                    timestamp,
                    source_jsonl
                ])

        print(f"      ✓ {len(self.by_split)} 个划分")

    def _generate_pivot_report(self, output_path: Path, timestamp: str, source_jsonl: str):
        """Generate class_source_pivot.csv (class × source cross-tabulation)"""
        print(f"   生成 {output_path.name} ...")

        # Get all unique sources (sorted)
        all_sources = sorted(self.by_source.keys())

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # Header: class, source1, source2, ..., total, generated_at, source_jsonl
            writer.writerow(['class'] + all_sources + ['total', 'generated_at', 'source_jsonl'])

            # Sort by class name
            for class_name in sorted(self.pivot.keys()):
                row = [class_name]

                # Count images for each source
                total = 0
                for source in all_sources:
                    count = len(self.pivot[class_name][source])
                    row.append(count)
                    total += count

                row.extend([total, timestamp, source_jsonl])
                writer.writerow(row)

        print(f"      ✓ {len(self.pivot)} 个类别 × {len(all_sources)} 个来源")

    def print_summary(self):
        """Print a formatted summary report to terminal."""
        print("\n" + "=" * 80)
        print("📊 数据集统计摘要")
        print("=" * 80)

        # Overall statistics
        total_images = len(self.images)
        print(f"\n总体统计:")
        print(f"  - 唯一图片数: {total_images:,}")
        print(f"  - JSONL记录数: {self.total_records:,}")
        print(f"  - 平均记录/图片: {self.total_records/total_images:.1f}x")

        # By split
        print(f"\n按数据划分:")
        for split in sorted(self.by_split.keys()):
            stats = self.by_split[split]
            img_count = len(stats['images'])
            rec_count = stats['records']
            print(f"  {split:8s}: {img_count:7,} 张图片 | {rec_count:9,} 条记录")

        # By source (top 10)
        print(f"\n按来源统计 (Top 10):")
        sorted_sources = sorted(self.by_source.items(),
                               key=lambda x: len(x[1]['images']),
                               reverse=True)
        for source, stats in sorted_sources[:10]:
            img_count = len(stats['images'])
            rec_count = stats['records']
            print(f"  {source:10s}: {img_count:7,} 张图片 | {rec_count:9,} 条记录")

        if len(sorted_sources) > 10:
            print(f"  ... 还有 {len(sorted_sources) - 10} 个来源")

        # By class (top 15)
        print(f"\n按类别统计 (Top 15):")
        sorted_classes = sorted(self.by_class.items(),
                               key=lambda x: len(x[1]['images']),
                               reverse=True)
        for class_name, stats in sorted_classes[:15]:
            img_count = len(stats['images'])
            root = stats['root']
            print(f"  {class_name:30s} [{root:8s}]: {img_count:6,} 张图片")

        if len(sorted_classes) > 15:
            print(f"  ... 还有 {len(sorted_classes) - 15} 个类别")

        print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Generate comprehensive statistics reports from JSONL datasets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all CSV reports
  python3 scripts/generate_stats.py \\
    --jsonl data.jsonl data_holdout_web.jsonl \\
    --out-dir stats_reports

  # Summary only (no CSV files)
  python3 scripts/generate_stats.py \\
    --jsonl data.jsonl \\
    --summary-only
        """
    )

    parser.add_argument(
        '--jsonl',
        nargs='+',
        required=True,
        help='JSONL file(s) to process (e.g., data.jsonl data_holdout_web.jsonl)'
    )

    parser.add_argument(
        '--out-dir',
        type=str,
        default='stats_reports',
        help='Output directory for CSV reports (default: stats_reports)'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only print terminal summary, do not generate CSV files'
    )

    args = parser.parse_args()

    # Initialize collector
    collector = StatsCollector()

    # Process each JSONL file
    print(f"\n🚀 开始处理 {len(args.jsonl)} 个JSONL文件...\n")
    for jsonl_file in args.jsonl:
        jsonl_path = Path(jsonl_file)
        if not jsonl_path.exists():
            print(f"❌ 文件不存在: {jsonl_path}")
            continue
        collector.process_jsonl(jsonl_path)

    # Print summary to terminal
    collector.print_summary()

    # Generate CSV reports (unless summary-only)
    if not args.summary_only:
        out_dir = Path(args.out_dir)
        collector.generate_reports(out_dir)
        print(f"\n💾 CSV报告已保存到: {out_dir.resolve()}/")
    else:
        print(f"\n💡 使用 --out-dir 参数可生成CSV文件")


if __name__ == '__main__':
    main()
