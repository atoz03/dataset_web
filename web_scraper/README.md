# 农业图像大规模爬虫项目

本项目使用 Scrapy 框架构建，旨在从网络上大规模爬取农业相关的图像，以扩充您的多模态数据集。

## 项目结构

```
web_scraper/
├── keywords.txt            # 要爬取的关键词列表
├── scraped_images/         # 爬取到的图片存放目录 (运行后自动生成)
├── scrapy.cfg              # Scrapy 项目配置文件
├── site_configs/           # 每个站点的采集配置（新增农业网站配置）
└── scraper/
    ├── __init__.py
    ├── items.py            # 数据结构定义
    ├── pipelines.py        # 图片下载与分类管道
    ├── settings.py         # 项目设置
    └── spiders/
        ├── __init__.py
        ├── agriculture_sites_spider.py # 农业垂直站点 & API 多源爬虫
        └── bing_images_spider.py       # 必应图片爬虫
```

## 如何使用

### 第 1 步：安装依赖

本项目依赖于 Scrapy、Pillow 等组件。建议在 Python 虚拟环境 中安装。

```bash
# 1. (可选) 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

# 2. 安装依赖（推荐使用仓库根目录的 requirements.txt）
pip install -r ../requirements.txt
```

### 第 2 步：配置关键词

打开 `keywords.txt` 文件，在其中添加或修改您想要爬取的关键词，每个关键词占一行。

这些关键词应该尽可能与您主项目 `docs/documentation.md` 中定义的**本体（Ontology）**保持一致，这将极大地方便后续的数据整合；为提升 API 类站点（如 iNaturalist）的命中率，建议同时提供标准学名或害虫/病原体英文名，例如 `Zea mays`、`Phytophthora infestans`。

**示例 `keywords.txt`:**
```
Apple Scab Leaf
Corn rust leaf
Tomato leaf mosaic virus
...
```

### 第 3 步：运行爬虫

在 `web_scraper/` 目录下，运行以下命令来启动爬虫：

```bash
# 确保您位于 web_scraper/ 目录下
cd web_scraper

# 运行 bing_images 爬虫
scrapy crawl bing_images

# 运行农业垂直站点爬虫（多站点 + API）
scrapy crawl agri_sites \\
  -a keywords_file=keywords.txt \\
  -a config_file=site_configs/agriculture_sites.json \\
  -a max_articles_per_keyword=40 \\
  -a max_api_results=1000
```

爬虫会开始工作，读取 `keywords.txt` 中的每一个词，去必应图片搜索，然后将下载的图片分类保存在 `scraped_images/` 目录中。

`agri_sites` 爬虫会读取相同的关键词清单，并根据 `site_configs/agriculture_sites.json` 中定义的站点配置执行采集：

- **gbif_occurrences**：使用 GBIF 开放 API，对应关键词映射到学名 `species/match`，再抓取带 `StillImage` 的观测记录，优先保留来自 `iNaturalist` 等开放许可源的高清原图与许可证、采集者等元数据。

可以通过命令行参数覆盖默认配置，例如：

- `max_api_results=500`：限制每个关键词在 API 站点处理的观测条目数量（GBIF 模式下按图片张数计数）。
- `config_file`：指向你自定义的 JSON 配置，实现快速扩展额外的农业网站或开放 API。

> ⚠️ 请务必遵守目标站点的 Robots 协议及使用条款。项目默认开启 `ROBOTSTXT_OBEY = True`，新增站点前建议先检查其 `robots.txt` 是否允许采集。

### 第 4 步：检查结果

爬取完成后，您会在 `web_scraper/` 目录下发现一个新生成的 `scraped_images/` 文件夹。其中的结构如下：

```
scraped_images/
├── Apple Scab Leaf/
│   ├── bing.com/
│   │   ├── 0a1b2c3d...e.jpg
│   │   └── f9e8d7c6...a.jpg
│   └── gbif_occurrences/
│       ├── 9c8b7a6d...e.jpg
│       └── ...
└── Corn leaf blight/
    ├── bing.com/
    └── gbif_occurrences/
```
图片已经按照搜索词自动分好类了。

### 第 4.2 步：预清洗与去重（推荐）

在人工审核前，可对 `scraped_images/` 执行一次尺寸/模糊/重复清理，减少明显低质或重复样本；近重复建议按“类级别”分组，以便跨来源（如 `bing.com` 与 `gbif_occurrences`）对比：

```bash
# 在仓库根目录执行（使用同一套脚本）
source .venv/bin/activate  # 如已创建

# 近重复按“类级别”范围，跨来源去重（bing.com 与 gbif_occurrences 等）
python scripts/deduplicate_images.py \
  --roots web_scraper/scraped_images \
  --min-width 224 --min-height 224 \
  --blur-method both --blur-threshold 60 --tenengrad-threshold 700 \
  --ham-threshold 3 --near-scope class --action move

# 从回收站“挽救”被误判的模糊图（基于当前阈值），仅执行回收不清洗：
python scripts/deduplicate_images.py \
  --roots web_scraper/scraped_images \
  --blur-method both --blur-threshold 60 --tenengrad-threshold 700 \
  --rescue-blur --skip-clean
```

上述命令会将待删除的文件安全移动到 `web_scraper/scraped_images/.trash/`，并支持在阈值调整后自动“回捞”被误判的模糊图，便于复核。

### 第 4.1 步：扩展站点配置（可选）

`site_configs/agriculture_sites.json` 采用列表形式描述每个农业站点或开放 API 的解析方式。核心字段说明如下：

- `type`: `html`、`api`、`gbif` 等；用于区分解析策略。
- `search`/`query`: 定义站点入口、分页方式、固定参数等（`gbif` 模式会自动对关键词执行 `species/match`）。
- `media_domains`: 明确允许下载的图片域名，避免下载到版权受限或未知来源的文件。
- `keyword_overrides`: 针对 `gbif` 模式覆盖关键词，对应到正式学名（如 `Apple Scab Leaf -> Venturia inaequalis`）。

可以复制现有条目快速添加更多农业网站，例如各国农业部公开图库、粮农组织（FAO）开放数据、植保机构的 RSS Feed 等。新增站点后建议先通过 `scrapy shell` 验证选择器是否稳定，再正式运行 `scrapy crawl agri_sites`。

## 第 5 步：整合新数据到主项目

现在，您需要将这些新爬取、并经过初步分类的数据，整合到您现有的标准化工作流中。

1.  **人工审核**:
    *   **这是最关键的一步！** 请务必手动检查 `scraped_images/` 下每个类别文件夹中的图片。
    *   **删除所有不相关、低质量、或包含水印的图片。** 搜索引擎返回的结果质量参差不齐，人工审核是保证数据集质量的必要环节。

2.  **合并到主数据集**:
    *   将经过您审核筛选后的、干净的图片文件夹，**拷贝**到您主项目的 `datasets/diseases/` 或 `datasets/crops/` 目录下。
    *   保留 `source_site` 这一层目录有助于追踪数据来源，后续清洗/去重可以依据目录或 `metadata.source_site` 字段过滤。
    *   例如，将 `web_scraper/scraped_images/Apple Scab Leaf/feedipedia/` 中的图片拷贝到 `datasets/diseases/Apple Scab Leaf/feedipedia/`。

3.  **执行您的标准化工作流**:
    *   回到您的主项目根目录。
    *   **重命名文件**: 运行 `scripts/bulk_rename_by_class.py`，为这些新文件打上新的来源标签（例如 `--tag web`）。
    *   **数据清洗**: 运行 `scripts/deduplicate_images.py`，进行尺寸过滤、模糊检测和（最重要的）**跨来源去重**。
    *   **生成标注**: 最后，重新运行 `scripts/build_jsonl.py`，它会自动扫描到这些新加入的图片，并为它们生成标准的“图像-文本对”标注。
    *   新增的 `metadata` 字段中包含了原始页面、来源站点、许可证等信息，可在构建 JSONL 时同步写入，帮助后续训练阶段进行溯源或过滤。

通过以上步骤，您就完成了一次完整的数据扩充循环：从爬取、审核到最终的自动化标注。

## 下一步扩展建议

- **扩大关键词覆盖**: 在 `web_scraper/keywords.txt` 中追加尚未覆盖的病害/虫害或作物学名，对命中率较低的条目补充 `site_configs/agriculture_sites.json` 的 `keyword_overrides`，确保能映射到 GBIF 可识别的学名。
- **提升抓取规模**: 在确认网络和许可允许的情况下，逐步提高 `scrapy crawl agri_sites` 的 `max_api_results` 或配置中的 `query.max_pages`，并拆分多批运行以避免一次性请求过大。
- **扩展数据源**: 若获取到允许采集的额外 API，可在 `site_configs/agriculture_sites.json` 新增条目，配置 `media_domains`、限速和分页策略；记得更新 README 与开发日志记录数据来源和使用条款。
 - **质量监控**: 每轮采集结束后审查 `web_scraper/agri_sites_run.log` 与 `scraped_images/*/gbif_occurrences/`，针对许可证（`license`）、作者（`creator`/`rights_holder`）或 robots 拒绝情况及时调整配置。

 ---

## 人工审核与并入（Pests 工作流）

为确保害虫图片质量与合规性，提供一套“离线网页审核 → 脚本导入”的流程。

### 1) 生成/刷新清单

抓取完成后，生成 `web_scraper/pest_review_manifest.js`（页面的数据源）。若去重/移动后出现 404 或需刷新，请在仓库根目录执行：

```bash
python3 scripts/generate_pest_review_manifest.py \
  --root web_scraper/scraped_images \
  --out web_scraper/pest_review_manifest.js
```

说明：清单会包含 `.trash/` 下的条目，并在每条记录上标注 `in_trash` 与 `trash_reason` 字段；页面会将其归入“回收站”分组，和正常类目分开展示，便于复核。

### 2) 打开审核页面

启动本地静态服务，确保相对路径生效：

```bash
python3 -m http.server 8000
# 在浏览器访问
http://localhost:8000/docs/pest_manual_review.html
```

页面功能：

- 按类别筛选，逐张标记“通过/剔除/重置”；
- 支持“回收站”分组展示（含原因标签），可针对近期清洗移入 `.trash/` 的图片进行复核与再判断；
- 支持导入/导出 JSON，决策同时保存在 `localStorage`；
- 无法看到图片时，请确认：
  - `web_scraper/pest_review_manifest.js` 是否存在且包含条目；
  - 是否通过本地服务以“仓库根目录”为站点根访问页面（`/docs/...`）；
  - 试用系统浏览器，避免 IDE 预览禁用本地脚本。

### 3) 导入审核通过的图片

使用 `scripts/import_reviewed_pests.py`：

```bash
python3 scripts/import_reviewed_pests.py \
    --review-json path/to/pest_review_YYYY-mm-dd.json \
    --tag web
```

脚本会把 `accepted` 条目拷贝到 `datasets/pests/<class>/`，自动重命名并进行尺寸/模糊/重复清理（安全移动至 `.trash/`）。

## 开发日志

- **2025-10-02**:
    - **项目启动**: BMad Master Orchestrator 响应用户需求，启动大规模爬虫项目，旨在极大扩充农业多模态数据集。
    - **项目初始化**:
        - 创建 `web_scraper/` 根目录。
        - 创建 Scrapy 配置文件 `scrapy.cfg` 和 `scraper/` 包结构。
    - **核心组件实现**:
        - 定义 `scraper/items.py`，明确了 `query`, `image_urls`, `source_site` 等核心数据字段。
        - 实现 `scraper/pipelines.py` 中的 `CustomImagesPipeline`，该管道能够根据搜索关键词将下载的图片自动存入对应的子文件夹。
        - 配置 `scraper/settings.py`，启用自定义管道，设定图片存储目录为 `scraped_images/`，并配置了友好的反爬虫策略（如 User-Agent, 下载延迟）。
    - **通用爬虫开发**:
        - 开发了 `scraper/spiders/bing_images_spider.py`，一个针对必应图片搜索的通用爬虫。
        - 该爬虫能从 `keywords.txt` 文件动态读取搜索词，并解析搜索结果页以提取图片链接。
    - **文档与交付**:
        - 创建了 `keywords.txt` 示例文件。
        - 编写了这份详细的 `README.md`，包含完整的安装、配置、运行和数据整合指南。
    - **项目状态**: 项目核心功能已完成并交付，用户可立即开始使用本工具进行数据爬取。
- **2025-10-03**:
    - **爬虫增强**: 升级 `bing_images_spider`，支持分页抓取、关键词 URL 编码、稳健的 JSON 解析，并为每张图片补充缩略图、标题、原始页面等元数据。
    - **多源抓取**: 新增 `agri_sites` 爬虫与 `site_configs/agriculture_sites.json`，形成可扩展的配置化多源框架，支持为每个数据源定制请求、分页、媒体过滤策略。
    - **管道优化**: 图片存储结构扩展为 `关键词/来源站点/文件名`，新增元数据、缩略图等字段，为后续标注提供更多上下文信息。
- **2025-10-04**:
    - **站点调整**: 遵守 robots 约束，停用 Feedipedia / iNaturalist 等受限源，新增 GBIF（Global Biodiversity Information Facility）作为开放式数据源，默认过滤到 `iNaturalist` 的公开授权图片。
    - **条目映射**: 新增农业病害到 GBIF 物种学名映射，自动通过 `species/match` + `occurrence/search` 获取 StillImage 数据及许可证信息。
    - **批量采集**: 在虚拟环境中运行 `scrapy crawl agri_sites -a max_api_results=20`，成功抓取 47 个条目、约 230 张图片，已按照 `关键词/gbif_occurrences/` 结构落盘，并保留原始版权/许可元数据。
