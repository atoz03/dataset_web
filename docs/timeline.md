# 项目时间线

按时间倒序汇总所有里程碑与关键处理日志，保留完整细节以便追踪与复盘。

## 已完成的重要里程碑 ✅

- diseases 目录 LLM 验证：111,116 张图片，JSON 覆盖 100%（2025-10-27 ~ 29 完成）
- crops 目录 LLM 验证：30,623 张图片，JSON 覆盖 100%（2025-11-02 完成）
- pests 目录 LLM 验证：18,909 张图片，JSON 覆盖 100%（2025-11-06 完成）
- 害虫数据挖掘与挽救：14,496 张图片从 rejected 目录挽救（2025-10-30）
- scraped_images 导入：17,148 张图片从网络爬虫导入主数据集（2025-11-02）
- 孤儿 JSON 清理：清理 39,697 个无匹配图片的 JSON 文件（2025-11-02）
- 主数据集规模：160,648 张有效图片（diseases 111K + crops 30.6K + pests 18.9K）

## 数据集优化与产出 ✅

- data.jsonl 生成（2025-11-02）：基于 160,691 张图片生成约 857,315 条记录；跳过隐藏目录，优先使用 LLM 描述；分布 Train 79.2% | Val 9.6% | Test 11.2%。
- 跨来源测试集（web holdout，2025-11-06）：在 `scripts/05_index_and_stats/build_jsonl.py` 增加 `--holdout-source` 与 `__web__` 识别，生成 `data_holdout_web.jsonl`（约 133,133 条，仅 web 来源）。

## 关键处理日志（按时间倒序）

### 2025-12-09：稻作阶段判别与 Responses API 适配 🚀

- **代码更新**：`llm_tools/verify_and_describe.py` 增加 `ResponsesVLMClient`，支持 `/codex/v1/responses`（`instructions` 作为系统 prompt）；新增 `--api-type responses`；修复 `_validate_payload` 绑定问题；稻作阶段模式输出 `stage_en/stage_zh/stage_conf`。
- **运行配置**：`VLM_API_BASE=https://right.codes/codex/v1`、`VLM_MODEL=gpt-5.1`、`VLM_TYPE=responses`、代理 `socks5h://127.0.0.1:7895`、`workers=4`、`--rice-stage-mode --skip-existing-metadata --action move`。
- **处理范围**：`web_scraper/scraped_images` 下全部稻作相关目录（rice field、paddy tillering/jointing、rice booting/jointing/heading/heading panicles/panicle initiation/grain filling/milk/tillering、young rice tillering、Rice growth stages English、Time series timelapse）。
- **结果**：通过样本保留并写入同名 `.json` 元数据；不匹配移入各目录 `.rejected_by_llm/`（Time series timelapse 多为时钟类被整体拒绝）。日志位于 `logs/2025-12-09/llm_enhancement_*`。
- **后续建议**：若需复核或删除可检查 `.rejected_by_llm/`；重新计数可运行 `python scripts/count_images_by_class.py --roots web_scraper/scraped_images`。

### 2025-11-17：项目目录结构重组与文档更新 🗂️

- **背景**：根目录混乱，包含大量历史脚本、报告和备份文件，影响项目可维护性。
- **执行操作**：
  1. **创建archive目录结构**：
     - `docs/archive/reports/`：归档历史报告（API验证、爬虫总结、任务执行等）
     - `docs/archive/backups/`：归档数据备份文件（data.jsonl.backup_20251102等）
  2. **脚本重组**：
     - 创建 `scripts/00_utilities/`：集中存放10个监控/启动脚本（monitor_*.sh、START_*.sh等）
     - 确认现有脚本分类：01_scraping、02_ingest_and_merge、03_cleaning、04_llm_enhancement、05_index_and_stats
  3. **文件迁移**：
     - 移动6个历史报告（4个MD + 2个JSON）至 `docs/archive/reports/`
     - 移动1个备份文件（432MB）至 `docs/archive/backups/`
     - 移动10个shell脚本至 `scripts/00_utilities/`
  4. **文档更新**：
     - 更新 `CLAUDE.md`：反映新目录结构、分阶段脚本清单、根目录整洁原则
     - 更新 `docs/documentation.md`：添加完整项目目录树
     - 更新 `docs/timeline.md`：记录本次整理
- **验证结果**：
  - ✅ 工作流水线完整性：29个脚本（8个合并、5个清洗、2个统计、10个工具）
  - ✅ 配置文件齐全：.env.llm、requirements.txt、10个映射表
  - ✅ 数据文件完整：data.jsonl、data_holdout_web.jsonl、data.sample.jsonl
  - ✅ 根目录整洁：仅保留CLAUDE.md、README.md和核心数据文件
- **成果**：项目结构清晰化，文档同步更新，为后续开发和协作奠定良好基础。

### 2025-11-06：pests 剩余覆盖完成与脚本优化 🔧

- 背景：pests 目录有 19 张图片（0.1%）缺少 JSON 元数据，需要使用 gpt-5-nano 模型补充。
- 问题发现：
  1. 脚本扫描范围过广：`verify_and_describe.py` 的 `rglob('*')` 会递归扫描 `.trash` 与 `.rejected_by_llm`，导致处理不必要的图片。
  2. 413 请求过大错误：部分图片超过 3MB，超过 API 限制（500KB），导致失败。
- 解决方案：
  1. 添加隐藏目录过滤：在相关循环中加入 `if any(part.startswith('.') for part in image_path.parts): continue` 跳过隐藏目录。
  2. 智能图片压缩：在 `analyze_image` 中对超 500KB 图片自动压缩为 JPEG，质量梯度降低，将 3MB+ 控制到 300–400KB。
- 执行结果：全部 19 张通过验证，生成 19 个高质量 JSON（平均质量分数 0.92），无 413 错误与遗漏。
- 最终状态：pests 目录达到 100% 覆盖，18,858 张图片全部配备 JSON 元数据。

### 2025-11-02：pests 目录 JSON 命名不匹配问题

- **问题描述**: 旧版LLM验证脚本使用SHA1哈希命名JSON,导致15,731个孤儿JSON无法与标准命名的图片匹配
- **解决方案**:

  1. 使用 `cleanup_pests_orphan_jsons.py`脚本分析并清理SHA1孤儿JSON
  2. 重新运行LLM验证(gpt-5-nano模型,32并发),生成18,735个匹配的JSON
  3. 清理剩余孤儿JSON,实现99.1%覆盖率
- **技术要点**:

  - 新版脚本使用 `image_path.with_suffix('.json')`确保JSON与图片文件名完全匹配
  - 采用移动而非删除策略,孤儿JSON保存在 `.orphaned_jsons/`目录便于回溯
- 清理情况：

  - 清理 diseases 目录 18,605 个孤儿 JSON，实现 100% 匹配
  - 清理 crops 目录 5,361 个孤儿 JSON，实现 100% 匹配
  - 所有 JSON 文件严格一对一匹配图片文件

### 2025-11-02：更新了生产配置和数据挽救工作流

- 配置：
  - API Base: `https://88996.cloud/v1`
  - Model: `gpt-5-nano`（技术路线从早期的 4zapi → gemini-2.0-flash-lite-001 → gemini-2.5-flash-lite-nothinking，最终采用 nano）
  - Workers: `32`（高并发，显著提升处理速度）
  - 协议：OpenAI 兼容（`VLM_TYPE=openai`）
- 创新：项目开发了独特的错误数据挽救工作流（`scripts/02_ingest_and_merge/rescue_rejected_pests.py`），从被 LLM 拒绝的数据中，根据其 `actual_class` 提取出大量被初始标注错误的有效数据，显著提高数据利用率。

### 2025-10-31：数据集状态审计与文档更新 📊

- 背景：全面审计后发现实际 JSON 覆盖率与文档记录不符。
- 发现：
  1. diseases：112,903 张有效图片，JSON 覆盖率 100%（抽样验证）。
  2. crops：30,053 张有效图片，JSON 覆盖率 88%（如 tobacco plant 类别缺失）。
  3. pests：严重 JSON 命名不匹配问题：7,760 张标准命名图片（`wasp__web__uuid.jpg`）；10,711 个旧 SHA1 命名 JSON（`30a5c21f...json`），无法关联。
- 统计：主数据集总规模 150,716 张；data.jsonl 记录数 1,263,216 条；scraped_images 待导入 1,053 张。
- 统计：主数据集总规模 150,716 张；`data.jsonl` 记录数 1,263,216 条；`scraped_images` 待导入 1,053 张。
- 后续行动：修复 pests 关联关系、补充 crops 缺失 JSON、更新文档。

### 2025-10-30：害虫数据大规模采集与处理

- 目标：解决害虫数据占比不足（仅 3.5%）。
- 阶段 1 数据采集：`agri_sites` 爬虫自 GBIF/iNaturalist 抓取 14,774 张图片。
- 阶段 2 数据清洗：`deduplicate_images.py` 去重/去模糊/去小尺寸，删除率 5.4%。
- 阶段 3 LLM 验证：`verify_and_describe.py` + 32 并发生成描述。
- 阶段 4 错误数据挽救：`rescue_rejected_pests.py` 基于 `actual_class` 挽救 14,496 张误标图片。
- 阶段 5/6 导入与索引：`import_llm_verified_scraped.py` 导入至 `datasets/pests`，并重建 `data.jsonl`。
- 成果：pests 从 ~7,000 增至 21,593（+207%），显著缓解不平衡。

### 2025-10-18 ~ 2025-10-26：LLM 语义增强大规模任务

- 目标：对 ~22 万张图片进行 LLM 语义验证与描述生成。
- 挑战：API 速率限制（429）与服务不稳（503）。
- 解决方案：多次重试（指数退避）、多 API 负载均衡（`multi_api_client.py`）、并发调优（32 降至 2–8）。
- 成果：完成 95%+ 数据的语义增强与高质量 JSON 生成。

### 2025-10-09：图片抓取策略更新

- 主力数据源采用 GBIF/iNaturalist；Unsplash 作为补充；废弃不可用的 Bing API。

### 2025-10-08：现状分析与 API 验证

- 统计危急类别（<100 张），并推荐 Pixabay、Pexels 作为替代图片库 API。

### 2025-09-25 ~ 2025-10-05：初始数据集构建与合并

- 从 Kaggle/GitHub 等来源下载多个数据集（Crop Diseases、140 Crops、PlantDoc、PlantVillage、Plant Pathology 2020/2021 等）。
- 使用 `merge_*.py` 与 `bulk_rename_by_class.py` 统一命名并合并入 `datasets/`，随后进行基础清洗。
