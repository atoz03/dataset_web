#!/usr/bin/env python3
"""
Monitor LLM verification tasks and generate progress reports

监控LLM验证任务并生成进度报告
"""

import time
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def count_images_with_json(root: Path) -> tuple:
    """统计目录中图片和JSON文件的数量"""
    if not root.exists():
        return 0, 0, 0

    total_imgs = 0
    has_json = 0

    for img in root.rglob('*.jpg'):
        if any(part.startswith('.') for part in img.parts):
            continue
        total_imgs += 1
        json_file = img.with_suffix('.json')
        if json_file.exists():
            has_json += 1

    missing = total_imgs - has_json
    coverage = (has_json / total_imgs * 100) if total_imgs > 0 else 0

    return total_imgs, has_json, missing, coverage


def parse_log_stats(log_file: Path) -> dict:
    """解析日志文件统计信息"""
    if not log_file.exists():
        return {}

    stats = {
        'accepted': 0,
        'rejected': 0,
        'errors': 0,
        'last_update': None
    }

    try:
        with open(log_file, 'r') as f:
            for line in f:
                if 'ACCEPTED:' in line:
                    stats['accepted'] += 1
                elif 'REJECTED:' in line or 'WARNING - REJECTED' in line:
                    stats['rejected'] += 1
                elif 'ERROR' in line:
                    stats['errors'] += 1

                # 提取时间戳
                if line.startswith('2025-'):
                    timestamp = line.split(' - ')[0]
                    stats['last_update'] = timestamp
    except Exception as e:
        print(f"Error parsing log {log_file}: {e}")

    stats['processed'] = stats['accepted'] + stats['rejected']
    return stats


def generate_report():
    """生成进度报告"""
    report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 统计pests目录
    pests_root = Path('datasets/pests')
    pests_total, pests_has_json, pests_missing, pests_coverage = count_images_with_json(pests_root)

    # 统计crops目录
    crops_root = Path('datasets/crops')
    crops_total, crops_has_json, crops_missing, crops_coverage = count_images_with_json(crops_root)

    # 解析日志统计
    pests_log_stats = parse_log_stats(Path('logs/pests_llm_verification_20251031.log'))
    crops_log_stats = parse_log_stats(Path('logs/crops_llm_verification_20251031.log'))

    # 生成报告
    report = f"""
{'='*80}
LLM验证任务进度报告
生成时间: {report_time}
{'='*80}

## Pests目录 (害虫)
  总图片数:     {pests_total:>6}
  已有JSON:     {pests_has_json:>6}
  缺失JSON:     {pests_missing:>6}
  覆盖率:       {pests_coverage:>5.1f}%

  日志统计:
    已处理:     {pests_log_stats.get('processed', 0):>6}
    通过:       {pests_log_stats.get('accepted', 0):>6}
    拒绝:       {pests_log_stats.get('rejected', 0):>6}
    错误:       {pests_log_stats.get('errors', 0):>6}
    最后更新:   {pests_log_stats.get('last_update', 'N/A')}

## Crops目录 (作物)
  总图片数:     {crops_total:>6}
  已有JSON:     {crops_has_json:>6}
  缺失JSON:     {crops_missing:>6}
  覆盖率:       {crops_coverage:>5.1f}%

  日志统计:
    已处理:     {crops_log_stats.get('processed', 0):>6}
    通过:       {crops_log_stats.get('accepted', 0):>6}
    拒绝:       {crops_log_stats.get('rejected', 0):>6}
    错误:       {crops_log_stats.get('errors', 0):>6}
    最后更新:   {crops_log_stats.get('last_update', 'N/A')}

## 总体进度
  总待处理:     {pests_missing + crops_missing:>6}
  Pests进度:    {pests_coverage:.1f}% {'✅' if pests_coverage >= 99 else '⏳'}
  Crops进度:    {crops_coverage:.1f}% {'✅' if crops_coverage >= 99 else '⏳'}

{'='*80}
"""

    return report, {
        'timestamp': report_time,
        'pests': {
            'total': pests_total,
            'has_json': pests_has_json,
            'missing': pests_missing,
            'coverage': pests_coverage,
            'log_stats': pests_log_stats
        },
        'crops': {
            'total': crops_total,
            'has_json': crops_has_json,
            'missing': crops_missing,
            'coverage': crops_coverage,
            'log_stats': crops_log_stats
        }
    }


def main():
    """主循环:每30分钟生成一次报告"""
    report_file = Path('logs/llm_monitoring_reports.log')
    json_file = Path('logs/llm_monitoring_data.json')

    reports_history = []

    print("开始监控LLM验证任务...")
    print("报告将保存到: logs/llm_monitoring_reports.log")
    print("按Ctrl+C停止监控\n")

    try:
        iteration = 0
        while True:
            iteration += 1

            # 生成报告
            report_text, report_data = generate_report()

            # 打印到控制台
            print(report_text)

            # 追加到日志文件
            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(report_text + '\n')

            # 保存JSON数据
            reports_history.append(report_data)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(reports_history, f, indent=2, ensure_ascii=False)

            # 检查是否完成
            pests_done = report_data['pests']['coverage'] >= 99.0
            crops_done = report_data['crops']['coverage'] >= 99.0

            if pests_done and crops_done:
                print("\n✅ 所有任务已完成!")
                break

            # 等待30分钟
            print(f"等待30分钟后进行下一次检查... (迭代 #{iteration})")
            time.sleep(1800)  # 30分钟

    except KeyboardInterrupt:
        print("\n\n监控已停止")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == '__main__':
    main()
