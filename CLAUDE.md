# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
---
## 项目概述

这是一个**农业多模态视觉数据集整合项目**,旨在构建高质量、大规模的农业知识库,用于训练视觉语言模型(VLM)。项目不仅提供图像分类数据,还生成丰富的多模态标注(中英双语Caption、VQA问答对、结构化标签)。

**核心特性:**

- 220+ 类别,215K+ 张图片(作物、病害、害虫)
- 中英双语图像描述和问答对生成
- 完整的数据溯源(标准化命名规范)
- LLM驱动的语义验证和质量控制
- Web界面人工审核工具

## 🎯 快速上手流程
完整阅读 `docs/documentation.md`，同步了解最新流程、术语和架构。

---

## 🌾 项目现状速览

- **目标**：构建农业多模态知识库（图像 + Caption + VQA + 结构化标签），服务视觉语言模型训练。
- **规模**：约 215K 张图片，覆盖 220+ 类别；作物≈80K、病害≈120K、害虫≈15K（持续更新）。
- **多语言**：默认生成中英双语文本，标签字段保持英文标准名，JSONL 中 `lang` 字段标注语言。
- **数据发布**：大数据集暂未随仓库提供，将在 Hugging Face 公开；当前提供 `data.sample.jsonl` 与处理脚本以复现流程。
- **质量策略**：全流程包含去重、模糊检测、尺寸筛选、LLM 语义验证与人工审核。

---

## 🗂 关键目录地图

```
dataset_web/
├── datasets/                # 标准化数据根目录（crops/pests/diseases）
│   ├── crops/
│   ├── pests/
│   └── diseases/
├── scripts/                 # 数据处理脚本（见下方清单）
├── llm_tools/               # LLM 验证与描述生成工具
├── web_scraper/             # 爬虫项目与缓存
├── docs/
│   ├── documentation.md     # 核心知识库（务必阅读）
│   ├── timeline.md          # 时间线与里程碑
│   ├── dev_notes/           # 助手提示 & 记忆库
│   └── archive/             # 历史文档与备份
├── stats_reports/           # 统计报表输出目录
├── mappings/                # 类别映射表（crop/disease/pest）
├── data.jsonl               # 全量多模态索引
├── data_holdout_web.jsonl   # 网爬保留集（验证用）
├── data.sample.jsonl        # 小样本示例
├── logs/                    # 任务与审计日志
├── sources/                 # 原始来源清单
└── docs/documentation.md    # 再次强调：核心文档
```

> 若新增目录或文件，请在 `docs/timeline.md` 或对应文档中登记，保持结构可追溯。

---

## 🔁 标准工作流（Playbook 摘要）

1. **数据合并**：
   - 复用 `scripts/merge_*.py` 族脚本（如 `merge_crop_diseases.py`、`merge_140_crops.py`）。
   - 始终“复制而非移动”，保持原始数据完整；必要时补充映射表。
2. **命名标准化**：
   - 运行 `python3 scripts/bulk_rename_by_class.py --root <目录> --tag <cd|pd|ac|ap>`。
   - 文件名格式：`<类别名>__<来源标签>__<uuid>.<ext>`，扩展名小写。
3. **去重与清洗**：
   - 使用 `scripts/deduplicate_images.py`，推荐先 `--action move` 移至 `.trash/`。
   - 常用参数：`--min-width 224 --min-height 224 --blur-method both --blur-threshold 60`。
4. **人工审核**：
   - 生成清单：`python3 scripts/generate_pest_review_manifest.py` 等。
   - 使用 `python3 scripts/pest_review_server.py` 或 `docs/pest_manual_review.html`（需本地 HTTP 服务）。
5. **LLM 语义增强**：
   - 调用 `python3 llm_tools/verify_and_describe.py --root <路径> --workers 6`。
   - 支持多 API 客户端（`multi_api_client.py`），需配置 `.env.llm`。
6. **生成 JSONL 索引**：
   - 命令示例：
     ```bash
     python3 scripts/build_jsonl.py \
         --roots datasets/diseases datasets/crops datasets/pests \
         --out data.jsonl \
         --train 0.8 --val 0.1 --test 0.1 \
         --seed 42
     ```
   - 默认生成 Caption/VQA 双任务条目，标签包含 `root/class/crop/disease/healthy/source`。
7. **统计与验收**：
   - 使用 `python3 scripts/generate_stats.py` 输出 CSV/JSON 报表。
   - 运行 `python3 scripts/count_images_by_class.py` 或 `python3 scripts/import_reviewed_pests.py` 等辅助脚本。
8. **记录行动**：
   - 将执行命令、参数、统计结果写入 `docs/dev_notes/` 或 `docs/archive/origin*.md`。

---

## 🔧 常用脚本速查

- `merge_crop_diseases.py` / `merge_kaggle_disease.py`：整合外部病害数据并映射标准类名。
- `merge_140_crops.py`：批量引入作物类数据集。
- `bulk_rename_by_class.py`：根据目录结构与来源标签统一重命名。
- `deduplicate_images.py`：支持 pHash/aHash 去重、模糊检测、尺寸过滤。
- `cleanup_pests_orphan_jsons.py`：清理孤立的 LLM JSON 元数据。
- `generate_pest_review_manifest.py` / `import_reviewed_pests.py`：配合人工审核与结果回流。
- `generate_stats.py`：输出类别、来源分布统计。
- `build_jsonl.py`：生成多模态 JSONL（Caption + VQA）。
- `verify_and_describe.py`：调用多 API 对图片生成描述并执行语义校验。
- `run_comprehensive_scraping.sh` / `scrape_pests_comprehensive.sh`：批量爬虫任务入口，需遵守爬虫策略。

> 若脚本新增参数或逻辑，请同步更新 `docs/documentation.md` 与此清单。

---

## ✅ 质量控制与记录规范

- **去重策略**：先移动再删除，确保可回滚；记录阈值、统计与样本数量。
- **LLM 验证**：设定合理并发（推荐 6），遇到 429/超时可降低 `--workers` 或开启 `--insecure`。
- **多语言输出**：Caption/VQA 需保持中英双语；JSONL `text` 字段内可包含双语串。
- **数据追溯**：任何改动需在 `origin.md` / `origin2.md` / `docs/dev_notes/mem.md` 中补充说明。
- **统计复核**：生成报表后将结果放入 `stats_reports/`，并写入更新日志（如 `docs/timeline.md`）。
- **安全操作**：默认不执行物理删除与破坏性操作，如确需执行，请先在说明文档中征询确认。

---

## 📚 文档与信息源指南

- `docs/documentation.md`：权威流程、规范、战略规划。
- `docs/timeline.md`：按时间记录的重大事件与版本演进。
如需补充新流程或变更，请同时更新 `docs/documentation.md` 保持信息一致。

---


---

## 🛠️ 常见问题与排障

- **LLM 请求 429/限流**：降低 `--workers` 或调整 `VLM_WORKERS` 环境变量；必要时错峰运行。
- **审核界面无法加载图片**：通过 `python3 -m http.server 8000` 启动本地服务，再访问 `http://localhost:8000/docs/pest_manual_review.html`。
- **爬虫被阻止**：优先使用官方 API；遵守 `robots.txt`，适度增加延迟。
- **JSONL 校验失败**：使用 `python3 -c "import json; [json.loads(line) for line in open('data.jsonl')]"` 检查格式；必要时重跑索引。
- **统计结果异常**：核对映射表与来源标签，确保目录命名正确，防止重复合并。

---

## 📏 编码与协作规范

### 八荣八耻

- 以瞎猜接口为耻，以认真查询为荣
- 以模糊执行为耻，以寻求确认为荣
- 以臆想业务为耻，以人类确认为荣
- 以创造接口为耻，以复用现有为荣
- 以一遍通过为耻，以回头校验为荣
- 以破坏架构为耻，以遵循规范为荣
- 以假装理解为耻，以诚实无知为荣
- 以盲目修改为耻，以谨慎重构为荣

### 核心原则

1. **认真查询**：修改前查阅现有实现与文档，避免臆测。
2. **寻求确认**：不确定时及时询问，保持沟通。
3. **业务对齐**：尊重人类指令，不擅自扩展需求。
4. **复用优先**：沿用现有脚本、模式与工具。
5. **完成校验**：执行后自检，必要时运行脚本验证结果。
6. **遵循架构**：保持目录、命名、依赖一致性。
7. **诚实反馈**：如遇阻碍或未知情况，立刻说明。
8. **谨慎重构**：充分理解上下文后再进行结构性调整。

> 奥卡姆剃刀原则：如无必要，勿增实体；在满足需求的前提下保持实现简洁。

---

若需要更多信息，请回到 `docs/documentation.md` 与相关记录；在执行新任务前务必确认最新要求。
