# 农业图像大规模爬虫项目

本项目使用 Scrapy 框架构建，旨在从网络上大规模爬取农业相关的图像，以扩充您的多模态数据集。

## 项目结构

```
web_scraper/
├── keywords.txt            # 要爬取的关键词列表
├── scraped_images/         # 爬取到的图片存放目录 (运行后自动生成)
├── scrapy.cfg              # Scrapy 项目配置文件
└── scraper/
    ├── __init__.py
    ├── items.py            # 数据结构定义
    ├── pipelines.py        # 图片下载与分类管道
    ├── settings.py         # 项目设置
    └── spiders/
        ├── __init__.py
        └── bing_images_spider.py # 必应图片爬虫
```

## 如何使用

### 第 1 步：安装依赖

本项目依赖于 Scrapy。建议在 Python 虚拟环境 中安装。

```bash
# 1. (可选) 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

# 2. 安装 Scrapy
pip install scrapy
```

### 第 2 步：配置关键词

打开 `keywords.txt` 文件，在其中添加或修改您想要爬取的关键词，每个关键词占一行。

这些关键词应该尽可能与您主项目 `docs/documentation.md` 中定义的**本体（Ontology）**保持一致，这将极大地方便后续的数据整合。

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
```

爬虫会开始工作，读取 `keywords.txt` 中的每一个词，去必应图片搜索，然后将下载的图片分类保存在 `scraped_images/` 目录中。

### 第 4 步：检查结果

爬取完成后，您会在 `web_scraper/` 目录下发现一个新生成的 `scraped_images/` 文件夹。其中的结构如下：

```
scraped_images/
├── Apple Scab Leaf/
│   ├── 0a1b2c3d...e.jpg
│   └── f9e8d7c6...a.jpg
└── Corn rust leaf/
    ├── 4a5b6c7d...f.jpg
    └── ...
```
图片已经按照搜索词自动分好类了。

## 第 5 步：整合新数据到主项目

现在，您需要将这些新爬取、并经过初步分类的数据，整合到您现有的标准化工作流中。

1.  **人工审核**:
    *   **这是最关键的一步！** 请务必手动检查 `scraped_images/` 下每个类别文件夹中的图片。
    *   **删除所有不相关、低质量、或包含水印的图片。** 搜索引擎返回的结果质量参差不齐，人工审核是保证数据集质量的必要环节。

2.  **合并到主数据集**:
    *   将经过您审核筛选后的、干净的图片文件夹，**拷贝**到您主项目的 `datasets/diseases/` 或 `datasets/crops/` 目录下。
    *   例如，将 `web_scraper/scraped_images/Apple Scab Leaf/` 中的所有图片，拷贝到 `datasets/diseases/Apple Scab Leaf/` 中。

3.  **执行您的标准化工作流**:
    *   回到您的主项目根目录。
    *   **重命名文件**: 运行 `scripts/bulk_rename_by_class.py`，为这些新文件打上新的来源标签（例如 `--tag web`）。
    *   **数据清洗**: 运行 `scripts/deduplicate_images.py`，进行尺寸过滤、模糊检测和（最重要的）**跨来源去重**。
    *   **生成标注**: 最后，重新运行 `scripts/build_jsonl.py`，它会自动扫描到这些新加入的图片，并为它们生成标准的“图像-文本对”标注。

通过以上步骤，您就完成了一次完整的数据扩充循环：从爬取、审核到最终的自动化标注。

---

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